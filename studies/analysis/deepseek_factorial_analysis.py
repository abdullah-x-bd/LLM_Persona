from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import math
import os
import sys
from collections import Counter
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reasoning_population_fidelity" / "src"))

import production_runtime
from core import OUTCOMES

FOLLOWUP_AAD = b"LLM_PERSONA_FOLLOWUP_SUITE_V1"
TRUTH_BUNDLE = ROOT / "data" / "encrypted" / "cams_truth_v2.x25519.aesgcm.gz.b64"
CODES_BUNDLE = ROOT / "data" / "encrypted" / "cams_codes_v2.x25519.aesgcm.gz.b64"

ARMS = ("thin_off", "thin_high", "rich_off", "rich_high")
BOOT_REPS = 10_000
BOOT_SEED = 3108202603
EPS = 1e-6


def decrypt_followup(path: Path, key: str, study_id: str) -> list[dict]:
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    nonce, ciphertext = blob[:12], blob[12:]
    aes = hashlib.sha256(FOLLOWUP_AAD + b"|" + study_id.encode() + b"|" + key.encode()).digest()
    comp = AESGCM(aes).decrypt(nonce, ciphertext, FOLLOWUP_AAD + b"|" + study_id.encode())
    text = gzip.decompress(comp).decode("utf-8")
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def wmean(x: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(x * w) / np.sum(w))


def ece10(P: np.ndarray, Y: np.ndarray, w: np.ndarray) -> float:
    p = P.reshape(-1)
    y = Y.reshape(-1)
    ww = np.repeat(w, P.shape[1])
    bins = np.minimum((p * 10).astype(int), 9)
    den = float(ww.sum())
    total = 0.0
    for b in range(10):
        m = bins == b
        if not np.any(m):
            continue
        wb = ww[m]
        mass = float(wb.sum()) / den
        total += mass * abs(wmean(p[m], wb) - wmean(y[m], wb))
    return float(total)


