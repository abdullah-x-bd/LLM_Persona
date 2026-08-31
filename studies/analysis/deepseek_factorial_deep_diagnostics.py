from __future__ import annotations

import argparse, csv, json, os, sys
from io import StringIO
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'reasoning_population_fidelity'/'src'))
from studies.analysis.deepseek_factorial_analysis import (
    ARMS, OUTCOMES, EPS, TRUTH_BUNDLE, CODES_BUNDLE, decrypt_followup,
    cell_metrics, contrast_values, bootstrap_all, pattern_dist, wmean
)
import production_runtime

SEED=3108202613
REPS=10000


def weighted_rate(mask,w):
    return float(np.sum(mask*w)/np.sum(w))


def subgroup_boot(P,A,Y,w,ids,demo):
    rng=np.random.default_rng(SEED); rows=[]
    for level in ['15-24','25-34','35-44','45-59','60+']:
        mask=demo['age_group'].to_numpy()==level
        idx0=np.where(mask)[0]; n=len(idx0)
        if n<20: continue
        ww=w[idx0]; YY=Y[idx0]
        for contrast,lo,hi in [('thin_reasoning','thin_off','thin_high'),('rich_reasoning','rich_off','rich_high')]:
            point_lo=cell_metrics(P[lo][idx0],A[lo][idx0],YY,ww)
            point_hi=cell_metrics(P[hi][idx0],A[hi][idx0],YY,ww)
            stores={m:[] for m in ['individual_brier','probability_prevalence_mae','hard_prevalence_mae','hard_accuracy']}
            base=np.full(n,1/n)
            rb={arm:np.mean((P[arm][idx0]-YY)**2,axis=1) for arm in [lo,hi]}
            ra={arm:np.mean(A[arm][idx0]==YY,axis=1) for arm in [lo,hi]}
            done=0
            while done<REPS:
                b=min(250,REPS-done); counts=rng.multinomial(n,base,size=b).astype(float); W=counts*ww[None,:]; den=W.sum(axis=1)
                truth=(W@YY)/den[:,None]
                vals={}
                for arm in [lo,hi]:
                    vals[(arm,'individual_brier')]=(W@rb[arm])/den
                    vals[(arm,'hard_accuracy')]=(W@ra[arm])/den
                    vals[(arm,'probability_prevalence_mae')]=np.mean(np.abs((W@P[arm][idx0])/den[:,None]-truth),axis=1)
                    vals[(arm,'hard_prevalence_mae')]=np.mean(np.abs((W@A[arm][idx0])/den[:,None]-truth),axis=1)
                for m in stores: stores[m].append(vals[(hi,m)]-vals[(lo,m)])
                done+=b
            for m,chunks in stores.items():
                x=np.concatenate(chunks); est=point_hi[m]-point_lo[m]
                rows.append({'age_group':level,'n':n,'contrast':contrast,'metric':m,'estimate':est,'ci95_low':float(np.quantile(x,.025)),'ci95_high':float(np.quantile(x,.975)),'sign_p_two_sided':min(1.0,2*min(float(np.mean(x<=0)),float(np.mean(x>=0)))),'reps':REPS,'seed':SEED})
    return pd.DataFrame(rows)


