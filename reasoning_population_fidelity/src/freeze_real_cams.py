from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE / "src"))

import production_runtime as legacy_runtime
import prepare_sample as legacy_sample
from core import approx_tokens, build_prompt, sha256_text, validate_persona
from pipeline import expand, load_config, load_jsonl, validate_expanded

CODES_BUNDLE = ROOT / "data" / "encrypted" / "cams_codes_v2.x25519.aesgcm.gz.b64"
TRUTH_BUNDLE = ROOT / "data" / "encrypted" / "cams_truth_v2.x25519.aesgcm.gz.b64"
CONFIG = HERE / "config" / "preflight.json"
SCHEMA = HERE / "prompts" / "response_schema.json"


def pct(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return float(xs[lo] * (1 - frac) + xs[hi] * frac)


def encrypted_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_base(out: Path) -> dict:
    code_text = legacy_runtime.decrypt_bundle(CODES_BUNDLE, legacy_runtime.CODES_AAD).decode("utf-8")
    truth_text = legacy_runtime.decrypt_bundle(TRUTH_BUNDLE, legacy_runtime.TRUTH_AAD).decode("utf-8")
    code_rows = list(csv.DictReader(StringIO(code_text)))
    truth_rows = list(csv.DictReader(StringIO(truth_text)))
    if len(code_rows) != 1000 or len(truth_rows) != 1000:
        raise AssertionError((len(code_rows), len(truth_rows)))
    code_ids = [r["anon_id"] for r in code_rows]
    truth_ids = [r["anon_id"] for r in truth_rows]
    if len(set(code_ids)) != 1000 or len(set(truth_ids)) != 1000:
        raise AssertionError("Duplicate frozen CAMS IDs")
    if set(code_ids) != set(truth_ids):
        raise AssertionError("Frozen persona and truth ID sets differ")
    rows = []
    for raw in sorted(code_rows, key=lambda r: r["anon_id"]):
        decoded = legacy_runtime.decode_row(raw)
        persona = legacy_sample.build_persona(decoded, "rich")
        validate_persona(persona)
        prompt = build_prompt(persona)
        rows.append({"anon_id": raw["anon_id"], "persona": persona, "prompt": prompt})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "respondents": len(rows),
        "codes_bundle_sha256": encrypted_sha(CODES_BUNDLE),
        "truth_bundle_sha256": encrypted_sha(TRUTH_BUNDLE),
        "base_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }


def freeze(base: Path, requests: Path, manifest: Path) -> dict:
    cfg = load_config(CONFIG)
    expected_conditions = set(cfg["study_1"]["reasoning_conditions"])
    if expected_conditions != {"off", "low", "xhigh"}:
        raise AssertionError(f"Unexpected treatment set: {sorted(expected_conditions)}")
    build_info = build_base(base)
    expansion = expand(base, requests, CONFIG, SCHEMA)
    rows = load_jsonl(requests)
    errors = validate_expanded(rows, cfg)
    if errors:
        raise AssertionError(errors[:20])
    if len(rows) != 3000 or expansion["respondents"] != 1000:
        raise AssertionError(expansion)
    by_id: dict[str, list[dict]] = {}
    for r in rows:
        by_id.setdefault(r["anon_id"], []).append(r)
    if len(by_id) != 1000:
        raise AssertionError("Wrong respondent count after expansion")
    for anon_id, grp in by_id.items():
        if len(grp) != 3:
            raise AssertionError(f"{anon_id}: expected 3 requests")
        if len({g["prompt"] for g in grp}) != 1:
            raise AssertionError(f"{anon_id}: prompt differs across reasoning conditions")
        if {g["reasoning"] for g in grp} != expected_conditions:
            raise AssertionError(f"{anon_id}: wrong reasoning conditions")
        if len({json.dumps(g["generation_settings"], sort_keys=True) for g in grp}) != 1:
            raise AssertionError(f"{anon_id}: generation settings differ across conditions")
    unique_prompts = [grp[0]["prompt"] for grp in by_id.values()]
    prompt_chars = [len(p) for p in unique_prompts]
    prompt_tokens = [approx_tokens(p) for p in unique_prompts]
    repeated_input_tokens = sum(approx_tokens(r["prompt"]) for r in rows)
    hard_completion_tokens = sum(int(r["reasoning_settings"]["max_completion_tokens"]) for r in rows)
    pm = cfg["primary_model"]
    current_price_cost = repeated_input_tokens / 1e6 * pm["input_usd_per_million"] + hard_completion_tokens / 1e6 * pm["output_usd_per_million"]
    ceiling = cfg["run_policy"]["provider_max_price_usd_per_million"]
    provider_ceiling_cost = repeated_input_tokens / 1e6 * ceiling["prompt"] + hard_completion_tokens / 1e6 * ceiling["completion"]
    req_bytes = requests.read_bytes()
    request_ids = [r["request_id"] for r in rows]
    result = {
        "freeze_version": 2,
        "experiment": "CAMS reasoning population fidelity",
        "respondents": 1000,
        "requests": 3000,
        "conditions": ["off", "low", "xhigh"],
        "model": pm["id"],
        "outcomes": cfg["outcomes"],
        "paid_inference_performed": False,
        "plaintext_committed": False,
        "encrypted_sources": {
            "codes_bundle_sha256": build_info["codes_bundle_sha256"],
            "truth_bundle_sha256": build_info["truth_bundle_sha256"],
        },
        "hashes": {
            "base_jsonl_sha256": build_info["base_sha256"],
            "requests_jsonl_sha256": hashlib.sha256(req_bytes).hexdigest(),
            "config_sha256": sha256_text(CONFIG.read_text(encoding="utf-8")),
            "schema_sha256": sha256_text(SCHEMA.read_text(encoding="utf-8")),
            "request_id_set_sha256": sha256_text("\n".join(sorted(request_ids)) + "\n"),
        },
        "invariants": {
            "unique_respondent_ids": len(by_id),
            "unique_request_ids": len(set(request_ids)),
            "requests_per_respondent": 3,
            "byte_identical_prompt_across_conditions": True,
            "generation_settings_identical_across_conditions": True,
            "persona_leakage_scan": "PASS",
            "expanded_request_validation": "PASS",
            "truth_id_set_matches_persona_id_set": True,
        },
        "prompt_distribution_per_unique_respondent": {
            "characters": {"min": min(prompt_chars), "median": statistics.median(prompt_chars), "mean": round(statistics.mean(prompt_chars), 3), "p95": round(pct(prompt_chars, 0.95), 3), "max": max(prompt_chars)},
            "conservative_approx_tokens_len_over_3_2": {"min": min(prompt_tokens), "median": statistics.median(prompt_tokens), "mean": round(statistics.mean(prompt_tokens), 3), "p95": round(pct(prompt_tokens, 0.95), 3), "max": max(prompt_tokens)},
            "note": "Deterministic conservative preflight estimates. Provider-billed tokenizer counts are measured in the engineering pilot before the full run."
        },
        "budget_projection": {
            "repeated_input_tokens_conservative": repeated_input_tokens,
            "hard_capped_completion_tokens": hard_completion_tokens,
            "configured_routed_price_usd_per_million": {"input": pm["input_usd_per_million"], "output": pm["output_usd_per_million"]},
            "configured_price_projection_usd": round(current_price_cost, 6),
            "hard_provider_ceiling_usd_per_million": ceiling,
            "provider_ceiling_projection_usd": round(provider_ceiling_cost, 6),
            "study_1_cap_usd": cfg["study_1"]["study_budget_cap_usd"],
            "absolute_project_spend_cap_usd": cfg["hard_spend_cap_usd"],
        },
        "reasoning_completion_caps": cfg["study_1"]["reasoning_conditions"],
        "generation_settings": cfg["study_1"]["generation_settings"],
    }
    if result["budget_projection"]["provider_ceiling_projection_usd"] > cfg["study_1"]["study_budget_cap_usd"]:
        raise AssertionError("Worst-case provider-ceiling projection exceeds Study 1 cap")
    if result["invariants"]["unique_request_ids"] != 3000:
        raise AssertionError("Request IDs are not unique")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default="/tmp/rpf_real_freeze")
    args = ap.parse_args()
    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    result = freeze(work / "base.jsonl", work / "requests.jsonl", work / "freeze_manifest.json")
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
