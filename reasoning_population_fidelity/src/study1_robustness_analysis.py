from __future__ import annotations

import argparse, csv, json, os, sys
from collections import defaultdict
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(HERE/'src'))
import production_runtime as legacy_runtime
from core import OUTCOMES
from final_analysis_study1 import decrypt_rpf,response_arrays,calc_core,pct_ci,wmean,vec_dist,entropy_bits,js_div

CONDITIONS=['off','low','medium']
BOOT_REPS=10000
BOOT_SEED=30082026
EXPECTED_FREEZE='120cc6bef15e7b2eb8fb2c49c7efa2fab5496b0a429cf34c8d9100b588cf9293'


def load_all(artifact_dir,key):
    summary=json.load(open(artifact_dir/'study1_summary.json'))
    assert summary['all_schema_valid'] and summary['requests_schema_valid']==3000 and summary['freeze_requests_sha256']==EXPECTED_FREEZE
    attempts=json.load(open(artifact_dir/'attempt_history.json'))
    raw=decrypt_rpf(artifact_dir/'raw_results.enc.b64',key)
    truth_text=legacy_runtime.decrypt_bundle(ROOT/'data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64',legacy_runtime.TRUTH_AAD).decode('utf-8')
    truth=pd.DataFrame(list(csv.DictReader(StringIO(truth_text))))
    for c in truth.columns:
        if c!='anon_id':
            try:truth[c]=pd.to_numeric(truth[c])
            except:pass
    truth=truth.sort_values('anon_id').reset_index(drop=True)
    ids=truth.anon_id.tolist();idx={x:i for i,x in enumerate(ids)}
    w=truth['analysis_weight'].astype(float).to_numpy();w=w/w.sum();y=truth[OUTCOMES].astype(int).to_numpy()
    probs={c:np.full((1000,6),np.nan) for c in CONDITIONS};hard={c:np.full((1000,6),-1,int) for c in CONDITIONS}
    rid_to_anon={};rid_to_cond={}
    for r in raw:
        i=idx[r['anon_id']];a,p=response_arrays(r['response']);probs[r['reasoning']][i]=p;hard[r['reasoning']][i]=a
        rid_to_anon[r['request_id']]=r['anon_id'];rid_to_cond[r['request_id']]=r['reasoning']
    return truth,ids,y,w,probs,hard,attempts,rid_to_anon,rid_to_cond


def metric_boot(y,w,probs,hard,mask,conditions=('off','low','medium')):
    ii=np.where(mask)[0]; ys=y[ii];ws=w[ii];ws=ws/ws.sum();pr={c:probs[c][ii] for c in conditions};ha={c:hard[c][ii] for c in conditions}
    core={c:calc_core(ys,pr[c],ha[c],ws) for c in conditions}
    rng=np.random.default_rng(BOOT_SEED); metrics=['population_probability_mae_pp','individual_brier','hard_prevalence_mae_pp','hard_accuracy','log_loss']
    boot={f'{a}-{b}':{m:[] for m in metrics} for a,b in [('medium','off'),('low','off'),('medium','low')] if a in conditions and b in conditions}
    n=len(ii)
    for _ in range(BOOT_REPS):
        s=rng.integers(0,n,size=n);counts=np.bincount(s,minlength=n).astype(float);wb=ws*counts
        v={c:calc_core(ys,pr[c],ha[c],wb) for c in conditions}
        for k in boot:
            a,b=k.split('-')
            for m in metrics:boot[k][m].append(v[a][m]-v[b][m])
    return core,boot,len(ii),float(w[mask].sum())

