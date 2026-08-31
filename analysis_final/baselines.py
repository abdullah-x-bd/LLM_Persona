from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import production_runtime

OUTCOMES = [
    "mobile_ability",
    "mobile_3m",
    "computer_ability",
    "internet_ability",
    "internet_3m",
    "copy_paste",
]
SEED = 31082026
OUTER_FOLDS = 10
INNER_FOLDS = 3
BOOT_REPS = 10000
EPS = 1e-6


def wmean(x, w):
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    return float(np.sum(x * w) / np.sum(w))


def wentropy(patterns, weights):
    df = pd.DataFrame({"p": patterns, "w": weights})
    shares = df.groupby("p", observed=True)["w"].sum().to_numpy(dtype=float)
    shares = shares / shares.sum()
    return float(-(shares * np.log2(shares)).sum()), int(len(shares)), float(shares.max())


def joint_dist(patterns, weights):
    df = pd.DataFrame({"p": patterns, "w": weights})
    s = df.groupby("p", observed=True)["w"].sum()
    s = s / s.sum()
    return s.to_dict()


def tv_js(d1, d2):
    keys = sorted(set(d1) | set(d2))
    p = np.array([d1.get(k, 0.0) for k in keys], dtype=float)
    q = np.array([d2.get(k, 0.0) for k in keys], dtype=float)
    tv = 0.5 * np.abs(p - q).sum()
    m = 0.5 * (p + q)
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    js = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    return float(tv), float(js)


def weighted_corr_matrix(mat, w):
    mat = np.asarray(mat, dtype=float)
    w = np.asarray(w, dtype=float)
    w = w / w.sum()
    mu = (mat * w[:, None]).sum(axis=0)
    xc = mat - mu
    cov = (xc * w[:, None]).T @ xc
    sd = np.sqrt(np.diag(cov))
    den = np.outer(sd, sd)
    corr = np.divide(cov, den, out=np.zeros_like(cov), where=den > 0)
    np.fill_diagonal(corr, 1.0)
    return corr


def ece10(y, p, w):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    w = np.asarray(w, dtype=float)
    bins = np.minimum((p * 10).astype(int), 9)
    total = w.sum()
    value = 0.0
    for b in range(10):
        m = bins == b
        if not m.any():
            continue
        wb = w[m]
        value += wb.sum() / total * abs(wmean(p[m], wb) - wmean(y[m], wb))
    return float(value)


def load_data(codes_path: Path, truth_path: Path):
    code_text = production_runtime.decrypt_bundle(codes_path, production_runtime.CODES_AAD).decode("utf-8")
    truth_text = production_runtime.decrypt_bundle(truth_path, production_runtime.TRUTH_AAD).decode("utf-8")
    codes = pd.read_csv(StringIO(code_text), dtype=str)
    truth = pd.read_csv(StringIO(truth_text))
    assert len(codes) == 1000 and len(truth) == 1000
    assert codes["anon_id"].nunique() == truth["anon_id"].nunique() == 1000
    assert set(codes["anon_id"]) == set(truth["anon_id"])
    leaked = sorted(set(OUTCOMES) & set(codes.columns))
    if leaked:
        raise RuntimeError(f"Target leakage columns present in codes bundle: {leaked}")
    data = truth.merge(codes, on="anon_id", how="inner", validate="one_to_one", suffixes=("", "_code"))
    weight_col = "analysis_weight" if "analysis_weight" in data.columns else "MULT"
    data[weight_col] = pd.to_numeric(data[weight_col], errors="raise").astype(float)
    features = [c for c in codes.columns if c != "anon_id"]
    if not features:
        raise RuntimeError("No persona-code predictors found")
    return data, features, weight_col


def make_preprocessor(X: pd.DataFrame):
    numeric = [c for c in X.columns if c in {"BL31C5", "BL41I1"}]
    categorical = [c for c in X.columns if c not in numeric]
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )


def weighted_brier(y, p, w):
    return wmean((np.asarray(p) - np.asarray(y)) ** 2, w)


def tune_logistic(X, y, w, candidates, seed):
    splitter = StratifiedKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=seed)
    scores = []
    for C in candidates:
        fold_scores = []
        for tr, va in splitter.split(X, y):
            pipe = Pipeline([
                ("prep", make_preprocessor(X.iloc[tr])),
                ("model", LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=5000)),
            ])
            pipe.fit(X.iloc[tr], y[tr], model__sample_weight=w[tr])
            p = pipe.predict_proba(X.iloc[va])[:, 1]
            fold_scores.append(weighted_brier(y[va], p, w[va]))
        scores.append((float(np.mean(fold_scores)), C))
    return min(scores)[1]


