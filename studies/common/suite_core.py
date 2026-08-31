from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "src", ROOT / "reasoning_population_fidelity" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import production_runtime
import multisurvey_runtime
import prepare_sample
from core import build_prompt as build_cams_prompt, validate_persona
from multisurvey_request_builder import STATE, GENDER, SECTOR, SOCIAL, MARITAL, Q

REGISTRY = ROOT / "studies" / "registry.json"
CAMS_CODES = ROOT / "data" / "encrypted" / "cams_codes_v2.x25519.aesgcm.gz.b64"
CAMS_TRUTH = ROOT / "data" / "encrypted" / "cams_truth_v2.x25519.aesgcm.gz.b64"
PLFS_PARTS = "plfs_2023_24_codes_full.part*.b64"
SCHEMA = ROOT / "reasoning_population_fidelity" / "prompts" / "response_schema.json"

PLFS_QUESTIONS = [
    "During the last seven days, were you in the labour force, meaning either employed or, if not employed, seeking or available for work?",
    "During the last seven days, were you employed under the current-weekly-status rule, meaning you worked for at least one hour on at least one day in an economic activity, or otherwise retained an employment attachment counted as employed?",
    "During the last seven days, were you not employed but seeking or available for work?",
    "Was your current weekly employment status self-employed, including own-account worker, employer, or unpaid helper in a household enterprise?",
    "Was your current weekly employment status regular wage or salaried employee?",
    "Was your current weekly employment status casual labour?"
]


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def stable_select(rows: list[dict], n: int, seed: int) -> list[dict]:
    if n > len(rows):
        raise AssertionError(f"Requested {n} respondents from only {len(rows)}")
    keyed = sorted(rows, key=lambda r: hashlib.sha256(f"{seed}|{r['anon_id']}".encode()).hexdigest())
    return keyed[:n]


def cams_rows(bundle: Path = CAMS_CODES) -> list[dict]:
    raw = production_runtime.decrypt_bundle(bundle, production_runtime.CODES_AAD).decode("utf-8")
    rows = list(csv.DictReader(StringIO(raw)))
    if not rows or len({r["anon_id"] for r in rows}) != len(rows):
        raise AssertionError("CAMS code bundle has missing or duplicate respondent IDs")
    return rows


def plfs_rows() -> list[dict]:
    parts = sorted((ROOT / "data" / "encrypted").glob(PLFS_PARTS))
    if not parts:
        raise FileNotFoundError("PLFS full code bundle parts are missing")
    joined = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    tmp = Path("/tmp/plfs_followup_codes.b64")
    tmp.write_text(joined, encoding="ascii")
    rows = multisurvey_runtime.rows_from_bytes(multisurvey_runtime.decrypt_public_bundle(tmp, "plfs_2023_24", "codes"))
    if not rows or len({r["anon_id"] for r in rows}) != len(rows):
        raise AssertionError("PLFS code bundle has missing or duplicate respondent IDs")
    return rows


def cams_persona(raw: dict, condition: str) -> str:
    decoded = production_runtime.decode_row(raw)
    persona = prepare_sample.build_persona(decoded, condition)
    validate_persona(persona)
    return persona


def plfs_persona(r: dict) -> str:
    return (
        f"You are a {r['age']}-year-old {GENDER.get(r['gender'],'person')} living in a {SECTOR[r['sector']]} of {STATE.get(r['state'],'India')}. "
        f"You are {MARITAL.get(r['marital'],'of recorded marital status')}. You have completed {r['education_years']} years of formal education. "
        f"Your household has {r['hh_size']} members. Its social group is {SOCIAL.get(r['social_group'],'other social group')}. "
        f"Its usual monthly consumption expenditure is in the {Q[r['consumption_quintile']]} quintile among households in the same rural/urban sector."
    )


def build_plfs_prompt(persona: str) -> str:
    qs = "\n".join(f"{i+1}. {q}" for i, q in enumerate(PLFS_QUESTIONS))
    return (
        "You are completing a short labour-force survey as one specific person. Treat the profile below as the only known facts about that person. "
        "Do not answer as an average Indian, do not retrieve or reproduce government survey statistics, and do not add facts not in the profile. "
        "Give the response this particular person would most plausibly give. Keep the answers logically consistent. Do not explain your reasoning.\n\n"
        f"PERSON PROFILE\n{persona}\n\n"
        "Answer all six questions in order. In field a, return six integers where 1 means yes and 0 means no. "
        "In field p, return six numbers from 0 to 1 giving the probability this respondent would answer yes.\n\n"
        f"QUESTIONS\n{qs}\n"
    )


def source_assets(study: dict) -> dict[str, Path | None]:
    source = study["source"]
    if source == "cams_existing_1000":
        return {"codes": CAMS_CODES, "truth": CAMS_TRUTH}
    if source == "plfs_existing_1500":
        truth = ROOT / study["requires_truth"]
        return {"codes": None, "truth": truth}
    if source == "cams_fresh_holdout_v1":
        return {"codes": ROOT / study["requires_codes"], "truth": ROOT / study["requires_truth"]}
    raise ValueError(source)


