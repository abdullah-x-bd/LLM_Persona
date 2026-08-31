from __future__ import annotations

import argparse, base64, csv, gzip, hashlib, json, math, os, sys
from collections import Counter
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(HERE / 'src'))

import production_runtime as legacy_runtime
from core import OUTCOMES

AAD = b'RPF_STUDY1_RESULTS_V1'
EXPECTED_FREEZE = '120cc6bef15e7b2eb8fb2c49c7efa2fab5496b0a429cf34c8d9100b588cf9293'
CONDITIONS = ['off','low','medium']
CONTRASTS = [('medium','off'),('low','off'),('medium','low')]
BOOT_REPS = 10000
BOOT_SEED = 30082026


def wmean(x,w):
    x=np.asarray(x,float); w=np.asarray(w,float)
    return float(np.sum(x*w)/np.sum(w))

def pct_ci(x):
    a=np.asarray(x,float)
    return float(np.quantile(a,.025)), float(np.quantile(a,.975))

def decrypt_rpf(path:Path,key:str):
    blob=base64.b64decode(path.read_text(encoding='ascii')); nonce,cipher=blob[:12],blob[12:]
    aes_key=hashlib.sha256(AAD+b'|'+key.encode()).digest()
    text=gzip.decompress(AESGCM(aes_key).decrypt(nonce,cipher,AAD)).decode('utf-8')
    return [json.loads(x) for x in text.splitlines() if x.strip()]

def response_arrays(obj):
    if set(obj)=={'a','p'}:
        return np.asarray(obj['a'],int), np.asarray(obj['p'],float)
    a=[]; p=[]
    for o in OUTCOMES:
        v=obj[o]; a.append(1 if v['answer']=='yes' else 0); p.append(float(v['probability_yes']))
    return np.asarray(a,int),np.asarray(p,float)

def vec_dist(mat,w):
    codes=(mat.astype(int)*(1<<np.arange(mat.shape[1]-1,-1,-1))).sum(axis=1)
    out=np.zeros(64,float)
    for k in range(64): out[k]=np.sum(w[codes==k])
    out/=out.sum()
    return out

def js_div(p,q):
    p=np.asarray(p,float);q=np.asarray(q,float);m=(p+q)/2
    def kl(a,b):
        mask=a>0
        return float(np.sum(a[mask]*np.log2(a[mask]/b[mask])))
    return .5*kl(p,m)+.5*kl(q,m)

def entropy_bits(p):
    p=np.asarray(p,float);m=p>0
    return float(-np.sum(p[m]*np.log2(p[m])))

def cliplogloss(p,y,w):
    p=np.clip(p,.001,.999)
    ll=-(y*np.log(p)+(1-y)*np.log(1-p))
    per_i=np.mean(ll,axis=1)
    return wmean(per_i,w)

def calc_core(y, probs, hard, w):
    hp=np.array([wmean(y[:,j],w) for j in range(6)])
    pp=np.array([wmean(probs[:,j],w) for j in range(6)])
    ap=np.array([wmean(hard[:,j],w) for j in range(6)])
    brier_i=np.mean((probs-y)**2,axis=1)
    acc_i=np.mean(hard==y,axis=1)
    return {
        'population_probability_mae_pp': float(100*np.mean(np.abs(pp-hp))),
        'individual_brier': wmean(brier_i,w),
        'hard_prevalence_mae_pp': float(100*np.mean(np.abs(ap-hp))),
        'hard_accuracy': wmean(acc_i,w),
        'log_loss': cliplogloss(probs,y,w),
        'calibration_in_large_pp': float(100*np.mean(pp-hp)),
        'mean_probability_extremeness': wmean(np.mean(np.abs(probs-.5),axis=1),w),
    }