def run(s01_dir:Path,s03_dir:Path,outdir:Path):
    key=os.environ['OPENROUTER_API_KEY']
    raw=decrypt_followup(s01_dir/'raw_results.enc.b64',key,'S01_second_model_reasoning')+decrypt_followup(s03_dir/'raw_results.enc.b64',key,'S03_persona_reasoning_factorial')
    resp={(str(r['anon_id']),str(r['arm_id'])):r['response'] for r in raw}; ids=sorted({k[0] for k in resp}); assert len(resp)==4000 and len(ids)==1000
    trows=list(csv.DictReader(StringIO(production_runtime.decrypt_bundle(TRUTH_BUNDLE,production_runtime.TRUTH_AAD).decode()))); tm={str(r['anon_id']):r for r in trows}
    Y=np.asarray([[int(float(tm[i][o])) for o in OUTCOMES] for i in ids],float); w=np.asarray([float(tm[i].get('analysis_weight') or tm[i].get('MULT') or 1) for i in ids],float)
    P={a:np.asarray([resp[(i,a)]['p'] for i in ids],float) for a in ARMS}; A={a:np.asarray([resp[(i,a)]['a'] for i in ids],float) for a in ARMS}
    crows=list(csv.DictReader(StringIO(production_runtime.decrypt_bundle(CODES_BUNDLE,production_runtime.CODES_AAD).decode()))); cm={str(r['anon_id']):r for r in crows}
    demo=[]
    for i in ids:
        d=production_runtime.decode_row(cm[i]); ag='15-24' if d.age<25 else '25-34' if d.age<35 else '35-44' if d.age<45 else '45-59' if d.age<60 else '60+'
        demo.append({'anon_id':i,'age_group':ag,'gender':d.gender,'sector':d.sector})
    demo=pd.DataFrame(demo)

    extreme={}
    for arm in ARMS:
        p=P[arm].reshape(-1); y=Y.reshape(-1); a=A[arm].reshape(-1); ww=np.repeat(w,6)
        pc=np.clip(p,EPS,1-EPS); ll=-(y*np.log(pc)+(1-y)*np.log(1-pc))
        extreme[arm]={
            'p_le_001_or_ge_099':weighted_rate((p<=.01)|(p>=.99),ww),
            'wrong_extreme_p_le_001_or_ge_099':weighted_rate(((p<=.01)&(y==1))|((p>=.99)&(y==0)),ww),
            'exact_zero_or_one':weighted_rate((p==0)|(p==1),ww),
            'logloss_gt_2':weighted_rate(ll>2,ww),'logloss_gt_5':weighted_rate(ll>5,ww),'logloss_gt_10':weighted_rate(ll>10,ww),
            'hard_vs_threshold_disagreement':weighted_rate(a!=(p>=.5),ww),
            'max_clipped_item_logloss':float(ll.max()),
        }

    ageboot=subgroup_boot(P,A,Y,w,ids,demo)

    transitions={}
    for persona,lo,hi in [('thin','thin_off','thin_high'),('rich','rich_off','rich_high')]:
        dlo=pattern_dist(A[lo],w); dhi=pattern_dist(A[hi],w)
        changed=np.any(A[lo]!=A[hi],axis=1)
        meanpd=np.mean(np.abs(P[hi]-P[lo]),axis=1)
        trans={}
        for j,i in enumerate(ids):
            s=''.join(str(int(x)) for x in A[lo][j]); t=''.join(str(int(x)) for x in A[hi][j]); trans[(s,t)]=trans.get((s,t),0)+w[j]
        total=sum(trans.values()); top=sorted(trans.items(),key=lambda kv:kv[1],reverse=True)[:15]
        transitions[persona]={'weighted_any_hard_pattern_change':weighted_rate(changed,w),'weighted_mean_abs_probability_change':wmean(meanpd,w),'top_transitions':[{'from':k[0],'to':k[1],'share':float(v/total)} for k,v in top]}

    # Retry-tail sensitivity, with bootstrap on respondents first-pass valid in all four cells.
    def fps(path):
        aa=json.load(open(path)); return {(str(r['anon_id']),str(r['arm_id'])) for r in aa if int(r.get('attempt',0))==1 and r.get('schema_valid') is True}
    fp=fps(s01_dir/'attempts.json')|fps(s03_dir/'attempts.json'); keep=[j for j,i in enumerate(ids) if all((i,a) in fp for a in ARMS)]
    K=np.asarray(keep,int); bootfp=bootstrap_all({a:P[a][K] for a in ARMS},{a:A[a][K] for a in ARMS},Y[K],w[K]) if len(K)>=100 else pd.DataFrame()
    fpmetrics={a:cell_metrics(P[a][K],A[a][K],Y[K],w[K]) for a in ARMS}
    fp_points=[]
    for metric in bootfp.metric.unique():
        cv=contrast_values(fpmetrics,metric)
        for c,v in cv.items(): fp_points.append({'metric':metric,'contrast':c,'estimate':v})
    if len(bootfp): bootfp=pd.DataFrame(fp_points).merge(bootfp,on=['metric','contrast'])

    outdir.mkdir(parents=True,exist_ok=True)
    ageboot.to_csv(outdir/'age_reasoning_bootstrap.csv',index=False)
    bootfp.to_csv(outdir/'all_four_first_pass_bootstrap.csv',index=False)
    (outdir/'extreme_probability_diagnostics.json').write_text(json.dumps(extreme,indent=2,sort_keys=True))
    (outdir/'reasoning_transition_diagnostics.json').write_text(json.dumps(transitions,indent=2,sort_keys=True))
    summary={'status':'DEEPSEEK_FACTORIAL_DEEP_DIAGNOSTICS_COMPLETE','age_bootstrap_reps':REPS,'age_bootstrap_seed':SEED,'all_four_first_pass_n':len(K),'extreme_probability_diagnostics':extreme,'reasoning_transitions':transitions,'respondent_plaintext_emitted':False,'paid_inference_performed':False}
    (outdir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
    print('DEEPSEEK_FACTORIAL_DEEP_DIAGNOSTICS_PASS',flush=True)
    print(json.dumps({'all_four_first_pass_n':len(K),'extreme_probability_diagnostics':extreme},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--s01-dir',type=Path,required=True); ap.add_argument('--s03-dir',type=Path,required=True); ap.add_argument('--outdir',type=Path,required=True); a=ap.parse_args(); run(a.s01_dir,a.s03_dir,a.outdir)
