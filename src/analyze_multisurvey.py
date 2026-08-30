from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

def load_jsonl(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines() if x.strip()]
def wmean(x,w):
    x=np.asarray(x,float);w=np.asarray(w,float);return float(np.sum(x*w)/np.sum(w))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--truth',required=True);ap.add_argument('--results',required=True);ap.add_argument('--schema',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);schema=json.loads(Path(a.schema).read_text());outs=schema['required']
    truth=pd.DataFrame(load_jsonl(a.truth)); results={}
    for r in load_jsonl(a.results):
        if 'error' not in r:results[(r['anon_id'],r['condition'])]=r
    rows=list(results.values())
    if len(rows)!=len(truth):raise AssertionError(f'Expected {len(truth)} results, got {len(rows)}')
    flat=[]
    for r in rows:
        for k in outs:flat.append({'anon_id':r['anon_id'],'condition':r['condition'],'outcome':k,'pred':int(r['response'][k]['answer']=='yes'),'prob':float(r['response'][k]['probability_yes'])})
    pred=pd.DataFrame(flat); idcols=[c for c in ['anon_id','weight','gender','sector','age'] if c in truth.columns]
    tv=truth.melt(id_vars=idcols,value_vars=outs,var_name='outcome',value_name='actual');d=pred.merge(tv,on=['anon_id','outcome'],validate='many_to_one')
    if 'weight' not in d.columns:d['weight']=1.0
    metrics=[]
    for (cond,k),g in d.groupby(['condition','outcome']):
        actual=wmean(g.actual,g.weight); hard=wmean(g.pred,g.weight); prob=wmean(g.prob,g.weight); acc=wmean((g.pred==g.actual).astype(float),g.weight); brier=wmean((g.prob-g.actual)**2,g.weight)
        metrics.append({'condition':cond,'outcome':k,'actual_rate':actual,'hard_rate':hard,'probability_rate':prob,'hard_error_pp':100*(hard-actual),'probability_error_pp':100*(prob-actual),'hard_abs_error_pp':100*abs(hard-actual),'probability_abs_error_pp':100*abs(prob-actual),'weighted_accuracy':acc,'brier':brier,'majority_baseline_accuracy':max(actual,1-actual)})
    m=pd.DataFrame(metrics);m.to_csv(out/'outcome_metrics.csv',index=False);subs=[]
    for sg in [x for x in ['gender','sector'] if x in d.columns]:
        for (cond,k,level),g in d.groupby(['condition','outcome',sg]):subs.append({'subgroup':sg,'level':level,'condition':cond,'outcome':k,'actual_rate':wmean(g.actual,g.weight),'hard_rate':wmean(g.pred,g.weight),'probability_rate':wmean(g.prob,g.weight)})
    if 'age' in d.columns:
        d['age_group']=pd.cut(d.age,[-1,29,44,59,200],labels=['15-29','30-44','45-59','60+'])
        for (cond,k,level),g in d.groupby(['condition','outcome','age_group'],observed=True):subs.append({'subgroup':'age_group','level':str(level),'condition':cond,'outcome':k,'actual_rate':wmean(g.actual,g.weight),'hard_rate':wmean(g.pred,g.weight),'probability_rate':wmean(g.prob,g.weight)})
    pd.DataFrame(subs).to_csv(out/'subgroup_estimates.csv',index=False);summary={}
    for cond,g in m.groupby('condition'):summary[cond]={'hard_MAE_pp':float(g.hard_abs_error_pp.mean()),'probability_MAE_pp':float(g.probability_abs_error_pp.mean()),'outcomes_within_5pp_hard':int((g.hard_abs_error_pp<=5).sum()),'outcomes_within_5pp_probability':int((g.probability_abs_error_pp<=5).sum()),'n_outcomes':int(len(g))}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