def ece_bins(p,y,w,bins=10):
    edges=np.linspace(0,1,bins+1);rows=[];ece=0.0
    for b in range(bins):
        lo,hi=edges[b],edges[b+1];mask=(p>=lo)&((p<hi) if b<bins-1 else (p<=hi))
        if not np.any(mask):continue
        ww=w[mask];share=ww.sum()/w.sum();mp=wmean(p[mask],ww);my=wmean(y[mask],ww);ece+=share*abs(mp-my)
        rows.append((b,lo,hi,share,mp,my))
    return float(ece),rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact-dir',type=Path,required=True);ap.add_argument('--outdir',type=Path,required=True);args=ap.parse_args();args.outdir.mkdir(parents=True,exist_ok=True)
    truth,ids,y,w,probs,hard,attempts,rid_to_anon,rid_to_cond=load_all(args.artifact_dir,os.environ['OPENROUTER_API_KEY'])
    ididx={x:i for i,x in enumerate(ids)}

    length_anons=defaultdict(set); length_counts=defaultdict(lambda:defaultdict(int)); total_attempts=defaultdict(int)
    for a in attempts:
        rid=a.get('request_id');anon=a.get('anon_id') or rid_to_anon.get(rid);c=a.get('reasoning') or rid_to_cond.get(rid)
        if not anon or c not in CONDITIONS:continue
        total_attempts[(anon,c)]+=1
        if not a.get('schema_valid') and (a.get('finish_reason')=='length' or a.get('meta_finish_reason')=='length'):
            length_anons[c].add(anon);length_counts[c][anon]+=1
    masks={
      'full':np.ones(1000,bool),
      'exclude_medium_length':np.array([x not in length_anons['medium'] for x in ids]),
      'exclude_low_length':np.array([x not in length_anons['low'] for x in ids]),
      'exclude_any_reasoning_length':np.array([x not in length_anons['low'] and x not in length_anons['medium'] for x in ids]),
      'exclude_extreme_retry_tail':np.array([length_counts['low'].get(x,0)<4 and length_counts['medium'].get(x,0)<4 for x in ids]),
    }
    sens=[]
    for name,mask in masks.items():
        core,boot,n,share=metric_boot(y,w,probs,hard,mask)
        for c in CONDITIONS:
            sens.append({'subset':name,'n':n,'population_weight_share':share,'condition':c,**core[c]})
        for k in ['medium-off','low-off','medium-low']:
            for m in ['population_probability_mae_pp','individual_brier','hard_prevalence_mae_pp','hard_accuracy','log_loss']:
                vals=boot[k][m];lo,hi=pct_ci(vals);a,b=k.split('-');sens.append({'subset':name,'n':n,'population_weight_share':share,'contrast':k,'metric':m,'estimate':core[a][m]-core[b][m],'ci_low':lo,'ci_high':hi})
    pd.DataFrame(sens).to_csv(args.outdir/'retry_sensitivity.csv',index=False)

    # Brier decomposition: weighted MSE(error)=weighted variance(error)+squared mean error, outcome by outcome.
    dec=[]
    for c in CONDITIONS:
        for j,o in enumerate(OUTCOMES):
            err=probs[c][:,j]-y[:,j];bias=wmean(err,w);b=wmean(err**2,w);var=b-bias*bias
            dec.append({'condition':c,'outcome':o,'brier':b,'bias':bias,'squared_bias':bias*bias,'error_variance':var})
    ddf=pd.DataFrame(dec);ddf.to_csv(args.outdir/'brier_bias_variance_decomposition.csv',index=False)
    agg=ddf.groupby('condition')[['brier','squared_bias','error_variance']].mean().reset_index();agg.to_csv(args.outdir/'brier_decomposition_aggregate.csv',index=False)

    # Probability/hard-answer alignment and p>=0.5 threshold counterfactual.
    align=[]
    for c in CONDITIONS:
        th=(probs[c]>=.5).astype(int);discord=(th!=hard[c]).astype(float)
        cm=calc_core(y,probs[c],th,w)
        align.append({'condition':c,'hard_probability_discordance_rate':wmean(np.mean(discord,axis=1),w),'thresholded_probability_accuracy':cm['hard_accuracy'],'thresholded_probability_prevalence_mae_pp':cm['hard_prevalence_mae_pp'],'reported_hard_accuracy':calc_core(y,probs[c],hard[c],w)['hard_accuracy'],'reported_hard_prevalence_mae_pp':calc_core(y,probs[c],hard[c],w)['hard_prevalence_mae_pp']})
    pd.DataFrame(align).to_csv(args.outdir/'hard_probability_alignment.csv',index=False)

    # 10-bin weighted calibration, per outcome and aggregate ECE across outcomes.
    cal=[]
    for c in CONDITIONS:
        eces=[]
        for j,o in enumerate(OUTCOMES):
            ece,rows=ece_bins(probs[c][:,j],y[:,j],w,10);eces.append(ece)
            for b,lo,hi,share,mp,my in rows:cal.append({'condition':c,'outcome':o,'bin':b,'bin_low':lo,'bin_high':hi,'weight_share':share,'mean_predicted':mp,'observed_prevalence':my,'absolute_calibration_gap':abs(mp-my),'outcome_ece':ece})
        cal.append({'condition':c,'outcome':'__MEAN_ECE__','bin':-1,'bin_low':None,'bin_high':None,'weight_share':1.0,'mean_predicted':None,'observed_prevalence':None,'absolute_calibration_gap':None,'outcome_ece':float(np.mean(eces))})
    pd.DataFrame(cal).to_csv(args.outdir/'calibration_bins_ece.csv',index=False)

    # Top weighted six-answer vectors to make homogenization visible.
    shares={}
    for label,mat in [('human',y),*[(c,hard[c]) for c in CONDITIONS]]:
        d=vec_dist(mat,w);shares[label]=d
    union=set()
    for label,d in shares.items(): union.update(np.argsort(-d)[:10].tolist())
    pats=[]
    for code in sorted(union,key=lambda k:-shares['human'][k]):
        bit=format(code,'06b');row={'pattern':bit,'pattern_named':','.join(f'{o}={bit[j]}' for j,o in enumerate(OUTCOMES))}
        for label,d in shares.items():row[label+'_share']=d[code]
        pats.append(row)
    pd.DataFrame(pats).to_csv(args.outdir/'top_response_vectors.csv',index=False)

    # Detailed subgroup prevalences, including the age mechanism.
    sg=[]
    for var,groups in [('sector',['rural','urban']),('gender_binary',['male','female']),('age_group',['15-24','25-34','35-44','45-59','60+'])]:
        for g in groups:
            mask=truth[var].astype(str).to_numpy()==g
            if not mask.any():continue
            ww=w*mask
            for j,o in enumerate(OUTCOMES):
                row={'subgroup_variable':var,'group':g,'outcome':o,'n':int(mask.sum()),'weight_share':float(ww.sum()),'human_prevalence':wmean(y[:,j],ww)}
                for c in CONDITIONS:row[c+'_probability_prevalence']=wmean(probs[c][:,j],ww)
                sg.append(row)
    pd.DataFrame(sg).to_csv(args.outdir/'subgroup_outcome_prevalence.csv',index=False)

    # Outcome-level bootstrap for primary medium-off mechanism.
    rng=np.random.default_rng(BOOT_SEED);obs=[]
    for j,o in enumerate(OUTCOMES):
        hp=wmean(y[:,j],w); offp=wmean(probs['off'][:,j],w);medp=wmean(probs['medium'][:,j],w)
        est_abs=100*(abs(medp-hp)-abs(offp-hp));est_b=wmean((probs['medium'][:,j]-y[:,j])**2-(probs['off'][:,j]-y[:,j])**2,w)
        vals_abs=[];vals_b=[]
        for _ in range(BOOT_REPS):
            s=rng.integers(0,1000,size=1000);cnt=np.bincount(s,minlength=1000);wb=w*cnt
            h=wmean(y[:,j],wb);op=wmean(probs['off'][:,j],wb);mp=wmean(probs['medium'][:,j],wb)
            vals_abs.append(100*(abs(mp-h)-abs(op-h)));vals_b.append(wmean((probs['medium'][:,j]-y[:,j])**2-(probs['off'][:,j]-y[:,j])**2,wb))
        alo,ahi=pct_ci(vals_abs);blo,bhi=pct_ci(vals_b)
        obs.append({'outcome':o,'medium_minus_off_absolute_prevalence_error_pp':est_abs,'mae_change_ci_low':alo,'mae_change_ci_high':ahi,'medium_minus_off_brier':est_b,'brier_change_ci_low':blo,'brier_change_ci_high':bhi})
    pd.DataFrame(obs).to_csv(args.outdir/'outcome_primary_contrast_bootstrap.csv',index=False)

    summary={'length_failure_respondents':{c:len(length_anons[c]) for c in CONDITIONS},'sensitivity_subset_sizes':{k:int(v.sum()) for k,v in masks.items()},'brier_decomposition_aggregate':agg.to_dict('records'),'hard_probability_alignment':align,'bootstrap_reps':BOOT_REPS,'bootstrap_seed':BOOT_SEED}
    (args.outdir/'robustness_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('STUDY1_ROBUSTNESS_ANALYSIS_PASS');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