def readiness(study_id: str) -> dict:
    reg = load_registry(); study = reg["studies"][study_id]
    assets = source_assets(study)
    missing = []
    if study["source"] == "plfs_existing_1500":
        parts = sorted((ROOT / "data" / "encrypted").glob(PLFS_PARTS))
        if not parts:
            missing.append("PLFS code bundle parts")
    elif assets["codes"] is not None and not assets["codes"].exists():
        missing.append(str(assets["codes"].relative_to(ROOT)))
    if assets["truth"] is not None and not assets["truth"].exists():
        missing.append(str(assets["truth"].relative_to(ROOT)))
    return {"study_id": study_id, "declared_status": study["status"], "missing_assets": missing, "data_ready": not missing}


def build_requests(study_id: str) -> list[dict]:
    reg = load_registry(); study = reg["studies"][study_id]
    ready = readiness(study_id)
    # Generation never reads truth, but a paid study is deliberately blocked if the analysis truth asset is absent.
    if not ready["data_ready"]:
        raise FileNotFoundError("Missing required study assets: " + ", ".join(ready["missing_assets"]))
    source = study["source"]
    if source in {"cams_existing_1000", "cams_fresh_holdout_v1"}:
        bundle = CAMS_CODES if source == "cams_existing_1000" else ROOT / study["requires_codes"]
        base = stable_select(cams_rows(bundle), int(study["respondents"]), int(study["selection_seed"]))
        persona_fn = lambda r, c: cams_persona(r, c)
        prompt_fn = build_cams_prompt
    elif source == "plfs_existing_1500":
        base = stable_select(plfs_rows(), int(study["respondents"]), int(study["selection_seed"]))
        persona_fn = lambda r, c: plfs_persona(r)
        prompt_fn = build_plfs_prompt
    else:
        raise ValueError(source)

    out = []
    schema_hash = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    for raw in base:
        for arm in study["arms"]:
            persona = persona_fn(raw, arm["persona"])
            prompt = prompt_fn(persona)
            row = {
                "study_id": study_id,
                "anon_id": raw["anon_id"],
                "arm_id": arm["id"],
                "persona_condition": arm["persona"],
                "model_key": arm["model"],
                "model": reg["models"][arm["model"]]["id"],
                "reasoning": arm["reasoning"],
                "max_completion_tokens": int(arm["max_completion_tokens"]),
                "prompt": prompt,
                "schema_sha256": schema_hash
            }
            rid_payload = {k: row[k] for k in ("study_id","anon_id","arm_id","model","reasoning","max_completion_tokens","schema_sha256")}
            rid_payload["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
            row["request_id"] = hashlib.sha256(json.dumps(rid_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            out.append(row)
    if len(out) != int(study["respondents"]) * len(study["arms"]):
        raise AssertionError("Wrong request count")
    if len({r["request_id"] for r in out}) != len(out):
        raise AssertionError("Duplicate request IDs")
    return out


def approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 3.2))


def static_report(study_id: str) -> dict:
    reg = load_registry(); study = reg["studies"][study_id]; ready = readiness(study_id)
    report = {**ready, "paid_inference_performed": False, "truth_loaded": False}
    if not ready["data_ready"]:
        report["status"] = "BLOCKED_DATA"
        return report
    rows = build_requests(study_id)
    by_model: dict[str, dict] = {}
    for r in rows:
        m = by_model.setdefault(r["model_key"], {"requests":0,"approx_input_tokens":0,"hard_completion_tokens":0})
        m["requests"] += 1; m["approx_input_tokens"] += approx_tokens(r["prompt"]); m["hard_completion_tokens"] += r["max_completion_tokens"]
    planning = 0.0
    for key, vals in by_model.items():
        model = reg["models"][key]
        vals["model"] = model["id"]
        vals["planning_price_usd_per_million"] = {"input":model["planning_input_usd_per_million"],"output":model["planning_output_usd_per_million"]}
        vals["planning_hard_ceiling_usd"] = vals["approx_input_tokens"] / 1e6 * model["planning_input_usd_per_million"] + vals["hard_completion_tokens"] / 1e6 * model["planning_output_usd_per_million"]
        planning += vals["planning_hard_ceiling_usd"]
    report.update({
        "status":"PASS_STATIC",
        "respondents":study["respondents"],
        "new_paid_requests":len(rows),
        "models":by_model,
        "planning_hard_ceiling_usd":round(planning,6),
        "study_spend_cap_usd":float(study["study_spend_cap_usd"]),
        "request_set_sha256":hashlib.sha256("\n".join(sorted(r["request_id"] for r in rows)).encode()).hexdigest(),
        "prompt_leakage_scan":"PASS" if source_assets(study).get("truth") else "NOT_APPLICABLE"
    })
    if planning > float(study["study_spend_cap_usd"]):
        report["status"] = "BLOCKED_BUDGET"
    return report


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("command",choices=["readiness","build","static"]); ap.add_argument("study_id"); ap.add_argument("--out")
    a=ap.parse_args()
    if a.command == "readiness": obj=readiness(a.study_id)
    elif a.command == "static": obj=static_report(a.study_id)
    else:
        rows=build_requests(a.study_id); obj={"study_id":a.study_id,"requests":len(rows),"respondents":len({r['anon_id'] for r in rows})}
        if not a.out: raise SystemExit("--out required for build")
        p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text("".join(json.dumps(r,separators=(",",":"),ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
    print(json.dumps(obj,indent=2,sort_keys=True))

if __name__ == "__main__":
    main()
