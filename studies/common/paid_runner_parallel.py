from __future__ import annotations
import argparse, concurrent.futures, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; HERE=ROOT/'studies'/'common'
for p in (HERE, ROOT/'reasoning_population_fidelity'/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from suite_core import SCHEMA, build_requests, load_registry, static_report
from openrouter_preflight import choose_endpoint, endpoint_healthy
from paid_runner import one, ceiling, write_checkpoint


def run(study_id: str, spend_cap: float, outdir: Path, concurrency: int=8, max_attempts: int=6):
    if os.getenv('ENABLE_PAID_STUDY_SUITE')!='I_ACCEPT_PAID_INFERENCE': raise RuntimeError('Paid authorization missing')
    key=os.getenv('OPENROUTER_API_KEY')
    if not key: raise RuntimeError('OPENROUTER_API_KEY missing')
    reg=load_registry(); study=reg['studies'][study_id]
    if spend_cap>float(study['study_spend_cap_usd'])+1e-12: raise RuntimeError('Requested cap exceeds registered cap')
    if static_report(study_id)['status']!='PASS_STATIC': raise RuntimeError('Static preflight failed')
    rows=build_requests(study_id); schema=json.loads(SCHEMA.read_text()); row_by_id={r['request_id']:r for r in rows}
    eps={}
    for mk in sorted({r['model_key'] for r in rows}):
        cfg=reg['models'][mk]; ep=choose_endpoint(cfg['id'],key,cfg['provider_name'])
        if not endpoint_healthy(ep): raise RuntimeError(f'Endpoint unhealthy: {ep}')
        eps[mk]=ep
    if 'deepseek_v4_flash' in eps and eps['deepseek_v4_flash']['tag']!='open-inference/fp8': raise RuntimeError(eps)
    single=sum(ceiling(r,eps[r['model_key']]) for r in rows)
    if single>spend_cap+1e-12: raise RuntimeError(f'Single-pass ceiling {single:.6f} exceeds cap {spend_cap:.6f}')
    attempts=[]; successes={}; raw={}; spent=0.0
    print(json.dumps({'status':'PARALLEL_PAID_STUDY_START','study_id':study_id,'requests':len(rows),'concurrency':concurrency,'max_attempts':max_attempts,'single_pass_ceiling_usd':round(single,6),'spend_cap_usd':spend_cap,'truth_loaded':False},indent=2))
    for attempt_no in range(1,max_attempts+1):
        missing=[r for r in rows if r['request_id'] not in successes]
        if not missing: break
        selected=[]; projected=spent
        for r in missing:
            c=ceiling(r,eps[r['model_key']])
            if projected+c>spend_cap+1e-12: break
            selected.append(r); projected+=c
        if not selected: break
        print(json.dumps({'phase':'attempt_wave_start','attempt':attempt_no,'missing_before':len(missing),'selected':len(selected)}))
        completed=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs={pool.submit(one,r,schema,eps[r['model_key']],key,attempt_no):r for r in selected}
            for fut in concurrent.futures.as_completed(futs):
                r=futs[fut]; rec,parsed=fut.result(); attempts.append(rec); spent+=float(rec.get('accounted_upper_bound_usd') or 0)
                if parsed is not None:
                    successes[r['request_id']]=rec; raw[r['request_id']]={'request_id':r['request_id'],'anon_id':r['anon_id'],'arm_id':r['arm_id'],'response':parsed}
                completed+=1
                if completed%50==0:
                    s=write_checkpoint(outdir,key,study_id,attempts,raw,successes,rows,row_by_id,study,reg,eps,spend_cap)
                    print(json.dumps({'phase':'attempt_wave_progress','attempt':attempt_no,'completed':completed,'schema_valid':s['schema_valid'],'remaining':s['remaining_failures'],'accounted_usd':s['accounted_upper_bound_usd']}))
        s=write_checkpoint(outdir,key,study_id,attempts,raw,successes,rows,row_by_id,study,reg,eps,spend_cap)
        print(json.dumps({'phase':'attempt_wave_end','attempt':attempt_no,'schema_valid':s['schema_valid'],'remaining':s['remaining_failures'],'accounted_usd':s['accounted_upper_bound_usd']}))
    summary=write_checkpoint(outdir,key,study_id,attempts,raw,successes,rows,row_by_id,study,reg,eps,spend_cap,final=True)
    print(json.dumps(summary,indent=2,sort_keys=True))
    if summary['remaining_failures']: raise RuntimeError(f"Study incomplete: {summary['remaining_failures']} unresolved")
    print('PARALLEL_FOLLOWUP_STUDY_PASS'); return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('study_id'); ap.add_argument('--spend-cap',type=float,required=True); ap.add_argument('--outdir',required=True); ap.add_argument('--concurrency',type=int,default=8); ap.add_argument('--max-attempts',type=int,default=6)
    a=ap.parse_args(); run(a.study_id,a.spend_cap,Path(a.outdir),a.concurrency,a.max_attempts)