def weighted_corr(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    wn = w / w.sum()
    mu = np.sum(X * wn[:, None], axis=0)
    xc = X - mu
    cov = (xc * wn[:, None]).T @ xc
    sd = np.sqrt(np.maximum(np.diag(cov), 1e-15))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    return corr


def pattern_dist(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    powers = (2 ** np.arange(X.shape[1] - 1, -1, -1)).astype(int)
    idx = X.astype(int) @ powers
    out = np.zeros(64, dtype=float)
    for i, wi in zip(idx, w):
        out[int(i)] += float(wi)
    out /= out.sum()
    return out


def entropy_bits(p: np.ndarray) -> float:
    q = p[p > 0]
    return float(-np.sum(q * np.log2(q)))


def js_bits(p: np.ndarray, q: np.ndarray) -> float:
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def cell_metrics(P: np.ndarray, A: np.ndarray, Y: np.ndarray, w: np.ndarray) -> dict:
    person_brier = np.mean((P - Y) ** 2, axis=1)
    pclip = np.clip(P, EPS, 1 - EPS)
    person_log = np.mean(-(Y * np.log(pclip) + (1 - Y) * np.log(1 - pclip)), axis=1)
    person_acc = np.mean(A == Y, axis=1)
    person_sharp = np.mean(np.abs(P - 0.5), axis=1)
    tp = np.sum(Y * w[:, None], axis=0) / w.sum()
    pp = np.sum(P * w[:, None], axis=0) / w.sum()
    hp = np.sum(A * w[:, None], axis=0) / w.sum()
    squared_bias = float(np.mean((pp - tp) ** 2))
    brier = wmean(person_brier, w)
    return {
        "individual_brier": brier,
        "log_loss": wmean(person_log, w),
        "hard_accuracy": wmean(person_acc, w),
        "probability_prevalence_mae": float(np.mean(np.abs(pp - tp))),
        "hard_prevalence_mae": float(np.mean(np.abs(hp - tp))),
        "mean_abs_p_minus_half": wmean(person_sharp, w),
        "ece10": ece10(P, Y, w),
        "mean_squared_population_bias": squared_bias,
        "mean_within_outcome_error_variance": float(brier - squared_bias),
        "mean_signed_probability_prevalence_bias": float(np.mean(pp - tp)),
        "truth_prevalence_mean": float(np.mean(tp)),
        "predicted_probability_prevalence_mean": float(np.mean(pp)),
        "hard_yes_prevalence_mean": float(np.mean(hp)),
    }


def outcome_metrics(P: np.ndarray, A: np.ndarray, Y: np.ndarray, w: np.ndarray) -> list[dict]:
    rows = []
    for j, outcome in enumerate(OUTCOMES):
        y, p, a = Y[:, j], P[:, j], A[:, j]
        tp, pp, hp = wmean(y, w), wmean(p, w), wmean(a, w)
        pclip = np.clip(p, EPS, 1 - EPS)
        rows.append({
            "outcome": outcome,
            "truth_prevalence": tp,
            "predicted_probability_prevalence": pp,
            "hard_yes_prevalence": hp,
            "probability_prevalence_abs_error": abs(pp - tp),
            "hard_prevalence_abs_error": abs(hp - tp),
            "brier": wmean((p - y) ** 2, w),
            "log_loss": wmean(-(y * np.log(pclip) + (1 - y) * np.log(1 - pclip)), w),
            "accuracy": wmean((a == y).astype(float), w),
            "mean_abs_p_minus_half": wmean(np.abs(p - 0.5), w),
        })
    return rows


def contrast_values(metrics: dict[str, dict], metric: str) -> dict[str, float]:
    t0, th, r0, rh = (metrics[a][metric] for a in ARMS)
    return {
        "reasoning_effect_thin_high_minus_off": th - t0,
        "reasoning_effect_rich_high_minus_off": rh - r0,
        "persona_effect_off_rich_minus_thin": r0 - t0,
        "persona_effect_high_rich_minus_thin": rh - th,
        "persona_x_reasoning_interaction": (rh - r0) - (th - t0),
    }


def bootstrap_all(P: dict[str, np.ndarray], A: dict[str, np.ndarray], Y: np.ndarray, w: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(BOOT_SEED)
    n = len(w)
    base_prob = np.full(n, 1.0 / n)
    rbrier = {a: np.mean((P[a] - Y) ** 2, axis=1) for a in ARMS}
    rlog = {}
    racc = {a: np.mean(A[a] == Y, axis=1) for a in ARMS}
    rsharp = {a: np.mean(np.abs(P[a] - 0.5), axis=1) for a in ARMS}
    for a in ARMS:
        pc = np.clip(P[a], EPS, 1 - EPS)
        rlog[a] = np.mean(-(Y * np.log(pc) + (1 - Y) * np.log(1 - pc)), axis=1)

    store: dict[tuple[str, str], list[np.ndarray]] = {}
    metrics = ("individual_brier", "log_loss", "hard_accuracy", "probability_prevalence_mae", "hard_prevalence_mae", "mean_abs_p_minus_half")
    contrast_names = (
        "reasoning_effect_thin_high_minus_off",
        "reasoning_effect_rich_high_minus_off",
        "persona_effect_off_rich_minus_thin",
        "persona_effect_high_rich_minus_thin",
        "persona_x_reasoning_interaction",
    )
    for metric in metrics:
        for c in contrast_names:
            store[(metric, c)] = []

    done = 0
    while done < BOOT_REPS:
        b = min(250, BOOT_REPS - done)
        counts = rng.multinomial(n, base_prob, size=b).astype(float)
        W = counts * w[None, :]
        den = W.sum(axis=1)
        truth_prev = (W @ Y) / den[:, None]
        vals: dict[str, dict[str, np.ndarray]] = {m: {} for m in metrics}
        for arm in ARMS:
            vals["individual_brier"][arm] = (W @ rbrier[arm]) / den
            vals["log_loss"][arm] = (W @ rlog[arm]) / den
            vals["hard_accuracy"][arm] = (W @ racc[arm]) / den
            vals["mean_abs_p_minus_half"][arm] = (W @ rsharp[arm]) / den
            pprev = (W @ P[arm]) / den[:, None]
            hprev = (W @ A[arm]) / den[:, None]
            vals["probability_prevalence_mae"][arm] = np.mean(np.abs(pprev - truth_prev), axis=1)
            vals["hard_prevalence_mae"][arm] = np.mean(np.abs(hprev - truth_prev), axis=1)
        for metric in metrics:
            t0, th, r0, rh = (vals[metric][a] for a in ARMS)
            derived = {
                "reasoning_effect_thin_high_minus_off": th - t0,
                "reasoning_effect_rich_high_minus_off": rh - r0,
                "persona_effect_off_rich_minus_thin": r0 - t0,
                "persona_effect_high_rich_minus_thin": rh - th,
                "persona_x_reasoning_interaction": (rh - r0) - (th - t0),
            }
            for c, arr in derived.items():
                store[(metric, c)].append(arr)
        done += b
        if done % 1000 == 0:
            print(json.dumps({"phase": "bootstrap", "completed": done, "total": BOOT_REPS}), flush=True)

    rows = []
    for (metric, contrast), chunks in store.items():
        x = np.concatenate(chunks)
        p2 = min(1.0, 2 * min(float(np.mean(x <= 0)), float(np.mean(x >= 0))))
        rows.append({
            "metric": metric,
            "contrast": contrast,
            "ci95_low": float(np.quantile(x, 0.025)),
            "ci95_high": float(np.quantile(x, 0.975)),
            "bootstrap_sign_p_two_sided": p2,
            "bootstrap_reps": BOOT_REPS,
            "seed": BOOT_SEED,
        })
    return pd.DataFrame(rows)


def subgroup_table(demo: pd.DataFrame, P: dict, A: dict, Y: np.ndarray, w: np.ndarray) -> pd.DataFrame:
    rows = []
    groupings = ["age_group", "gender", "sector", "mpce_band"]
    total_w = w.sum()
    for g in groupings:
        for level in sorted(demo[g].dropna().astype(str).unique()):
            mask = demo[g].astype(str).to_numpy() == level
            if mask.sum() < 15:
                continue
            mm = {arm: cell_metrics(P[arm][mask], A[arm][mask], Y[mask], w[mask]) for arm in ARMS}
            for metric in ("individual_brier", "probability_prevalence_mae", "hard_prevalence_mae", "hard_accuracy", "mean_abs_p_minus_half"):
                cv = contrast_values(mm, metric)
                rows.append({
                    "grouping": g,
                    "level": level,
                    "n": int(mask.sum()),
                    "weight_share": float(w[mask].sum() / total_w),
                    "metric": metric,
                    **{f"{arm}": mm[arm][metric] for arm in ARMS},
                    **cv,
                })
    return pd.DataFrame(rows)


def first_pass_success(attempts_path: Path) -> set[tuple[str, str]]:
    attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    return {(str(r["anon_id"]), str(r["arm_id"])) for r in attempts if int(r.get("attempt", 0)) == 1 and r.get("schema_valid") is True}


def make_results_md(metrics: dict, boot: pd.DataFrame, joint: dict, retry: dict) -> str:
    def pct(x): return f"{100*x:.2f} pp"
    lines = [
        "# DeepSeek S01 + S03 factorial results",
        "",
        "This report is generated from the complete 1,000-respondent four-cell DeepSeek factorial and the withheld CAMS human truth. Lower Brier, log loss, prevalence MAE, TV, and JS are better. Higher hard accuracy is better.",
        "",
        "## Cell metrics",
        "",
        "| Arm | Brier | Log loss | Hard accuracy | Prob. prevalence MAE | Hard prevalence MAE | |p-0.5| |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        m=metrics[arm]
        lines.append(f"| {arm} | {m['individual_brier']:.5f} | {m['log_loss']:.5f} | {100*m['hard_accuracy']:.2f}% | {100*m['probability_prevalence_mae']:.2f} pp | {100*m['hard_prevalence_mae']:.2f} pp | {m['mean_abs_p_minus_half']:.4f} |")
    lines += ["", "## Factorial contrasts", ""]
    for metric in ("individual_brier", "probability_prevalence_mae", "hard_prevalence_mae", "hard_accuracy"):
        cv=contrast_values(metrics, metric)
        lines.append(f"### {metric}")
        for k,v in cv.items():
            row=boot[(boot.metric==metric)&(boot.contrast==k)].iloc[0]
            scale=100 if "prevalence" in metric or metric=="hard_accuracy" else 1
            unit=" pp" if scale==100 else ""
            lines.append(f"- {k}: {v*scale:+.4f}{unit}, 95% bootstrap CI [{row.ci95_low*scale:+.4f}, {row.ci95_high*scale:+.4f}]{unit}")
        lines.append("")
    lines += [
        "## Joint-population structure",
        "",
        f"Human weighted entropy: {joint['human']['entropy_bits']:.4f} bits.",
    ]
    for arm in ARMS:
        j=joint[arm]
        lines.append(f"- {arm}: entropy {j['entropy_bits']:.4f}, TV from human {j['tv_from_human']:.4f}, JS {j['js_bits_from_human']:.4f}, largest archetype share {100*j['largest_pattern_share']:.2f}%.")
    lines += ["", "## Retry-process sensitivity", "", f"Respondents with first-pass-valid outputs in all four arms: {retry['all_four_first_pass_n']} / 1000.", ""]
    lines.append("The full 1,000-person factorial is the primary analysis. The all-four-first-pass subset is a post-treatment operational sensitivity check and must not replace the full-sample estimate.")
    return "\n".join(lines) + "\n"


def run(s01_dir: Path, s03_dir: Path, outdir: Path) -> dict:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY required only as decryption secret")
    s01_summary = json.loads((s01_dir / "summary.json").read_text())
    s03_summary = json.loads((s03_dir / "summary.json").read_text())
    assert s01_summary["schema_valid"] == 2000 and s01_summary["by_arm"] == {"rich_high":1000,"rich_off":1000}, s01_summary
    assert s03_summary["schema_valid"] == 2000 and s03_summary["by_arm"] == {"thin_high":1000,"thin_off":1000}, s03_summary
    assert s01_summary["truth_loaded"] is False and s03_summary["truth_loaded"] is False

    raw1 = decrypt_followup(s01_dir / "raw_results.enc.b64", key, "S01_second_model_reasoning")
    raw3 = decrypt_followup(s03_dir / "raw_results.enc.b64", key, "S03_persona_reasoning_factorial")
    all_raw = raw1 + raw3
    response = {(str(r["anon_id"]), str(r["arm_id"])): r["response"] for r in all_raw}
    ids = sorted({str(r["anon_id"]) for r in all_raw})
    assert len(ids) == 1000
    assert len(response) == 4000
    for rid in ids:
        assert all((rid, arm) in response for arm in ARMS)

    truth_text = production_runtime.decrypt_bundle(TRUTH_BUNDLE, production_runtime.TRUTH_AAD).decode("utf-8")
    truth_rows = list(csv.DictReader(StringIO(truth_text)))
    tmap = {str(r["anon_id"]): r for r in truth_rows}
    assert set(ids).issubset(tmap)
    Y = np.asarray([[int(float(tmap[rid][o])) for o in OUTCOMES] for rid in ids], dtype=float)
    w = np.asarray([float(tmap[rid].get("analysis_weight") or tmap[rid].get("MULT") or 1) for rid in ids], dtype=float)

    P, A = {}, {}
    for arm in ARMS:
        A[arm] = np.asarray([response[(rid, arm)]["a"] for rid in ids], dtype=float)
        P[arm] = np.asarray([response[(rid, arm)]["p"] for rid in ids], dtype=float)
        assert A[arm].shape == P[arm].shape == Y.shape == (1000, 6)

    codes_text = production_runtime.decrypt_bundle(CODES_BUNDLE, production_runtime.CODES_AAD).decode("utf-8")
    code_rows = list(csv.DictReader(StringIO(codes_text)))
    cmap = {str(r["anon_id"]): r for r in code_rows}
    demo_rows=[]
    for rid in ids:
        d=production_runtime.decode_row(cmap[rid])
        age_group = "15-24" if d.age < 25 else "25-34" if d.age < 35 else "35-44" if d.age < 45 else "45-59" if d.age < 60 else "60+"
        demo_rows.append({"anon_id":rid,"age":d.age,"age_group":age_group,"gender":d.gender,"sector":d.sector,"mpce_band":d.mpce_band})
    demo=pd.DataFrame(demo_rows)

    metrics={arm:cell_metrics(P[arm],A[arm],Y,w) for arm in ARMS}
    out_rows=[]
    for arm in ARMS:
        for r in outcome_metrics(P[arm],A[arm],Y,w):
            out_rows.append({"arm":arm,**r})
    outcome_df=pd.DataFrame(out_rows)

    effects=[]
    for outcome in OUTCOMES:
        block=outcome_df[outcome_df.outcome==outcome].set_index("arm")
        for metric in ("brier","log_loss","accuracy","probability_prevalence_abs_error","hard_prevalence_abs_error","mean_abs_p_minus_half"):
            vals={a:float(block.loc[a,metric]) for a in ARMS}
            cv=contrast_values({a:{metric:vals[a]} for a in ARMS},metric)
            effects.append({"outcome":outcome,"metric":metric,**{a:vals[a] for a in ARMS},**cv})
    effects_df=pd.DataFrame(effects)

    print(json.dumps({"phase":"bootstrap_start","reps":BOOT_REPS,"seed":BOOT_SEED}),flush=True)
    boot=bootstrap_all(P,A,Y,w)
    point_rows=[]
    for metric in boot.metric.unique():
        cv=contrast_values(metrics,metric)
        for c,v in cv.items(): point_rows.append({"metric":metric,"contrast":c,"estimate":v})
    point=pd.DataFrame(point_rows)
    boot=point.merge(boot,on=["metric","contrast"],how="left")

    human_dist=pattern_dist(Y,w); human_corr=weighted_corr(Y,w)
    joint={"human":{"entropy_bits":entropy_bits(human_dist),"distinct_patterns":int(np.sum(human_dist>0)),"largest_pattern_share":float(human_dist.max()),"top_patterns":[]}}
    for idx in np.argsort(human_dist)[::-1][:10]:
        if human_dist[idx]<=0: continue
        joint["human"]["top_patterns"].append({"pattern":format(int(idx),"06b"),"share":float(human_dist[idx])})
    for arm in ARMS:
        d=pattern_dist(A[arm],w); c=weighted_corr(A[arm],w)
        entry={"entropy_bits":entropy_bits(d),"distinct_patterns":int(np.sum(d>0)),"largest_pattern_share":float(d.max()),"tv_from_human":float(0.5*np.sum(np.abs(d-human_dist))),"js_bits_from_human":js_bits(d,human_dist),"correlation_rmse_from_human":float(np.sqrt(np.mean((c-human_corr)**2))),"top_patterns":[]}
        for idx in np.argsort(d)[::-1][:10]:
            if d[idx]<=0: continue
            entry["top_patterns"].append({"pattern":format(int(idx),"06b"),"share":float(d[idx]),"human_share":float(human_dist[idx])})
        joint[arm]=entry

    subgroup=subgroup_table(demo,P,A,Y,w)

    fp1=first_pass_success(s01_dir/"attempts.json"); fp3=first_pass_success(s03_dir/"attempts.json")
    fp=fp1|fp3
    rates={arm:sum((rid,arm) in fp for rid in ids)/len(ids) for arm in ARMS}
    all4=[rid for rid in ids if all((rid,arm) in fp for arm in ARMS)]
    retry={"first_pass_success_rate_by_arm":rates,"all_four_first_pass_n":len(all4),"all_four_first_pass_share":len(all4)/1000}
    if len(all4)>=100:
        pos=np.asarray([ids.index(rid) for rid in all4],dtype=int)
        sm={arm:cell_metrics(P[arm][pos],A[arm][pos],Y[pos],w[pos]) for arm in ARMS}
        retry["all_four_first_pass_metrics"]={a:{k:v for k,v in sm[a].items() if isinstance(v,(int,float))} for a in ARMS}
        retry["all_four_first_pass_contrasts"]={metric:contrast_values(sm,metric) for metric in ("individual_brier","probability_prevalence_mae","hard_prevalence_mae","hard_accuracy","log_loss","mean_abs_p_minus_half")}

    outdir.mkdir(parents=True,exist_ok=True)
    pd.DataFrame([{"arm":a,**metrics[a]} for a in ARMS]).to_csv(outdir/"cell_metrics.csv",index=False)
    outcome_df.to_csv(outdir/"outcome_metrics.csv",index=False)
    effects_df.to_csv(outdir/"outcome_factorial_effects.csv",index=False)
    boot.to_csv(outdir/"bootstrap_factorial_contrasts.csv",index=False)
    subgroup.to_csv(outdir/"subgroup_factorial.csv",index=False)
    (outdir/"joint_structure.json").write_text(json.dumps(joint,indent=2,sort_keys=True))
    (outdir/"retry_sensitivity.json").write_text(json.dumps(retry,indent=2,sort_keys=True))
    summary={
        "status":"COMPLETE_DEEPSEEK_FACTORIAL_ANALYSIS",
        "respondents":1000,
        "cells":{a:1000 for a in ARMS},
        "model":"deepseek/deepseek-v4-flash-0731",
        "provider":"OpenInference fp8",
        "truth":"withheld CAMS human outcomes loaded only after generation completion",
        "weighting":"CAMS analysis_weight",
        "bootstrap_reps":BOOT_REPS,
        "bootstrap_seed":BOOT_SEED,
        "cell_metrics":metrics,
        "factorial_contrasts":{metric:contrast_values(metrics,metric) for metric in ("individual_brier","log_loss","hard_accuracy","probability_prevalence_mae","hard_prevalence_mae","mean_abs_p_minus_half")},
        "joint_structure":joint,
        "retry_sensitivity":retry,
        "respondent_level_plaintext_emitted":False,
        "paid_inference_performed_in_analysis":False,
    }
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    (outdir/"RESULTS.md").write_text(make_results_md(metrics,boot,joint,retry),encoding="utf-8")
    print("DEEPSEEK_FACTORIAL_ANALYSIS_PASS",flush=True)
    print(json.dumps({"cell_metrics":metrics,"factorial_contrasts":summary["factorial_contrasts"],"retry_sensitivity":{"first_pass_success_rate_by_arm":rates,"all_four_first_pass_n":len(all4)}},indent=2),flush=True)
    return summary


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--s01-dir",type=Path,required=True)
    ap.add_argument("--s03-dir",type=Path,required=True)
    ap.add_argument("--outdir",type=Path,required=True)
    a=ap.parse_args(); run(a.s01_dir,a.s03_dir,a.outdir)
