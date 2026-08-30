from __future__ import annotations

import argparse
import csv
import json
import sys
from io import StringIO
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RPF = ROOT / "reasoning_population_fidelity"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(RPF / "src"))

import production_runtime
from core import OUTCOMES
from resume_study1 import decrypt_seed_raw

TRUTH_BUNDLE = ROOT / "data" / "encrypted" / "cams_truth_v2.x25519.aesgcm.gz.b64"
CONDITIONS = ("off", "low", "medium")
SEED = 30082026
BOOT_REPS = 2000


def wmean(x: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(x * w) / np.sum(w))


def ci(xs: list[float]) -> list[float]:
    a = np.asarray(xs, dtype=float)
    return [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]


def condition_metrics(ids, pred, truth, weights, cond):
    w = np.asarray([weights[i] for i in ids], dtype=float)
    outcome_rows = {}
    respondent_brier = np.zeros(len(ids), dtype=float)
    respondent_acc = np.zeros(len(ids), dtype=float)
    respondent_sharp = np.zeros(len(ids), dtype=float)

    for outcome in OUTCOMES:
        y = np.asarray([truth[i][outcome] for i in ids], dtype=float)
        p = np.asarray([pred[(i, cond)][outcome]["probability_yes"] for i in ids], dtype=float)
        a = np.asarray([1.0 if pred[(i, cond)][outcome]["answer"] == "yes" else 0.0 for i in ids], dtype=float)
        brier = (p - y) ** 2
        acc = (a == y).astype(float)
        respondent_brier += brier / len(OUTCOMES)
        respondent_acc += acc / len(OUTCOMES)
        respondent_sharp += np.abs(p - 0.5) / len(OUTCOMES)
        tp = wmean(y, w)
        pp = wmean(p, w)
        hp = wmean(a, w)
        outcome_rows[outcome] = {
            "truth_prevalence": tp,
            "predicted_probability_prevalence": pp,
            "hard_yes_prevalence": hp,
            "probability_prevalence_abs_error": abs(pp - tp),
            "hard_prevalence_abs_error": abs(hp - tp),
            "brier": wmean(brier, w),
            "accuracy": wmean(acc, w),
            "mean_probability_sharpness_abs_p_minus_half": wmean(np.abs(p - 0.5), w),
        }

    return {
        "probability_prevalence_mae": float(np.mean([v["probability_prevalence_abs_error"] for v in outcome_rows.values()])),
        "hard_prevalence_mae": float(np.mean([v["hard_prevalence_abs_error"] for v in outcome_rows.values()])),
        "individual_brier": wmean(respondent_brier, w),
        "hard_accuracy": wmean(respondent_acc, w),
        "mean_probability_sharpness_abs_p_minus_half": wmean(respondent_sharp, w),
        "outcomes": outcome_rows,
        "_respondent_brier": respondent_brier,
        "_weights": w,
    }


def pair_change(ids, pred, c1, c2):
    w = np.asarray([1.0 for _ in ids])
    abs_pd = []
    hard_diff = []
    for i in ids:
        for outcome in OUTCOMES:
            p1 = float(pred[(i, c1)][outcome]["probability_yes"])
            p2 = float(pred[(i, c2)][outcome]["probability_yes"])
            a1 = pred[(i, c1)][outcome]["answer"]
            a2 = pred[(i, c2)][outcome]["answer"]
            abs_pd.append(abs(p2 - p1))
            hard_diff.append(1.0 if a1 != a2 else 0.0)
    return {
        "mean_abs_probability_change": float(np.mean(abs_pd)),
        "hard_answer_disagreement_rate": float(np.mean(hard_diff)),
    }


