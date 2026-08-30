from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd


def load_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]


def successes(path):
    out={}
    for r in load_jsonl(path):
        if 'error' not in r:
            out[(r['anon_id'],r['condition'])]=r
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--a',required=True)
    ap.add_argument('--b',required=True)
    ap.add_argument('--model-a',required=True)
    ap.add_argument('--model-b',required=True)
    ap.add_argument('--out',required=True)
    ap.add_argument('--bootstrap',type=int,default=5000)
    a=ap.parse_args()
    A=successes(a.a); B=successes(a.b)
    keys=sorted(set(A)&set(B))
    if not keys: raise AssertionError('No matched requests')
    outcomes=list(A[keys[0]]['response'])
    if set(outcomes)!=set(B[keys[0]]['response']): raise AssertionError('Outcome schema mismatch')
    rng=np.random.default_rng(20260830)
    rows=[]
    for condition in sorted({k[1] for k in keys}):
        ck=[k for k in keys if k[1]==condition]
        for outcome in outcomes:
            pa=np.asarray([float(A[k]['response'][outcome]['probability_yes']) for k in ck])
            pb=np.asarray([float(B[k]['response'][outcome]['probability_yes']) for k in ck])
            ya=np.asarray([A[k]['response'][outcome]['answer']=='yes' for k in ck])
            yb=np.asarray([B[k]['response'][outcome]['answer']=='yes' for k in ck])
            diff=pa-pb
            idx=rng.integers(0,len(ck),size=(a.bootstrap,len(ck)))
            boot=diff[idx].mean(axis=1)
            lo,hi=np.quantile(boot,[0.025,0.975])
            pearson=float(np.corrcoef(pa,pb)[0,1]) if np.std(pa)>0 and np.std(pb)>0 else None
            spearman=float(pd.Series(pa).corr(pd.Series(pb),method='spearman')) if len(pa)>1 else None
            rows.append({
                'condition':condition,'outcome':outcome,'n_matched':len(ck),
                f'{a.model_a}_probability_mean':float(pa.mean()),f'{a.model_b}_probability_mean':float(pb.mean()),
                f'{a.model_a}_minus_{a.model_b}_probability_mean':float(diff.mean()),
                'paired_difference_ci95_low':float(lo),'paired_difference_ci95_high':float(hi),
                'mean_absolute_probability_difference':float(np.abs(diff).mean()),
                f'{a.model_a}_yes_rate':float(ya.mean()),f'{a.model_b}_yes_rate':float(yb.mean()),
                'hard_answer_agreement':float((ya==yb).mean()),'probability_pearson':pearson,'probability_spearman':spearman
            })
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    m=pd.DataFrame(rows); m.to_csv(out/'outcome_metrics.csv',index=False)
    summary={
        'model_a':a.model_a,'model_b':a.model_b,'matched_requests':len(keys),
        'conditions':sorted({k[1] for k in keys}),'outcomes':outcomes,
        'mean_hard_answer_agreement':float(m.hard_answer_agreement.mean()),
        'mean_absolute_probability_difference':float(m.mean_absolute_probability_difference.mean()),
        'mean_directional_probability_difference_a_minus_b':float(m[f'{a.model_a}_minus_{a.model_b}_probability_mean'].mean()),
        'all_outcome_difference_cis_exclude_zero':bool(((m.paired_difference_ci95_low>0)&(m.paired_difference_ci95_high>0) | (m.paired_difference_ci95_low<0)&(m.paired_difference_ci95_high<0)).all())
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
