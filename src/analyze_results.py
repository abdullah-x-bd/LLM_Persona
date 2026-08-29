from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
OUTCOMES=["mobile_ability","mobile_3m","computer_ability","internet_ability","internet_3m","copy_paste"]
def wmean(x,w):x=np.asarray(x,float);w=np.asarray(w,float);return float(np.sum(x*w)/np.sum(w))
def load_jsonl(p):return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
def latest_successes(rows):
    keep={}
    for r in rows:
        if "error" in r:continue
        keep[(r["anon_id"],r["condition"])]=r
    return list(keep.values())
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--sample",required=True);ap.add_argument("--results",required=True);ap.add_argument("--out",required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);sample=pd.read_csv(a.sample);rows=latest_successes(load_jsonl(a.results))
    if not rows:raise ValueError("No successful model results")
    flat=[]
    for r in rows:
        for k in OUTCOMES:flat.append({"anon_id":r["anon_id"],"condition":r["condition"],"outcome":k,"pred":1 if r["response"][k]["answer"]=="yes" else 0,"prob":float(r["response"][k]["probability_yes"])})
    pred=pd.DataFrame(flat);truth=sample.melt(id_vars=["anon_id","analysis_weight","gender_binary","sector","age_group"],value_vars=OUTCOMES,var_name="outcome",value_name="actual");d=pred.merge(truth,on=["anon_id","outcome"],how="inner",validate="many_to_one");expected=len(sample)*len(OUTCOMES)*pred["condition"].nunique()
    if len(d)!=expected:raise AssertionError(f"Incomplete merge: {len(d)} != {expected}")
    metrics=[]
    for (cond,k),g in d.groupby(["condition","outcome"]):
        w=g.analysis_weight;actual=wmean(g.actual,w);hard=wmean(g.pred,w);prob=wmean(g.prob,w);acc=wmean((g.pred==g.actual).astype(float),w);sens=wmean(g.loc[g.actual==1,"pred"],g.loc[g.actual==1,"analysis_weight"]) if (g.actual==1).any() else np.nan;spec=wmean(1-g.loc[g.actual==0,"pred"],g.loc[g.actual==0,"analysis_weight"]) if (g.actual==0).any() else np.nan;brier=wmean((g.prob-g.actual)**2,w);majority=max(actual,1-actual)
        metrics.append({"condition":cond,"outcome":k,"actual_rate":actual,"hard_rate":hard,"probability_rate":prob,"hard_error_pp":100*(hard-actual),"probability_error_pp":100*(prob-actual),"hard_abs_error_pp":100*abs(hard-actual),"probability_abs_error_pp":100*abs(prob-actual),"weighted_accuracy":acc,"weighted_sensitivity":sens,"weighted_specificity":spec,"brier":brier,"majority_baseline_accuracy":majority})
    m=pd.DataFrame(metrics);m.to_csv(out/"outcome_metrics.csv",index=False);sub=[]
    for sg in ["gender_binary","sector","age_group"]:
        for (cond,k,level),g in d.groupby(["condition","outcome",sg]):sub.append({"subgroup":sg,"level":level,"condition":cond,"outcome":k,"actual_rate":wmean(g.actual,g.analysis_weight),"hard_rate":wmean(g.pred,g.analysis_weight),"probability_rate":wmean(g.prob,g.analysis_weight)})
    pd.DataFrame(sub).to_csv(out/"subgroup_estimates.csv",index=False);summary={}
    for cond,g in m.groupby("condition"):summary[cond]={"hard_MAE_pp":float(g.hard_abs_error_pp.mean()),"probability_MAE_pp":float(g.probability_abs_error_pp.mean()),"outcomes_within_5pp_hard":int((g.hard_abs_error_pp<=5).sum()),"outcomes_within_5pp_probability":int((g.probability_abs_error_pp<=5).sum()),"n_outcomes":int(len(g))}
    (out/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8");print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