def bootstrap_contrast(ids, pred, truth, weights, c1, c2, reps=BOOT_REPS):
    rng = np.random.default_rng(SEED)
    n = len(ids)
    brier_diffs = []
    prev_mae_diffs = []
    for _ in range(reps):
        idx = rng.integers(0, n, size=n)
        bs_ids = [ids[j] for j in idx]
        w = np.asarray([weights[i] for i in bs_ids], dtype=float)
        rb = {}
        pmae = {}
        for cond in (c1, c2):
            person_brier = np.zeros(n, dtype=float)
            abs_prev = []
            for outcome in OUTCOMES:
                y = np.asarray([truth[i][outcome] for i in bs_ids], dtype=float)
                p = np.asarray([pred[(i, cond)][outcome]["probability_yes"] for i in bs_ids], dtype=float)
                person_brier += ((p - y) ** 2) / len(OUTCOMES)
                abs_prev.append(abs(wmean(p, w) - wmean(y, w)))
            rb[cond] = wmean(person_brier, w)
            pmae[cond] = float(np.mean(abs_prev))
        brier_diffs.append(rb[c2] - rb[c1])
        prev_mae_diffs.append(pmae[c2] - pmae[c1])
    return {
        "individual_brier_diff": {"estimate_direction": f"{c2}-{c1}", "ci95": ci(brier_diffs)},
        "probability_prevalence_mae_diff": {"estimate_direction": f"{c2}-{c1}", "ci95": ci(prev_mae_diffs)},
        "bootstrap_reps": reps,
        "seed": SEED,
    }


def run(seed_dir: Path, out_path: Path):
    api_key = __import__("os").environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY required as decryption secret")

    raw_rows = decrypt_seed_raw(seed_dir / "raw_results.enc.b64", api_key)
    pred = {(r["anon_id"], r["reasoning"]): r["response"] for r in raw_rows}
    by_cond = {c: {i for (i, cc) in pred if cc == c} for c in CONDITIONS}
    complete_ids = sorted(set.intersection(*(by_cond[c] for c in CONDITIONS)))

    truth_text = production_runtime.decrypt_bundle(TRUTH_BUNDLE, production_runtime.TRUTH_AAD).decode("utf-8")
    truth_rows = list(csv.DictReader(StringIO(truth_text)))
    truth = {}
    weights = {}
    for r in truth_rows:
        rid = r["anon_id"]
        truth[rid] = {o: int(float(r[o])) for o in OUTCOMES}
        weight_raw = r.get("analysis_weight") or r.get("MULT") or "1"
        weights[rid] = float(weight_raw)

    if not complete_ids:
        raise RuntimeError("No complete three-arm respondents in checkpoint")
    if not set(complete_ids).issubset(truth):
        raise RuntimeError("Prediction IDs do not match truth bundle")

    metrics = {c: condition_metrics(complete_ids, pred, truth, weights, c) for c in CONDITIONS}
    contrasts = {}
    for c1, c2 in (("off", "low"), ("off", "medium"), ("low", "medium")):
        bdiff = metrics[c2]["individual_brier"] - metrics[c1]["individual_brier"]
        pdiff = metrics[c2]["probability_prevalence_mae"] - metrics[c1]["probability_prevalence_mae"]
        adiff = metrics[c2]["hard_accuracy"] - metrics[c1]["hard_accuracy"]
        contrasts[f"{c2}_minus_{c1}"] = {
            "individual_brier_diff": bdiff,
            "probability_prevalence_mae_diff": pdiff,
            "hard_accuracy_diff": adiff,
            **pair_change(complete_ids, pred, c1, c2),
            "bootstrap": bootstrap_contrast(complete_ids, pred, truth, weights, c1, c2),
        }

    clean_metrics = {}
    for c, m in metrics.items():
        clean_metrics[c] = {k: v for k, v in m.items() if not k.startswith("_")}

    report = {
        "status": "INTERIM_ONLY_DO_NOT_USE_FOR_ENGINEERING",
        "checkpoint_schema_valid": len(raw_rows),
        "available_counts": {c: len(by_cond[c]) for c in CONDITIONS},
        "complete_case_respondents_all_three_arms": len(complete_ids),
        "analysis_population": "respondents with valid off, low, and medium outputs in the 2574-response checkpoint",
        "weighting": "frozen CAMS analysis_weight (fallback MULT only if absent)",
        "metrics": clean_metrics,
        "contrasts": contrasts,
        "interpretation_keys": {
            "individual_brier": "lower is better",
            "probability_prevalence_mae": "lower is better",
            "hard_accuracy": "higher is better",
            "contrast": "negative Brier/MAE difference favors the second-named arm; positive accuracy difference favors the second-named arm",
        },
        "warning": "Interim complete-case estimates can differ from the final 1000-person paired analysis because completion is not random. No engineering or treatment changes should be made from this report.",
        "plaintext_respondent_rows_emitted": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    run(args.seed_dir, args.out)
