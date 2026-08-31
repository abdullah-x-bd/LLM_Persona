from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import sys
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reasoning_population_fidelity" / "src"))

import production_runtime
from core import OUTCOMES

RPF_AAD = b"RPF_STUDY1_RESULTS_V1"
FOLLOWUP_AAD = b"LLM_PERSONA_FOLLOWUP_SUITE_V1"
EPS = 1e-6
BOOT_REPS = 10000
BOOT_SEED = 3108202691

CELL_META = {
    "luna_thin": ("Luna", "thin", "persona", 1000),
    "luna_rich": ("Luna", "rich", "persona", 1000),
    "claude_thin": ("Claude", "thin", "persona", 250),
    "claude_rich": ("Claude", "rich", "persona", 250),
    "qwen_off": ("Qwen", "off", "reasoning", 1000),
    "qwen_low": ("Qwen", "low", "reasoning", 1000),
    "qwen_medium": ("Qwen", "medium", "reasoning", 1000),
    "deepseek_thin_off": ("DeepSeek", "thin/off", "factorial", 1000),
    "deepseek_thin_high": ("DeepSeek", "thin/high", "factorial", 1000),
    "deepseek_rich_off": ("DeepSeek", "rich/off", "factorial", 1000),
    "deepseek_rich_high": ("DeepSeek", "rich/high", "factorial", 1000),
}


def wmean(x, w):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    return float(np.sum(x * w) / np.sum(w))


def response_arrays(obj):
    if isinstance(obj, dict) and set(obj) == {"a", "p"}:
        return np.asarray(obj["a"], int), np.asarray(obj["p"], float)
    a, p = [], []
    for o in OUTCOMES:
        v = obj[o]
        a.append(1 if v["answer"] == "yes" else 0)
        p.append(float(v["probability_yes"]))
    return np.asarray(a, int), np.asarray(p, float)


