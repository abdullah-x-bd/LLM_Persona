from __future__ import annotations
import argparse, concurrent.futures, json, os, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; HERE=ROOT/'studies'/'common'
for p in (HERE, ROOT/'reasoning_population_fidelity'/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from suite_core import SCHEMA, build_requests, load_registry, static_report
from openrouter_preflight import choose_endpoint, endpoint_healthy
from paid_runner import one, ceiling, encrypt_rows


def write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,phase,final=False):
    outdir.mkdir(parents=True,exist_ok=True)
    row_by_id={r['request_id']:r for r in rows}; by_arm={a['id']:0 for a in study['arms']}
    for rid in raw: by_arm[row_by_id[rid]['arm_id']]+=1
    missing=len(rows)-len(raw)
    (outdir/'attempts.json').write_text(json.dumps(sorted(attempts,key=lambda x:(x['request_id'],x.get('attempt',0))),indent=2,sort_keys=True))
    encrypt_rows([raw[k] for k in sorted(raw)],outdir/'raw_results.enc.b64',key,study_id)
    summary={'study_id':study_id,'planned_requests':len(rows),'schema_valid':len(raw),'remaining_failures':missing,'by_arm':by_arm,'attempts':len(attempts),'accounted_upper_bound_usd':round(spent,6),'spend_cap_usd':cap,'provider_names':{'deepseek_v4_flash':'OpenInference'},'endpoint_tags':{'deepseek_v4_flash':ep['tag']},'allow_fallbacks':False,'data_collection':'deny','truth_loaded':False,'all_schema_valid':missing==0,'checkpoint_phase':phase,'checkpoint_final':final}
    (outdir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
    return summary


def progress(label,completed,total,raw,attempts,rows,start,spent,extra=None):
    elapsed=max(0.001,time.perf_counter()-start); rpm=completed/elapsed*60; eta=(total-completed)/max(rpm,1e-9)
    by={'thin_off':0,'thin_high':0}; rmap={r['request_id']:r for r in rows}
    for rid in raw: by[rmap[rid]['arm_id']]+=1
    x={'phase':label,'completed':completed,'total':total,'valid':len(raw),'failed_so_far':completed-len(raw),'thin_off_valid':by['thin_off'],'thin_high_valid':by['thin_high'],'elapsed_min':round(elapsed/60,2),'throughput_req_per_min':round(rpm,2),'eta_first_pass_min':round(eta,1),'accounted_usd':round(spent,6)}
    if extra: x.update(extra)
    print(json.dumps(x),flush=True)


def run(outdir: Path,cap: float,concurrency: int):
    if os.getenv('ENABLE_PAID_STUDY_SUITE')!='I_ACCEPT_PAID_INFERENCE': raise RuntimeError('paid auth missing')
    key=os.getenv('OPENROUTER_API_KEY');
    if not key: raise RuntimeError('OPENROUTER_API_KEY missing')
    study_id='S03_persona_reasoning_factorial'; reg=load_registry(); study=reg['studies'][study_id]
    assert static_report(study_id)['status']=='PASS_STATIC'
    rows=build_requests(study_id)
    # Interleave arms by respondent so slow high-reasoning work starts immediately.
    rows=sorted(rows,key=lambda r:(r['anon_id'],0 if r['arm_id']=='thin_high' else 1))
    schema=json.loads(SCHEMA.read_text()); cfg=reg['models']['deepseek_v4_flash']; ep=choose_endpoint(cfg['id'],key,cfg['provider_name'])
    if not endpoint_healthy(ep) or ep['tag']!='open-inference/fp8': raise RuntimeError(f'bad endpoint {ep}')
    single=sum(ceiling(r,ep) for r in rows)
    if single>cap+1e-12: raise RuntimeError(f'single-pass ceiling {single} > cap {cap}')
    print(json.dumps({'status':'S03_FAST_START','requests':len(rows),'concurrency':concurrency,'single_pass_ceiling_usd':round(single,6),'cap_usd':cap,'endpoint':ep['tag'],'truth_loaded':False}),flush=True)
    attempts=[]; raw={}; spent=0.0; start=time.perf_counter(); completed=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs={pool.submit(one,r,schema,ep,key,1):r for r in rows}
        for fut in concurrent.futures.as_completed(futs):
            r=futs[fut]; rec,parsed=fut.result(); attempts.append(rec); spent+=float(rec.get('accounted_upper_bound_usd') or 0)
            if parsed is not None: raw[r['request_id']]={'request_id':r['request_id'],'anon_id':r['anon_id'],'arm_id':r['arm_id'],'response':parsed}
            completed+=1
            if completed%25==0 or completed==len(rows): progress('first_pass',completed,len(rows),raw,attempts,rows,start,spent)
            if completed%50==0: write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,'first_pass')
    write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,'first_pass_complete')
    for cycle in range(2,8):
        missing=[r for r in rows if r['request_id'] not in raw]
        if not missing: break
        selected=[]; projected=spent
        for r in missing:
            c=ceiling(r,ep)
            if projected+c>cap+1e-12: break
            selected.append(r); projected+=c
        if not selected: break
        print(json.dumps({'phase':'retry_wave_start','cycle':cycle,'missing_before':len(missing),'selected':len(selected),'concurrency':concurrency}),flush=True)
        done=0; wave_start=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs={pool.submit(one,r,schema,ep,key,cycle):r for r in selected}
            for fut in concurrent.futures.as_completed(futs):
                r=futs[fut]; rec,parsed=fut.result(); attempts.append(rec); spent+=float(rec.get('accounted_upper_bound_usd') or 0)
                if parsed is not None: raw[r['request_id']]={'request_id':r['request_id'],'anon_id':r['anon_id'],'arm_id':r['arm_id'],'response':parsed}
                done+=1
                if done%25==0 or done==len(selected):
                    rem=len(rows)-len(raw); print(json.dumps({'phase':'retry_wave_progress','cycle':cycle,'completed_in_wave':done,'selected':len(selected),'valid_total':len(raw),'remaining':rem,'wave_elapsed_min':round((time.perf_counter()-wave_start)/60,2),'accounted_usd':round(spent,6)}),flush=True)
                if done%50==0: write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,f'retry_{cycle}')
        write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,f'retry_{cycle}_complete')
    summary=write_ckpt(outdir,key,study_id,attempts,raw,rows,study,reg,ep,spent,cap,'final',final=True)
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)
    if summary['remaining_failures']: raise RuntimeError(f"S03 incomplete: {summary['remaining_failures']} missing")
    print('S03_FAST_2000_PASS',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); ap.add_argument('--cap',type=float,default=0.85); ap.add_argument('--concurrency',type=int,default=16)
    a=ap.parse_args(); run(Path(a.outdir),a.cap,a.concurrency)