def tune_hgb(X, y, w, candidates, seed):
    splitter = StratifiedKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=seed)
    scores = []
    for leaves, min_leaf in candidates:
        fold_scores = []
        for tr, va in splitter.split(X, y):
            pipe = Pipeline([
                ("prep", make_preprocessor(X.iloc[tr])),
                ("model", HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_iter=250,
                    max_leaf_nodes=leaves,
                    min_samples_leaf=min_leaf,
                    l2_regularization=1.0,
                    random_state=seed,
                )),
            ])
            pipe.fit(X.iloc[tr], y[tr], model__sample_weight=w[tr])
            p = pipe.predict_proba(X.iloc[va])[:, 1]
            fold_scores.append(weighted_brier(y[va], p, w[va]))
        scores.append((float(np.mean(fold_scores)), (leaves, min_leaf)))
    return min(scores)[1]


def fit_oof(data, features, weight_col):
    X = data[features].copy()
    for c in X.columns:
        if c in {"BL31C5", "BL41I1"}:
            X[c] = pd.to_numeric(X[c], errors="coerce")
            X[c] = X[c].fillna(X[c].median())
        else:
            X[c] = X[c].fillna("MISSING").astype(str)
    w_all = data[weight_col].to_numpy(dtype=float)
    ids = data["anon_id"].astype(str).to_numpy()
    out_rows = []
    tuning_rows = []
    logit_grid = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]
    hgb_grid = [(7, 20), (15, 20), (15, 40), (31, 20), (31, 40)]

    for oi, outcome in enumerate(OUTCOMES):
        y = data[outcome].to_numpy(dtype=int)
        splitter = StratifiedKFold(n_splits=OUTER_FOLDS, shuffle=True, random_state=SEED + oi)
        preds = {
            "weighted_prevalence": np.full(len(data), np.nan),
            "logistic": np.full(len(data), np.nan),
            "gradient_boosting": np.full(len(data), np.nan),
            "random_forest": np.full(len(data), np.nan),
        }
        for fold, (tr, te) in enumerate(splitter.split(X, y)):
            seed = SEED + oi * 100 + fold
            p0 = wmean(y[tr], w_all[tr])
            preds["weighted_prevalence"][te] = p0

            C = tune_logistic(X.iloc[tr], y[tr], w_all[tr], logit_grid, seed)
            logit = Pipeline([
                ("prep", make_preprocessor(X.iloc[tr])),
                ("model", LogisticRegression(C=C, penalty="l2", solver="lbfgs", max_iter=5000)),
            ])
            logit.fit(X.iloc[tr], y[tr], model__sample_weight=w_all[tr])
            preds["logistic"][te] = logit.predict_proba(X.iloc[te])[:, 1]

            leaves, min_leaf = tune_hgb(X.iloc[tr], y[tr], w_all[tr], hgb_grid, seed)
            hgb = Pipeline([
                ("prep", make_preprocessor(X.iloc[tr])),
                ("model", HistGradientBoostingClassifier(
                    learning_rate=0.05,
                    max_iter=250,
                    max_leaf_nodes=leaves,
                    min_samples_leaf=min_leaf,
                    l2_regularization=1.0,
                    random_state=seed,
                )),
            ])
            hgb.fit(X.iloc[tr], y[tr], model__sample_weight=w_all[tr])
            preds["gradient_boosting"][te] = hgb.predict_proba(X.iloc[te])[:, 1]

            rf = Pipeline([
                ("prep", make_preprocessor(X.iloc[tr])),
                ("model", RandomForestClassifier(
                    n_estimators=600,
                    min_samples_leaf=8,
                    max_features="sqrt",
                    n_jobs=-1,
                    random_state=seed,
                )),
            ])
            rf.fit(X.iloc[tr], y[tr], model__sample_weight=w_all[tr])
            preds["random_forest"][te] = rf.predict_proba(X.iloc[te])[:, 1]
            tuning_rows.append({
                "outcome": outcome,
                "fold": fold,
                "logistic_C": C,
                "hgb_max_leaf_nodes": leaves,
                "hgb_min_samples_leaf": min_leaf,
            })

        for model, pp in preds.items():
            if np.isnan(pp).any():
                raise RuntimeError(f"Missing OOF predictions for {model} {outcome}")
            for rid, yy, ww, prob in zip(ids, y, w_all, pp):
                out_rows.append({
                    "anon_id": rid,
                    "outcome": outcome,
                    "model": model,
                    "truth": int(yy),
                    "weight": float(ww),
                    "probability": float(prob),
                    "hard": int(prob >= 0.5),
                })
    pred = pd.DataFrame(out_rows)
    tuning = pd.DataFrame(tuning_rows)
    return pred, tuning


