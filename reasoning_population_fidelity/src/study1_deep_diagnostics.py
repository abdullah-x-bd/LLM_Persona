from __future__ import annotations

import argparse,csv,json,os,sys
from collections import defaultdict
from io import StringIO
from pathlib import Path
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(HERE/'src'))
import production_runtime as legacy_runtime
from core import OUTCOMES
from final_analysis_study1 import decrypt_rpf,response_arrays,wmean

CONDITIONS=['off','low','medium'];EXPECTED='120cc6bef15e7b2eb8fb2c49c7efa2fab5496b0a429cf34c8d9100b588cf9293'

def wcorr(x,y,w):
    mx=wmean(x,w);my=wmean(y,w);vx=wmean((x-mx)**2,w);vy=wmean((y-my)**2,w)
    if vx<=1e-15 or vy<=1e-15:return np.nan
    return wmean((x-mx)*(y-my),w)/np.sqrt(vx*vy)

def code(mat):return (mat.astype(int)*(1<<np.arange(5,-1,-1))).sum(axis=1)

def load(artifact,key):
    s=json.load(open(artifact/'study1_summary.json'));assert s['all_schema_valid'] and s['freeze_requests_sha256']==EXPECTED
    raw=decrypt_rpf(artifact/'raw_results.enc.b64',key);attempts=json.load(open(artifact/'attempt_history.json'))
    tt=legacy_runtime.decrypt_bundle(ROOT/'data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64',legacy_runtime.TRUTH_AAD).decode()
    t=pd.DataFrame(list(csv.DictReader(StringIO(tt))))
    for c in t.columns:
        if c!='anon_id':
            try:t[c]=pd.to_numeric(t[c])
            except:pass
    t=t.sort_values('anon_id').reset_index(drop=True);ids=t.anon_id.tolist();ix={a:i for i,a in enumerate(ids)}
    w=t.analysis_weight.astype(float).to_numpy();w=w/w.sum();y=t[OUTCOMES].astype(int).to_numpy()
    p={c:np.zeros((1000,6)) for c in CONDITIONS};h={c:np.zeros((1000,6),int) for c in CONDITIONS}
    ridmap={}
    for r in raw:
        i=ix[r['anon_id']];a,pp=response_arrays(r['response']);p[r['reasoning']][i]=pp;h[r['reasoning']][i]=a;ridmap[r['request_id']]=(r['anon_id'],r['reasoning'])
    return t,ids,w,y,p,h,attempts,ridmap

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact-dir',required=True,type=Path);ap.add_argument('--outdir',required=True,type=Path);args=ap.parse_args();args.outdir.mkdir(parents=True,exist_ok=True)
    t,ids,w,y,p,h,attempts,ridmap=load(args.artifact_dir,os.environ['OPENROUTER_API_KEY']);idix={a:i for i,a in enumerate(ids)}

    # Length-failure composition.
    length=defaultdict(set)
    for a in attempts:
        if a.get('schema_valid'):continue
        if a.get('finish_reason')!='length' and a.get('meta_finish_reason')!='length':continue
        anon=a.get('anon_id');c=a.get('reasoning')
        if anon and c in CONDITIONS:length[c].add(anon)
    lf=[]
    for c in ['low','medium']:
        flag=np.array([a in length[c] for a in ids])
        lf.append({'condition':c,'subgroup_variable':'overall','group':'all','n':1000,'unweighted_length_failure_rate':flag.mean(),'survey_weighted_length_failure_rate':wmean(flag.astype(float),w)})
        for var,groups in [('sector',['rural','urban']),('gender_binary',['male','female']),('age_group',['15-24','25-34','35-44','45-59','60+'])]:
            vals=t[var].astype(str).to_numpy()
            for g in groups:
                m=vals==g
                if not m.any():continue
                ww=w*m
                lf.append({'condition':c,'subgroup_variable':var,'group':g,'n':int(m.sum()),'unweighted_length_failure_rate':flag[m].mean(),'survey_weighted_length_failure_rate':wmean(flag.astype(float),ww)})
    pd.DataFrame(lf).to_csv(args.outdir/'length_failure_demographics.csv',index=False)

    # Pairwise joint-structure correlations.
    corr=[];mats={'human':y,**{c:h[c] for c in CONDITIONS}}
    for label,mat in mats.items():
        vals=[]
        for j in range(6):
            for k in range(j+1,6):
                r=wcorr(mat[:,j],mat[:,k],w);vals.append(r);corr.append({'representation':label,'outcome_a':OUTCOMES[j],'outcome_b':OUTCOMES[k],'weighted_correlation':r})
        corr.append({'representation':label,'outcome_a':'__SUMMARY__','outcome_b':'mean_pairwise','weighted_correlation':float(np.nanmean(vals))})
    cdf=pd.DataFrame(corr);cdf.to_csv(args.outdir/'joint_structure_correlations.csv',index=False)
    human={(r.outcome_a,r.outcome_b):r.weighted_correlation for _,r in cdf[(cdf.representation=='human')&(cdf.outcome_a!='__SUMMARY__')].iterrows()}
    cs=[]
    for c in CONDITIONS:
        sub=cdf[(cdf.representation==c)&(cdf.outcome_a!='__SUMMARY__')];diff=[]
        for _,r in sub.iterrows():diff.append(r.weighted_correlation-human[(r.outcome_a,r.outcome_b)])
        cs.append({'condition':c,'mean_pairwise_hard_correlation':float(sub.weighted_correlation.mean()),'human_mean_pairwise_correlation':float(cdf[(cdf.representation=='human')&(cdf.outcome_a!='__SUMMARY__')].weighted_correlation.mean()),'correlation_rmse_vs_human':float(np.sqrt(np.mean(np.asarray(diff)**2))),'mean_correlation_excess':float(np.mean(diff))})
    pd.DataFrame(cs).to_csv(args.outdir/'joint_structure_summary.csv',index=False)

    # Weighted response-vector transitions across reasoning arms.
    tr=[]
    for a,b in [('off','low'),('off','medium'),('low','medium')]:
        ca,cb=code(h[a]),code(h[b])
        for x in range(64):
            for z in range(64):
                m=(ca==x)&(cb==z);share=float(w[m].sum())
                if share>0:tr.append({'contrast':f'{a}->{b}','from_pattern':format(x,'06b'),'to_pattern':format(z,'06b'),'weight_share':share,'changed':x!=z})
    tdf=pd.DataFrame(tr).sort_values(['contrast','weight_share'],ascending=[True,False]);tdf.to_csv(args.outdir/'response_vector_transitions.csv',index=False)

    # Outcome-level shifts from reasoning.
    sh=[]
    for a,b in [('off','low'),('off','medium'),('low','medium')]:
        for j,o in enumerate(OUTCOMES):
            d=p[b][:,j]-p[a][:,j];flip=(h[b][:,j]!=h[a][:,j]).astype(float)
            toward=(np.abs(p[b][:,j]-.5)<np.abs(p[a][:,j]-.5)).astype(float)
            sh.append({'contrast':f'{a}->{b}','outcome':o,'mean_signed_probability_change':wmean(d,w),'mean_absolute_probability_change':wmean(np.abs(d),w),'hard_flip_rate':wmean(flip,w),'share_moved_toward_0_5':wmean(toward,w)})
    pd.DataFrame(sh).to_csv(args.outdir/'reasoning_probability_shifts_by_outcome.csv',index=False)

    # Subgroup Brier effects.
    sb=[]
    for var,groups in [('sector',['rural','urban']),('gender_binary',['male','female']),('age_group',['15-24','25-34','35-44','45-59','60+'])]:
        vals=t[var].astype(str).to_numpy()
        for g in groups:
            m=vals==g
            if not m.any():continue
            ww=w*m
            row={'subgroup_variable':var,'group':g,'n':int(m.sum()),'weight_share':float(ww.sum())}
            for c in CONDITIONS:row[c+'_brier']=wmean(np.mean((p[c]-y)**2,axis=1),ww)
            row['medium_minus_off_brier']=row['medium_brier']-row['off_brier'];row['low_minus_off_brier']=row['low_brier']-row['off_brier'];sb.append(row)
    pd.DataFrame(sb).to_csv(args.outdir/'subgroup_brier_effects.csv',index=False)

    # Phone-first / no-computer diagnostic using true outcomes only for post hoc interpretation.
    cond=[]
    subsets={
      'true_computer_no':y[:,2]==0,
      'true_computer_yes':y[:,2]==1,
      'true_phone_active_no_computer':(y[:,0]==1)&(y[:,1]==1)&(y[:,2]==0),
    }
    targets=[3,4,5]
    for name,m in subsets.items():
        ww=w*m
        for j in targets:
            row={'subset':name,'n':int(m.sum()),'weight_share':float(ww.sum()),'outcome':OUTCOMES[j],'human_prevalence':wmean(y[:,j],ww)}
            for c in CONDITIONS:
                row[c+'_probability_prevalence']=wmean(p[c][:,j],ww);row[c+'_hard_prevalence']=wmean(h[c][:,j],ww)
            cond.append(row)
    pd.DataFrame(cond).to_csv(args.outdir/'phone_first_conditional_diagnostic.csv',index=False)

    summary={'length_failure_counts':{c:len(length[c]) for c in ['low','medium']},'joint_structure_summary':cs,'top_changed_transitions':tdf[tdf.changed].groupby('contrast',group_keys=False).head(8).to_dict('records')}
    (args.outdir/'deep_diagnostics_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('STUDY1_DEEP_DIAGNOSTICS_PASS');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
