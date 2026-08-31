from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; HERE=ROOT/'studies'/'common'
for p in (HERE, ROOT/'reasoning_population_fidelity'/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from suite_core import SCHEMA, build_requests, load_registry, static_report
from openrouter_preflight import choose_endpoint, endpoint_healthy
from paid_runner import one, ceiling, encrypt_rows
from resume_followup import decrypt_rows, checkpoint


def run(seed_dir: Path,outdir: Path,cap: float,max_attempts: int):
    if os.getenv('ENABLE_PAID_STUDY_SUITE')!='I_ACCEPT_PAID_INFERENCE': raise RuntimeError('paid auth missing')
    key=os.getenv('OPENROUTER_API_KEY')
    if not key: raise RuntimeError('OPENROUTER_API_KEY missing')
    study_id='S01_second_model_reasoning'; reg=load_registry(); study=reg['studies'][study_id]
    assert static_report(study_id)['status']=='PASS_STATIC'
    seed_summary=json.load(open(seed_dir/'summary.json'))
    assert seed_summary['schema_valid']==1999 and seed_summary['remaining_failures']==1,seed_summary
    assert seed_summary['by_arm']=={'rich_high':999,'rich_off':1000},seed_summary
    raw_rows=decrypt_rows(seed_dir/'raw_results.enc.b64',key,study_id); raw={r['request_id']:r for r in raw_rows}; assert len(raw)==1999
    attempts=json.load(open(seed_dir/'attempts.json')); rows=build_requests(study_id); row_by_id={r['request_id']:r for r in rows}
    missing=[r for r in rows if r['request_id'] not in raw]; assert len(missing)==1
    target=missing[0]; schema=json.loads(SCHEMA.read_text())
    cfg=reg['models'][target['model_key']]; ep=choose_endpoint(cfg['id'],key,cfg['provider_name']); assert endpoint_healthy(ep) and ep['tag']=='open-inference/fp8'
    eps={target['model_key']:ep}; spent=0.0
    # minimal seed summary shape expected by checkpoint helper
    base={'schema_valid':1999,'accounted_upper_bound_usd':float(seed_summary.get('combined_preserved_accounted_upper_bound_usd',seed_summary.get('accounted_upper_bound_usd',0.0)))}
    print(json.dumps({'status':'S01_FINAL_ONE_START','request_id':target['request_id'],'arm':target['arm_id'],'max_attempts':max_attempts,'cap_usd':cap}),flush=True)
    for i in range(1,max_attempts+1):
        c=ceiling(target,ep)
        if spent+c>cap+1e-12: break
        t=time.perf_counter(); rec,parsed=one(target,schema,ep,key,100+i); rec['recovery_cycle']=100+i; attempts.append(rec); spent+=float(rec.get('accounted_upper_bound_usd') or c)
        if parsed is not None:
            raw[target['request_id']]={'request_id':target['request_id'],'anon_id':target['anon_id'],'arm_id':target['arm_id'],'response':parsed}
        # local checkpoint after every single attempt
        outdir.mkdir(parents=True,exist_ok=True)
        (outdir/'attempts.json').write_text(json.dumps(sorted(attempts,key=lambda x:(x['request_id'],x.get('attempt',0),x.get('recovery_cycle',0))),indent=2,sort_keys=True))
        encrypt_rows([raw[k] for k in sorted(raw)],outdir/'raw_results.enc.b64',key,study_id)
        by_arm={'rich_off':0,'rich_high':0}
        for rid in raw: by_arm[row_by_id[rid]['arm_id']]+=1
        summary={'study_id':study_id,'planned_requests':2000,'schema_valid':len(raw),'remaining_failures':2000-len(raw),'by_arm':by_arm,'attempts_preserved':len(attempts),'seed_schema_valid':1999,'recovery_accounted_upper_bound_usd':round(spent,6),'combined_preserved_accounted_upper_bound_usd':round(base['accounted_upper_bound_usd']+spent,6),'allow_fallbacks':False,'data_collection':'deny','truth_loaded':False,'all_schema_valid':len(raw)==2000,'endpoint_tags':{'deepseek_v4_flash':'open-inference/fp8'},'checkpoint_final':len(raw)==2000}
        (outdir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
        print(json.dumps({'phase':'attempt','n':i,'schema_valid':len(raw),'remaining':2000-len(raw),'latency_s':round(time.perf_counter()-t,2),'finish_reason':rec.get('finish_reason'),'error':rec.get('error'),'recovery_accounted_usd':round(spent,6)}),flush=True)
        if parsed is not None:
            print('S01_FINAL_2000_PASS',flush=True); return summary
        time.sleep(0.5)
    raise RuntimeError('S01 final request still unresolved')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--seed-dir',required=True); ap.add_argument('--outdir',required=True); ap.add_argument('--cap',type=float,default=0.03); ap.add_argument('--max-attempts',type=int,default=20)
    a=ap.parse_args(); run(Path(a.seed_dir),Path(a.outdir),a.cap,a.max_attempts)