def metrics_from_long(pred: pd.DataFrame):
    model_rows = []
    outcome_rows = []
    for model, g in pred.groupby("model", observed=True):
        per_out = []
        for outcome, h in g.groupby("outcome", observed=True):
            y = h.truth.to_numpy(dtype=float)
            p = h.probability.to_numpy(dtype=float)
            a = h.hard.to_numpy(dtype=float)
            w = h.weight.to_numpy(dtype=float)
            tp, pp, hp = wmean(y, w), wmean(p, w), wmean(a, w)
            row = {
                "model": model,
                "outcome": outcome,
                "truth_prevalence": tp,
                "probability_prevalence": pp,
                "hard_prevalence": hp,
                "probability_prevalence_abs_error": abs(pp - tp),
                "hard_prevalence_abs_error": abs(hp - tp),
                "brier": weighted_brier(y, p, w),
                "log_loss": wmean(-(y * np.log(np.clip(p, EPS, 1-EPS)) + (1-y) * np.log(np.clip(1-p, EPS, 1-EPS))), w),
                "hard_accuracy": wmean((a == y).astype(float), w),
                "ece10": ece10(y, p, w),
            }
            outcome_rows.append(row)
            per_out.append(row)

        gg = g.copy()
        gg["item_sqerr"] = (gg.probability - gg.truth) ** 2
        gg["item_logloss"] = -(gg.truth * np.log(np.clip(gg.probability, EPS, 1-EPS)) + (1-gg.truth) * np.log(np.clip(1-gg.probability, EPS, 1-EPS)))
        row = {
            "model": model,
            "individual_brier": wmean(gg.item_sqerr, gg.weight),
            "log_loss": wmean(gg.item_logloss, gg.weight),
            "hard_accuracy": wmean((gg.hard == gg.truth).astype(float), gg.weight),
            "probability_prevalence_mae": float(np.mean([r["probability_prevalence_abs_error"] for r in per_out])),
            "hard_prevalence_mae": float(np.mean([r["hard_prevalence_abs_error"] for r in per_out])),
            "ece10": float(np.mean([r["ece10"] for r in per_out])),
        }

        wide = g.pivot(index="anon_id", columns="outcome", values="hard").reindex(columns=OUTCOMES)
        yt = g.pivot(index="anon_id", columns="outcome", values="truth").reindex(columns=OUTCOMES)
        ww = g.drop_duplicates("anon_id").set_index("anon_id")["weight"].reindex(wide.index).to_numpy(dtype=float)
        patt = wide.astype(int).astype(str).agg("".join, axis=1).to_numpy()
        truth_patt = yt.astype(int).astype(str).agg("".join, axis=1).to_numpy()
        ent, n_patt, max_share = wentropy(patt, ww)
        t_ent, t_n, t_max = wentropy(truth_patt, ww)
        tv, js = tv_js(joint_dist(patt, ww), joint_dist(truth_patt, ww))
        corr = weighted_corr_matrix(wide.to_numpy(dtype=float), ww)
        tcorr = weighted_corr_matrix(yt.to_numpy(dtype=float), ww)
        tri = np.triu_indices(len(OUTCOMES), 1)
        row.update({
            "hard_pattern_entropy_bits": ent,
            "hard_distinct_patterns": n_patt,
            "largest_hard_pattern_share": max_share,
            "joint_tv": tv,
            "joint_js": js,
            "hard_correlation_rmse": float(np.sqrt(np.mean((corr[tri] - tcorr[tri]) ** 2))),
            "human_entropy_bits": t_ent,
            "human_distinct_patterns": t_n,
            "human_largest_pattern_share": t_max,
        })
        model_rows.append(row)
    return pd.DataFrame(model_rows), pd.DataFrame(outcome_rows)


def subgroup_metrics(pred: pd.DataFrame, truth: pd.DataFrame):
    attrs = [c for c in ["gender_binary", "sector", "age_group"] if c in truth.columns]
    d = pred.merge(truth[["anon_id"] + attrs], on="anon_id", how="left", validate="many_to_one")
    rows = []
    for attr in attrs:
        for (model, level, outcome), g in d.groupby(["model", attr, "outcome"], observed=True):
            w = g.weight.to_numpy(dtype=float)
            y = g.truth.to_numpy(dtype=float)
            p = g.probability.to_numpy(dtype=float)
            a = g.hard.to_numpy(dtype=float)
            rows.append({
                "model": model,
                "subgroup": attr,
                "level": str(level),
                "outcome": outcome,
                "n": int(len(g)),
                "truth_prevalence": wmean(y, w),
                "probability_prevalence": wmean(p, w),
                "hard_prevalence": wmean(a, w),
                "brier": weighted_brier(y, p, w),
            })
    return pd.DataFrame(rows)