def safe_group(df,col):
    if col in df.columns: return col
    aliases={'gender_binary':['gender','sex'],'age_group':['agegroup'],'sector':['Sector']}
    for a in aliases.get(col,[]):
        if a in df.columns:return a
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact-dir',required=True,type=Path);ap.add_argument('--outdir',required=True,type=Path);args=ap.parse_args()
    out=args.outdir;out.mkdir(parents=True,exist_ok=True)
    key=os.environ['OPENROUTER_API_KEY']
    summary=json.load(open(args.artifact_dir/'study1_summary.json'))
    assert summary['all_schema_valid'] and summary['requests_schema_valid']==3000 and summary['remaining_failures']==0
    assert summary['condition_valid_counts']=={'off':1000,'low':1000,'medium':1000}
    assert summary['freeze_requests_sha256']==EXPECTED_FREEZE
    meta=json.load(open(args.artifact_dir/'production_requests.json'))
    assert len(meta)==3000 and len({x['request_id'] for x in meta})==3000
    raw=decrypt_rpf(args.artifact_dir/'raw_results.enc.b64',key)
    assert len(raw)==3000 and len({x['request_id'] for x in raw})==3000

    truth_text=legacy_runtime.decrypt_bundle(ROOT/'data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64',legacy_runtime.TRUTH_AAD).decode('utf-8')
    code_text=legacy_runtime.decrypt_bundle(ROOT/'data/encrypted/cams_codes_v2.x25519.aesgcm.gz.b64',legacy_runtime.CODES_AAD).decode('utf-8')
    truth=pd.DataFrame(list(csv.DictReader(StringIO(truth_text))))
    codes=pd.DataFrame(list(csv.DictReader(StringIO(code_text))))
    assert len(truth)==1000 and truth['anon_id'].nunique()==1000 and set(truth.anon_id)==set(codes.anon_id)
    for c in truth.columns:
        if c!='anon_id':
            try: truth[c]=pd.to_numeric(truth[c])
            except Exception: pass
    for c in codes.columns:
        if c!='anon_id':
            try: codes[c]=pd.to_numeric(codes[c])
            except Exception: pass

    if 'sector' not in truth.columns and 'SEC' in codes.columns:
        truth=truth.merge(codes[['anon_id','SEC']],on='anon_id',how='left');truth['sector']=truth['SEC'].map({1:'rural',2:'urban'})
    if 'gender_binary' not in truth.columns and 'BL31C4' in codes.columns:
        if 'BL31C4' not in truth.columns: truth=truth.merge(codes[['anon_id','BL31C4']],on='anon_id',how='left')
        truth['gender_binary']=truth['BL31C4'].map({1:'male',2:'female'})
    if 'age_group' not in truth.columns and 'BL31C5' in codes.columns:
        if 'BL31C5' not in truth.columns: truth=truth.merge(codes[['anon_id','BL31C5']],on='anon_id',how='left')
        age=truth['BL31C5'].astype(float)
        truth['age_group']=pd.cut(age,bins=[14,24,34,44,59,np.inf],labels=['15-24','25-34','35-44','45-59','60+']).astype(str)

    weight_col='analysis_weight' if 'analysis_weight' in truth.columns else ('MULT' if 'MULT' in truth.columns else None)
    if weight_col is None: raise RuntimeError(f'No survey weight found. Truth columns={list(truth.columns)}')
    for o in OUTCOMES:
        if o not in truth.columns: raise RuntimeError(f'Missing truth outcome {o}; columns={list(truth.columns)}')
    truth=truth.sort_values('anon_id').reset_index(drop=True)
    ids=truth.anon_id.tolist(); idx={x:i for i,x in enumerate(ids)}
    y=truth[OUTCOMES].astype(int).to_numpy(); w=truth[weight_col].astype(float).to_numpy(); w=w/w.sum()

    probs={c:np.full((1000,6),np.nan) for c in CONDITIONS};hard={c:np.full((1000,6),-1,int) for c in CONDITIONS}
    for r in raw:
        c=r['reasoning'];i=idx[r['anon_id']];a,p=response_arrays(r['response']);hard[c][i]=a;probs[c][i]=p
    for c in CONDITIONS:
        assert np.isfinite(probs[c]).all() and (hard[c]>=0).all()

    core={c:calc_core(y,probs[c],hard[c],w) for c in CONDITIONS}
    metric_names=list(core['off'])
    boot_cond={c:{m:[] for m in metric_names} for c in CONDITIONS}
    boot_con={f'{a}-{b}':{m:[] for m in metric_names} for a,b in CONTRASTS}
    rng=np.random.default_rng(BOOT_SEED)
    for rep in range(BOOT_REPS):
        s=rng.integers(0,1000,size=1000)
        counts=np.bincount(s,minlength=1000).astype(float); wb=w*counts
        vals={c:calc_core(y,probs[c],hard[c],wb) for c in CONDITIONS}
        for c in CONDITIONS:
            for m in metric_names: boot_cond[c][m].append(vals[c][m])
        for a,b in CONTRASTS:
            k=f'{a}-{b}'
            for m in metric_names:boot_con[k][m].append(vals[a][m]-vals[b][m])

    primary_rows=[]
    for c in CONDITIONS:
        for m in metric_names:
            lo,hi=pct_ci(boot_cond[c][m]);primary_rows.append({'condition':c,'metric':m,'estimate':core[c][m],'ci_low':lo,'ci_high':hi})
    pd.DataFrame(primary_rows).to_csv(out/'condition_metrics.csv',index=False)
    contrast_rows=[]
    for a,b in CONTRASTS:
        k=f'{a}-{b}'
        for m in metric_names:
            est=core[a][m]-core[b][m];lo,hi=pct_ci(boot_con[k][m]);contrast_rows.append({'contrast':k,'metric':m,'estimate':est,'ci_low':lo,'ci_high':hi})
    pd.DataFrame(contrast_rows).to_csv(out/'paired_contrasts.csv',index=False)

    outcome_rows=[]
    human_prev=np.array([wmean(y[:,j],w) for j in range(6)])
    for c in CONDITIONS:
        for j,o in enumerate(OUTCOMES):
            pp=wmean(probs[c][:,j],w);hp=human_prev[j];hh=wmean(hard[c][:,j],w)
            outcome_rows.append({'condition':c,'outcome':o,'human_prevalence':hp,'probability_prevalence':pp,'probability_error_pp':100*(pp-hp),'absolute_probability_error_pp':100*abs(pp-hp),'hard_prevalence':hh,'hard_error_pp':100*(hh-hp),'absolute_hard_error_pp':100*abs(hh-hp),'brier':wmean((probs[c][:,j]-y[:,j])**2,w),'accuracy':wmean((hard[c][:,j]==y[:,j]).astype(float),w),'calibration_in_large_pp':100*(pp-hp)})
    pd.DataFrame(outcome_rows).to_csv(out/'outcome_metrics.csv',index=False)

    human_dist=vec_dist(y,w);div_rows=[]
    for c in CONDITIONS:
        d=vec_dist(hard[c],w); div_rows.append({'condition':c,'observed_patterns':int(np.sum(d>0)),'shannon_entropy_bits':entropy_bits(d),'effective_patterns':float(2**entropy_bits(d)),'largest_pattern_share':float(d.max()),'tv_distance_to_human':float(.5*np.abs(d-human_dist).sum()),'js_divergence_bits_to_human':js_div(d,human_dist),'human_observed_patterns':int(np.sum(human_dist>0)),'human_entropy_bits':entropy_bits(human_dist)})
    pd.DataFrame(div_rows).to_csv(out/'diversity_distributional.csv',index=False)

    subgroup_rows=[];gap_rows=[];over_rows=[]
    group_defs=[('sector',['rural','urban']),('gender_binary',['male','female']),('age_group',['15-24','25-34','35-44','45-59','60+'])]
    for logical,preferred in group_defs:
        col=safe_group(truth,logical)
        if col is None: continue
        available=[g for g in preferred if g in set(truth[col].astype(str))]
        if len(available)<2: continue
        for g in available:
            mask=(truth[col].astype(str).to_numpy()==g);wg=w*mask
            hp=np.array([wmean(y[:,j],wg) for j in range(6)])
            for c in CONDITIONS:
                pp=np.array([wmean(probs[c][:,j],wg) for j in range(6)])
                subgroup_rows.append({'subgroup_variable':logical,'group':g,'condition':c,'n_unweighted':int(mask.sum()),'weight_share':float(wg.sum()),'probability_prevalence_mae_pp':100*float(np.mean(np.abs(pp-hp)))})
        for j,o in enumerate(OUTCOMES):
            hprev=[]
            for g in available:
                mask=(truth[col].astype(str).to_numpy()==g);wg=w*mask;hprev.append(wmean(y[:,j],wg))
            human_gap=max(hprev)-min(hprev)
            for c in CONDITIONS:
                mprev=[]
                for g in available:
                    mask=(truth[col].astype(str).to_numpy()==g);wg=w*mask;mprev.append(wmean(probs[c][:,j],wg))
                model_gap=max(mprev)-min(mprev)
                over_rows.append({'subgroup_variable':logical,'outcome':o,'condition':c,'human_gap_pp':100*human_gap,'synthetic_probability_gap_pp':100*model_gap,'excess_gap_magnitude_pp':100*(model_gap-human_gap),'gap_ratio':float(model_gap/human_gap) if human_gap>1e-12 else None})
            for a_i in range(len(available)):
                for b_i in range(a_i+1,len(available)):
                    ga,gb=available[a_i],available[b_i]
                    ma=(truth[col].astype(str).to_numpy()==ga);mb=(truth[col].astype(str).to_numpy()==gb)
                    wha=w*ma;whb=w*mb;hg=wmean(y[:,j],whb)-wmean(y[:,j],wha)
                    for c in CONDITIONS:
                        sg=wmean(probs[c][:,j],whb)-wmean(probs[c][:,j],wha)
                        gap_rows.append({'subgroup_variable':logical,'group_a':ga,'group_b':gb,'outcome':o,'condition':c,'human_gap_pp':100*hg,'synthetic_gap_pp':100*sg,'signed_gap_error_pp':100*(sg-hg),'absolute_gap_error_pp':100*abs(sg-hg)})
    pd.DataFrame(subgroup_rows).to_csv(out/'subgroup_mae.csv',index=False)
    pd.DataFrame(gap_rows).to_csv(out/'subgroup_gap_reproduction.csv',index=False)
    pd.DataFrame(over_rows).to_csv(out/'demographic_overdetermination.csv',index=False)

    change=[]
    for a,b in CONTRASTS:
        dp=np.abs(probs[a]-probs[b]); flips=(hard[a]!=hard[b]).astype(float)
        change.append({'contrast':f'{a}-{b}','weighted_mean_abs_probability_change':wmean(np.mean(dp,axis=1),w),'weighted_hard_flip_rate':wmean(np.mean(flips,axis=1),w),'mean_extremeness_change':core[a]['mean_probability_extremeness']-core[b]['mean_probability_extremeness']})
    pd.DataFrame(change).to_csv(out/'exploratory_arm_changes.csv',index=False)

    attempts=json.load(open(args.artifact_dir/'attempt_history.json'));op=[]
    for c in CONDITIONS:
        sm=[r for r in meta if r['reasoning']==c]; aa=[r for r in attempts if r.get('reasoning')==c]
        length=sum(1 for r in aa if r.get('finish_reason')=='length' and not r.get('schema_valid'))
        op.append({'condition':c,'successful_requests':len(sm),'attempt_records':len(aa),'successful_cost_usd':sum(float(r.get('cost_usd') or 0) for r in sm),'mean_prompt_tokens':np.mean([r.get('prompt_tokens',0) for r in sm]),'mean_completion_tokens':np.mean([r.get('completion_tokens',0) for r in sm]),'mean_reasoning_tokens':np.mean([r.get('reasoning_tokens',0) for r in sm]),'median_latency_seconds':float(np.median([float(r.get('latency_seconds') or 0) for r in sm])),'length_failures_in_attempt_history':length})
    pd.DataFrame(op).to_csv(out/'operational_metrics.csv',index=False)

    result={'integrity':{'requests':3000,'respondents':1000,'counts':summary['condition_valid_counts'],'freeze_sha256':EXPECTED_FREEZE,'provider_order':summary['provider_order'],'all_schema_valid':True},'co_primary':{c:{'population_probability_mae_pp':core[c]['population_probability_mae_pp'],'individual_brier':core[c]['individual_brier']} for c in CONDITIONS},'primary_contrast_medium_minus_off':{},'secondary_contrasts':{},'diversity_distributional':div_rows,'bootstrap_reps':BOOT_REPS,'bootstrap_seed':BOOT_SEED,'truth_columns':list(truth.columns)}
    for m in ['population_probability_mae_pp','individual_brier']:
        vals=boot_con['medium-off'][m];lo,hi=pct_ci(vals);result['primary_contrast_medium_minus_off'][m]={'estimate':core['medium'][m]-core['off'][m],'ci95':[lo,hi]}
    for k in ['low-off','medium-low']:
        result['secondary_contrasts'][k]={}
        for m in ['population_probability_mae_pp','individual_brier']:
            lo,hi=pct_ci(boot_con[k][m]);a,b=k.split('-');result['secondary_contrasts'][k][m]={'estimate':core[a][m]-core[b][m],'ci95':[lo,hi]}
    (out/'final_analysis_summary.json').write_text(json.dumps(result,indent=2,sort_keys=True),encoding='utf-8')

    md=['# Study 1 final analysis','',f'Integrity: 3000/3000 valid; 1000 respondents in each arm; bootstrap n={BOOT_REPS}, seed={BOOT_SEED}.','', '## Co-primary metrics','', '| Condition | Probability prevalence MAE (pp) | Individual Brier | Hard prevalence MAE (pp) | Hard accuracy | Log loss |','|---|---:|---:|---:|---:|---:|']
    for c in CONDITIONS: md.append(f"| {c} | {core[c]['population_probability_mae_pp']:.3f} | {core[c]['individual_brier']:.5f} | {core[c]['hard_prevalence_mae_pp']:.3f} | {core[c]['hard_accuracy']:.4f} | {core[c]['log_loss']:.4f} |")
    md += ['', '## Paired co-primary contrasts','', '| Contrast | Metric | Estimate | 95% bootstrap CI |','|---|---|---:|---:|']
    for k in ['medium-off','low-off','medium-low']:
        a,b=k.split('-')
        for m in ['population_probability_mae_pp','individual_brier']:
            lo,hi=pct_ci(boot_con[k][m]);md.append(f"| {k} | {m} | {core[a][m]-core[b][m]:.5f} | [{lo:.5f}, {hi:.5f}] |")
    md += ['', '## Notes','', '- Negative MAE/Brier contrasts indicate improvement for the first arm named in the contrast.', '- Subgroup, overdetermination, diversity, outcome-specific and operational tables are included as separate CSV files.', '- `exploratory_arm_changes.csv` is explicitly exploratory and was not part of the frozen co-primary analysis.']
    (out/'FINAL_RESULTS.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('STUDY1_FULL_ANALYSIS_PASS')
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