def load_jsonl(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def decrypt_qwen(path: Path, key: str):
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    nonce, cipher = blob[:12], blob[12:]
    aes_key = hashlib.sha256(RPF_AAD + b"|" + key.encode()).digest()
    text = gzip.decompress(AESGCM(aes_key).decrypt(nonce, cipher, RPF_AAD)).decode("utf-8")
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def decrypt_followup(path: Path, key: str, study_id: str):
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    nonce, cipher = blob[:12], blob[12:]
    aes_key = hashlib.sha256(FOLLOWUP_AAD + b"|" + study_id.encode() + b"|" + key.encode()).digest()
    aad = FOLLOWUP_AAD + b"|" + study_id.encode()
    text = gzip.decompress(AESGCM(aes_key).decrypt(nonce, cipher, aad)).decode("utf-8")
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def truth_and_demo():
    ttxt = production_runtime.decrypt_bundle(ROOT / "data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64", production_runtime.TRUTH_AAD).decode("utf-8")
    ctxt = production_runtime.decrypt_bundle(ROOT / "data/encrypted/cams_codes_v2.x25519.aesgcm.gz.b64", production_runtime.CODES_AAD).decode("utf-8")
    truth = pd.read_csv(StringIO(ttxt))
    codes = pd.read_csv(StringIO(ctxt), dtype=str)
    assert len(truth) == len(codes) == 1000
    d = truth.merge(codes, on="anon_id", how="left", validate="one_to_one", suffixes=("", "_code"))
    if "age_group" not in d.columns:
        age = pd.to_numeric(d["BL31C5"])
        d["age_group"] = pd.cut(age, bins=[14,24,34,44,59,np.inf], labels=["15-24","25-34","35-44","45-59","60+"]).astype(str)
    if "gender_binary" not in d.columns:
        d["gender_binary"] = d["BL31C4"].astype(str).map({"1":"male","2":"female"}).fillna(d["BL31C4"].astype(str))
    if "sector" not in d.columns:
        d["sector"] = d["SEC"].astype(str).map({"1":"rural","2":"urban"}).fillna(d["SEC"].astype(str))
    wcol = "analysis_weight" if "analysis_weight" in d.columns else "MULT"
    d[wcol] = pd.to_numeric(d[wcol], errors="raise")
    for o in OUTCOMES:
        d[o] = pd.to_numeric(d[o], errors="raise").astype(int)
    return d, wcol


def build_cell(rows, condition_field, condition_value, truth, wcol):
    subset = [r for r in rows if str(r[condition_field]) == condition_value and "error" not in r]
    byid = {str(r["anon_id"]): r["response"] for r in subset}
    ids = sorted(byid)
    Y = truth.set_index("anon_id").loc[ids, OUTCOMES].to_numpy(int)
    w = truth.set_index("anon_id").loc[ids, wcol].to_numpy(float)
    A, P = [], []
    for rid in ids:
        a, p = response_arrays(byid[rid])
        A.append(a); P.append(p)
    A = np.asarray(A, int); P = np.asarray(P, float)
    assert A.shape == P.shape == Y.shape == (len(ids), 6)
    return {"ids": ids, "A": A, "P": P, "Y": Y, "w": w}


def metrics(cell):
    P,A,Y,w = cell["P"],cell["A"],cell["Y"],cell["w"]
    person_b = np.mean((P-Y)**2, axis=1)
    pc = np.clip(P, EPS, 1-EPS)
    person_l = np.mean(-(Y*np.log(pc)+(1-Y)*np.log(1-pc)), axis=1)
    person_a = np.mean(A==Y, axis=1)
    tp = np.sum(Y*w[:,None],axis=0)/w.sum()
    pp = np.sum(P*w[:,None],axis=0)/w.sum()
    hp = np.sum(A*w[:,None],axis=0)/w.sum()
    return {
        "individual_brier": wmean(person_b,w),
        "log_loss": wmean(person_l,w),
        "hard_accuracy": wmean(person_a,w),
        "probability_prevalence_mae": float(np.mean(np.abs(pp-tp))),
        "hard_prevalence_mae": float(np.mean(np.abs(hp-tp))),
        "mean_abs_p_minus_half": wmean(np.mean(np.abs(P-.5),axis=1),w),
        "mean_signed_probability_bias": float(np.mean(pp-tp)),
    }


def outcome_metrics(cell, cell_id):
    P,A,Y,w = cell["P"],cell["A"],cell["Y"],cell["w"]
    rows=[]
    for j,o in enumerate(OUTCOMES):
        tp=wmean(Y[:,j],w);pp=wmean(P[:,j],w);hp=wmean(A[:,j],w)
        pc=np.clip(P[:,j],EPS,1-EPS)
        rows.append({
            "cell":cell_id,"outcome":o,
            "truth_prevalence":tp,"probability_prevalence":pp,"hard_prevalence":hp,
            "probability_prevalence_error":pp-tp,"hard_prevalence_error":hp-tp,
            "probability_prevalence_abs_error":abs(pp-tp),"hard_prevalence_abs_error":abs(hp-tp),
            "brier":wmean((P[:,j]-Y[:,j])**2,w),
            "log_loss":wmean(-(Y[:,j]*np.log(pc)+(1-Y[:,j])*np.log(1-pc)),w),
            "hard_accuracy":wmean((A[:,j]==Y[:,j]).astype(float),w),
        })
    return rows


def weighted_corr(X,w):
    wn=w/w.sum();mu=np.sum(X*wn[:,None],axis=0);xc=X-mu
    cov=(xc*wn[:,None]).T@xc;sd=np.sqrt(np.maximum(np.diag(cov),1e-15));corr=cov/np.outer(sd,sd);np.fill_diagonal(corr,1)
    return corr


def pattern_dist(X,w):
    codes=(X.astype(int)*(1<<np.arange(5,-1,-1))).sum(axis=1)
    out=np.zeros(64,float)
    for c,ww in zip(codes,w):out[int(c)]+=float(ww)
    out/=out.sum();return out


def entropy(p):
    q=p[p>0];return float(-np.sum(q*np.log2(q)))


def js(p,q):
    m=(p+q)/2
    def kl(a,b):
        z=a>0;return float(np.sum(a[z]*np.log2(a[z]/b[z])))
    return .5*kl(p,m)+.5*kl(q,m)


def joint_rows(cells):
    ref = cells["luna_thin"]
    human=pattern_dist(ref["Y"],ref["w"]);hc=weighted_corr(ref["Y"],ref["w"])
    rows=[{"cell":"human","entropy_bits":entropy(human),"distinct_patterns":int((human>0).sum()),"largest_pattern_share":float(human.max()),"joint_tv":0.0,"joint_js":0.0,"correlation_rmse":0.0}]
    patt=[]
    for k in range(64):patt.append({"cell":"human","pattern":format(k,"06b"),"share":float(human[k])})
    for cid,c in cells.items():
        d=pattern_dist(c["A"],c["w"]);cc=weighted_corr(c["A"],c["w"]);tri=np.triu_indices(6,1)
        rows.append({"cell":cid,"entropy_bits":entropy(d),"distinct_patterns":int((d>0).sum()),"largest_pattern_share":float(d.max()),"joint_tv":float(.5*np.abs(d-human).sum()),"joint_js":js(d,human),"correlation_rmse":float(np.sqrt(np.mean((cc[tri]-hc[tri])**2)))})
        for k in range(64):patt.append({"cell":cid,"pattern":format(k,"06b"),"share":float(d[k])})
    return pd.DataFrame(rows),pd.DataFrame(patt)


def align_pair(c1,c2):
    common=sorted(set(c1["ids"])&set(c2["ids"]));assert common
    def take(c):
        ix={rid:i for i,rid in enumerate(c["ids"])};pos=[ix[r] for r in common]
        return {k:(v[pos] if isinstance(v,np.ndarray) and len(v)==len(c["ids"]) else v) for k,v in c.items() if k!="ids"}|{"ids":common}
    return take(c1),take(c2)


def metric_values(cell, counts=None):
    P,A,Y,w=cell["P"],cell["A"],cell["Y"],cell["w"].copy()
    if counts is not None:w=w*counts
    return metrics({"P":P,"A":A,"Y":Y,"w":w})


def paired_bootstrap(c1,c2, metric_names, seed):
    a,b=align_pair(c1,c2);n=len(a["ids"]);rng=np.random.default_rng(seed);store={m:[] for m in metric_names}
    base1=metric_values(a);base2=metric_values(b)
    for _ in range(BOOT_REPS):
        s=rng.integers(0,n,size=n);counts=np.bincount(s,minlength=n).astype(float)
        m1=metric_values(a,counts);m2=metric_values(b,counts)
        for m in metric_names:store[m].append(m2[m]-m1[m])
    rows=[]
    for m in metric_names:
        arr=np.asarray(store[m]);rows.append({"metric":m,"estimate":base2[m]-base1[m],"ci_low":float(np.quantile(arr,.025)),"ci_high":float(np.quantile(arr,.975)),"n":n,"bootstrap_reps":BOOT_REPS})
    return rows


def fourway_heterogeneity(q0,q1,d0,d1,metric_names,seed):
    common=sorted(set(q0["ids"])&set(q1["ids"])&set(d0["ids"])&set(d1["ids"]));n=len(common);assert n==1000
    def subset(c):
        ix={rid:i for i,rid in enumerate(c["ids"])};pos=[ix[r] for r in common]
        return {"ids":common,"P":c["P"][pos],"A":c["A"][pos],"Y":c["Y"][pos],"w":c["w"][pos]}
    q0,q1,d0,d1=map(subset,(q0,q1,d0,d1));rng=np.random.default_rng(seed)
    base={x:metric_values(c) for x,c in [("q0",q0),("q1",q1),("d0",d0),("d1",d1)]}
    store={m:[] for m in metric_names}
    for _ in range(BOOT_REPS):
        s=rng.integers(0,n,size=n);counts=np.bincount(s,minlength=n).astype(float)
        v={x:metric_values(c,counts) for x,c in [("q0",q0),("q1",q1),("d0",d0),("d1",d1)]}
        for m in metric_names:store[m].append((v["d1"][m]-v["d0"][m])-(v["q1"][m]-v["q0"][m]))
    rows=[]
    for m in metric_names:
        est=(base["d1"][m]-base["d0"][m])-(base["q1"][m]-base["q0"][m]);arr=np.asarray(store[m])
        rows.append({"metric":m,"estimate":est,"ci_low":float(np.quantile(arr,.025)),"ci_high":float(np.quantile(arr,.975)),"n":n,"bootstrap_reps":BOOT_REPS})
    return rows


def subgroup_table(cells, truth, wcol):
    rows=[]
    for cid,c in cells.items():
        t=truth.set_index("anon_id").loc[c["ids"]]
        for var in ["age_group","gender_binary","sector"]:
            levels=list(pd.unique(t[var].astype(str)))
            for level in levels:
                mask=t[var].astype(str).to_numpy()==level
                if mask.sum()<10:continue
                P,A,Y,w=c["P"][mask],c["A"][mask],c["Y"][mask],c["w"][mask]
                tp=np.sum(Y*w[:,None],axis=0)/w.sum();pp=np.sum(P*w[:,None],axis=0)/w.sum();hp=np.sum(A*w[:,None],axis=0)/w.sum()
                rows.append({"cell":cid,"subgroup":var,"level":level,"n":int(mask.sum()),"individual_brier":wmean(np.mean((P-Y)**2,axis=1),w),"probability_prevalence_mae":float(np.mean(np.abs(pp-tp))),"hard_prevalence_mae":float(np.mean(np.abs(hp-tp))),"hard_accuracy":wmean(np.mean(A==Y,axis=1),w)})
    return pd.DataFrame(rows)


def age_reasoning_bootstrap(cells,truth):
    specs=[("Qwen","qwen_off","qwen_medium"),("DeepSeek","deepseek_rich_off","deepseek_rich_high")]
    out=[]
    for model,c0id,c1id in specs:
        c0,c1=align_pair(cells[c0id],cells[c1id]);t=truth.set_index("anon_id").loc[c0["ids"]]
        for ai,age in enumerate(["15-24","25-34","35-44","45-59","60+"]):
            mask=t.age_group.astype(str).to_numpy()==age;idx=np.where(mask)[0];n=len(idx)
            if n<20:continue
            a={"ids":[c0["ids"][i] for i in idx],"P":c0["P"][idx],"A":c0["A"][idx],"Y":c0["Y"][idx],"w":c0["w"][idx]}
            b={"ids":a["ids"],"P":c1["P"][idx],"A":c1["A"][idx],"Y":c1["Y"][idx],"w":c1["w"][idx]}
            for r in paired_bootstrap(a,b,["individual_brier","probability_prevalence_mae","hard_prevalence_mae","hard_accuracy"],BOOT_SEED+1000+ai+(0 if model=="Qwen" else 100)):
                out.append({"model":model,"age_group":age,**r})
    return pd.DataFrame(out)


def probability_tail(cells):
    rows=[]
    for cid in ["qwen_off","qwen_medium","deepseek_rich_off","deepseek_rich_high"]:
        c=cells[cid];P,Y,w=c["P"],c["Y"],c["w"]
        ww=np.repeat(w,6);p=P.reshape(-1);y=Y.reshape(-1);ll=-(y*np.log(np.clip(p,EPS,1-EPS))+(1-y)*np.log(np.clip(1-p,EPS,1-EPS)))
        wrong=((p>=.5)!=(y==1));extreme=(p<=.01)|(p>=.99)
        rows.append({"cell":cid,"extreme_share":wmean(extreme.astype(float),ww),"wrong_extreme_share":wmean((extreme&wrong).astype(float),ww),"exact_zero_one_share":wmean(((p==0)|(p==1)).astype(float),ww),"logloss_gt_2_share":wmean((ll>2).astype(float),ww),"logloss_gt_5_share":wmean((ll>5).astype(float),ww),"logloss_gt_10_share":wmean((ll>10).astype(float),ww)})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--luna-results",type=Path,required=True)
    ap.add_argument("--claude-results",type=Path,required=True)
    ap.add_argument("--qwen-dir",type=Path,required=True)
    ap.add_argument("--deepseek-s01-dir",type=Path,required=True)
    ap.add_argument("--deepseek-s03-dir",type=Path,required=True)
    ap.add_argument("--baseline-dir",type=Path,required=True)
    ap.add_argument("--outdir",type=Path,required=True)
    args=ap.parse_args();args.outdir.mkdir(parents=True,exist_ok=True)
    key=os.environ["OPENROUTER_API_KEY"]
    truth,wcol=truth_and_demo()

    luna=load_jsonl(args.luna_results);claude=load_jsonl(args.claude_results);qraw=decrypt_qwen(args.qwen_dir/"raw_results.enc.b64",key)
    d1=decrypt_followup(args.deepseek_s01_dir/"raw_results.enc.b64",key,"S01_second_model_reasoning")
    d3=decrypt_followup(args.deepseek_s03_dir/"raw_results.enc.b64",key,"S03_persona_reasoning_factorial")

    cells={
        "luna_thin":build_cell(luna,"condition","thin",truth,wcol),"luna_rich":build_cell(luna,"condition","rich",truth,wcol),
        "claude_thin":build_cell(claude,"condition","thin",truth,wcol),"claude_rich":build_cell(claude,"condition","rich",truth,wcol),
        "qwen_off":build_cell(qraw,"reasoning","off",truth,wcol),"qwen_low":build_cell(qraw,"reasoning","low",truth,wcol),"qwen_medium":build_cell(qraw,"reasoning","medium",truth,wcol),
        "deepseek_thin_off":build_cell(d3,"arm_id","thin_off",truth,wcol),"deepseek_thin_high":build_cell(d3,"arm_id","thin_high",truth,wcol),
        "deepseek_rich_off":build_cell(d1,"arm_id","rich_off",truth,wcol),"deepseek_rich_high":build_cell(d1,"arm_id","rich_high",truth,wcol),
    }
    assert len(cells["luna_thin"]["ids"])==1000 and len(cells["claude_thin"]["ids"])==250
    assert set(cells["luna_thin"]["ids"])==set(cells["qwen_off"]["ids"])==set(cells["deepseek_rich_off"]["ids"])

    cell_rows=[];out_rows=[]
    for cid,c in cells.items():
        model,condition,intervention,n=CELL_META[cid];cell_rows.append({"cell":cid,"method_class":"LLM","model":model,"condition":condition,"intervention":intervention,"n":n,**metrics(c)});out_rows.extend(outcome_metrics(c,cid))

    bm=pd.read_csv(args.baseline_dir/"baseline_metrics.csv")
    for _,r in bm.iterrows():
        cell_rows.append({"cell":"baseline_"+r.model,"method_class":"supervised_crossfit","model":r.model,"condition":"OOF","intervention":"supervised_reference","n":1000,**{k:float(r[k]) for k in ["individual_brier","log_loss","hard_accuracy","probability_prevalence_mae","hard_prevalence_mae","ece10","hard_pattern_entropy_bits","joint_tv","joint_js","hard_correlation_rmse"] if k in r and pd.notna(r[k])}})
    cell_df=pd.DataFrame(cell_rows)

    metrics_primary=["individual_brier","log_loss","hard_accuracy","probability_prevalence_mae","hard_prevalence_mae"]
    contrasts=[]
    specs=[
        ("luna_rich_minus_thin","luna_thin","luna_rich"),("claude_rich_minus_thin","claude_thin","claude_rich"),
        ("qwen_low_minus_off","qwen_off","qwen_low"),("qwen_medium_minus_off","qwen_off","qwen_medium"),
        ("deepseek_thin_high_minus_off","deepseek_thin_off","deepseek_thin_high"),("deepseek_rich_high_minus_off","deepseek_rich_off","deepseek_rich_high"),
        ("deepseek_persona_off_rich_minus_thin","deepseek_thin_off","deepseek_rich_off"),("deepseek_persona_high_rich_minus_thin","deepseek_thin_high","deepseek_rich_high"),
    ]
    for si,(name,a,b) in enumerate(specs):
        for r in paired_bootstrap(cells[a],cells[b],metrics_primary,BOOT_SEED+si):contrasts.append({"contrast":name,"first_cell":a,"second_cell":b,**r})

    het_ds=fourway_heterogeneity(cells["deepseek_thin_off"],cells["deepseek_thin_high"],cells["deepseek_rich_off"],cells["deepseek_rich_high"],metrics_primary,BOOT_SEED+50)
    for r in het_ds:contrasts.append({"contrast":"deepseek_persona_x_reasoning_interaction","first_cell":"thin reasoning effect","second_cell":"rich reasoning effect","direction_note":"(rich high-rich off) - (thin high-thin off)",**r})

    model_het=fourway_heterogeneity(cells["qwen_off"],cells["qwen_medium"],cells["deepseek_rich_off"],cells["deepseek_rich_high"],metrics_primary,BOOT_SEED+60)
    for r in model_het:contrasts.append({"contrast":"deepseek_minus_qwen_reasoning_effect","first_cell":"Qwen medium-off","second_cell":"DeepSeek high-off","direction_note":"DeepSeek reasoning effect - Qwen reasoning effect",**r})
    contrast_df=pd.DataFrame(contrasts)

    joint,patterns=joint_rows(cells)
    subgroup=subgroup_table(cells,truth,wcol)
    age=age_reasoning_bootstrap(cells,truth)
    tails=probability_tail(cells)
    outcome_df=pd.DataFrame(out_rows)

    oe=[]
    for name,a,b in [(x[0],x[1],x[2]) for x in specs]:
        ga=outcome_df[outcome_df.cell==a].set_index("outcome");gb=outcome_df[outcome_df.cell==b].set_index("outcome")
        for o in OUTCOMES:
            for m in ["brier","log_loss","hard_accuracy","probability_prevalence_abs_error","hard_prevalence_abs_error"]:
                oe.append({"contrast":name,"outcome":o,"metric":m,"effect":float(gb.loc[o,m]-ga.loc[o,m])})
    outcome_effects=pd.DataFrame(oe)

    cell_df.to_csv(args.outdir/"unified_cell_metrics.csv",index=False)
    contrast_df.to_csv(args.outdir/"unified_contrasts.csv",index=False)
    outcome_df.to_csv(args.outdir/"unified_outcome_metrics.csv",index=False)
    outcome_effects.to_csv(args.outdir/"unified_outcome_effects.csv",index=False)
    joint.to_csv(args.outdir/"unified_joint_metrics.csv",index=False)
    patterns.to_csv(args.outdir/"unified_pattern_distribution.csv",index=False)
    subgroup.to_csv(args.outdir/"unified_subgroup_metrics.csv",index=False)
    age.to_csv(args.outdir/"unified_age_reasoning_effects.csv",index=False)
    tails.to_csv(args.outdir/"unified_probability_tail.csv",index=False)
    evidence=contrast_df[contrast_df.contrast.isin(["luna_rich_minus_thin","claude_rich_minus_thin","qwen_medium_minus_off","deepseek_rich_high_minus_off","deepseek_persona_x_reasoning_interaction","deepseek_minus_qwen_reasoning_effect"])].copy()
    evidence.to_csv(args.outdir/"evidence_matrix.csv",index=False)

    summary={
        "status":"COMPLETE_FINAL_UNIFIED_CAMS_ANALYSIS",
        "llm_cells":11,
        "human_truth_respondents":1000,
        "claude_subset_respondents":250,
        "bootstrap_reps":BOOT_REPS,
        "bootstrap_seed":BOOT_SEED,
        "paid_inference_performed":False,
        "respondent_level_plaintext_emitted":False,
        "harmonization_note":"Cross-study metrics are recomputed with one common metric implementation and 1e-6 log-loss clipping. Frozen study-specific analyses remain authoritative for their preregistered primary results.",
        "supervised_baseline_note":"Supervised comparators are cross-fitted reference points, not information-regime-equivalent substitutes for zero-shot LLM simulation.",
        "integrity":{"luna":{k:len(cells[k]["ids"]) for k in ["luna_thin","luna_rich"]},"claude":{k:len(cells[k]["ids"]) for k in ["claude_thin","claude_rich"]},"qwen":{k:len(cells[k]["ids"]) for k in ["qwen_off","qwen_low","qwen_medium"]},"deepseek":{k:len(cells[k]["ids"]) for k in ["deepseek_thin_off","deepseek_thin_high","deepseek_rich_off","deepseek_rich_high"]}},
    }
    (args.outdir/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print("FINAL_UNIFIED_CAMS_ANALYSIS_PASS",flush=True)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=="__main__":main()