def bootstrap(pred: pd.DataFrame, reps=BOOT_REPS):
    ids = sorted(pred.anon_id.unique())
    models = sorted(pred.model.unique())
    n = len(ids)
    mats = {}
    for model in models:
        g = pred[pred.model == model]
        p = g.pivot(index="anon_id", columns="outcome", values="probability").reindex(index=ids, columns=OUTCOMES).to_numpy(float)
        a = g.pivot(index="anon_id", columns="outcome", values="hard").reindex(index=ids, columns=OUTCOMES).to_numpy(float)
        y = g.pivot(index="anon_id", columns="outcome", values="truth").reindex(index=ids, columns=OUTCOMES).to_numpy(float)
        w = g.drop_duplicates("anon_id").set_index("anon_id")["weight"].reindex(ids).to_numpy(float)
        mats[model] = (p, a, y, w)
    rng = np.random.default_rng(SEED + 99)
    store = {m: {k: [] for k in ["individual_brier", "log_loss", "hard_accuracy", "probability_prevalence_mae", "hard_prevalence_mae"]} for m in models}
    for r in range(reps):
        idx = rng.integers(0, n, size=n)
        for model in models:
            p, a, y, w = mats[model]
            pp, aa, yy, ww = p[idx], a[idx], y[idx], w[idx]
            ww2 = ww[:, None]
            denom = ww.sum()
            store[model]["individual_brier"].append(float(np.sum(((pp-yy)**2) * ww2) / (denom * len(OUTCOMES))))
            ll = -(yy*np.log(np.clip(pp, EPS, 1-EPS)) + (1-yy)*np.log(np.clip(1-pp, EPS, 1-EPS)))
            store[model]["log_loss"].append(float(np.sum(ll * ww2) / (denom * len(OUTCOMES))))
            store[model]["hard_accuracy"].append(float(np.sum((aa==yy) * ww2) / (denom * len(OUTCOMES))))
            tprev = np.sum(yy * ww2, axis=0) / denom
            pprev = np.sum(pp * ww2, axis=0) / denom
            hprev = np.sum(aa * ww2, axis=0) / denom
            store[model]["probability_prevalence_mae"].append(float(np.mean(np.abs(pprev-tprev))))
            store[model]["hard_prevalence_mae"].append(float(np.mean(np.abs(hprev-tprev))))
        if (r + 1) % 1000 == 0:
            print(json.dumps({"phase": "bootstrap", "completed": r+1, "total": reps}), flush=True)
    rows = []
    for model in models:
        for metric, vals in store[model].items():
            arr = np.asarray(vals)
            rows.append({
                "model": model,
                "metric": metric,
                "ci_low": float(np.quantile(arr, .025)),
                "ci_high": float(np.quantile(arr, .975)),
                "bootstrap_reps": reps,
                "seed": SEED + 99,
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", type=Path, default=ROOT / "data/encrypted/cams_codes_v2.x25519.aesgcm.gz.b64")
    ap.add_argument("--truth", type=Path, default=ROOT / "data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64")
    ap.add_argument("--outdir", type=Path, required=True)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    data, features, weight_col = load_data(args.codes, args.truth)
    pred, tuning = fit_oof(data, features, weight_col)
    metrics, outcome = metrics_from_long(pred)
    subgroup = subgroup_metrics(pred, data)
    boot = bootstrap(pred)

    metrics.to_csv(args.outdir / "baseline_metrics.csv", index=False)
    outcome.to_csv(args.outdir / "baseline_outcome_metrics.csv", index=False)
    subgroup.to_csv(args.outdir / "baseline_subgroup_metrics.csv", index=False)
    tuning.to_csv(args.outdir / "baseline_tuning.csv", index=False)
    boot.to_csv(args.outdir / "baseline_bootstrap.csv", index=False)
    summary = {
        "status": "COMPLETE_CROSSFITTED_SUPERVISED_BASELINES",
        "respondents": 1000,
        "outcomes": OUTCOMES,
        "outer_folds": OUTER_FOLDS,
        "inner_folds": INNER_FOLDS,
        "bootstrap_reps": BOOT_REPS,
        "seed": SEED,
        "predictor_columns": features,
        "models": sorted(metrics.model.tolist()),
        "truth_loaded": True,
        "paid_inference_performed": False,
        "respondent_level_plaintext_emitted": False,
        "interpretation": "Cross-fitted supervised comparators trained on held-out human outcomes. They are not information-regime-equivalent to zero-shot LLM simulation and are reported as supervised reference points.",
        "metrics": metrics.set_index("model").to_dict(orient="index"),
    }
    (args.outdir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CROSSFITTED_BASELINES_PASS", flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
