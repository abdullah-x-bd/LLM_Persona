from __future__ import annotations
import argparse, base64, concurrent.futures, gzip, hashlib, json, os, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'studies'/'common'
for p in (HERE, ROOT/'reasoning_population_fidelity'/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from suite_core import SCHEMA, build_requests, load_registry, static_report
from openrouter_preflight import choose_endpoint, endpoint_healthy
from paid_runner import AAD, one, ceiling, encrypt_rows


def decrypt_rows(path: Path, key: str, study_id: str) -> list[dict]:
    blob=base64.b64decode(path.read_text(encoding='ascii'))
    nonce,cipher=blob[:12],blob[12:]
    aes=hashlib.sha256(AAD+b'|'+study_id.encode()+b'|'+key.encode()).digest()
    comp=AESGCM(aes).decrypt(nonce,cipher,AAD+b'|'+study_id.encode())
    raw=gzip.decompress(comp).decode('utf-8')
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def checkpoint(outdir: Path, key: str, study_id: str, attempts: list[dict], raw: dict, rows: list[dict], study: dict, reg: dict, eps: dict, seed_summary: dict, recovery_spent: float, recovery_cap: float, cycle: int, final: bool=False) -> dict:
    outdir.mkdir(parents=True,exist_ok=True)
    successes=set(raw); row_by_id={r['request_id']:r for r in rows}
    by_arm={a['id']:0 for a in study['arms']}
    for rid in successes: by_arm[row_by_id[rid]['arm_id']]+=1
    missing=[r for r in rows if r['request_id'] not in successes]
    (outdir/'attempts.json').write_text(json.dumps(sorted(attempts,key=lambda x:(x['request_id'],x.get('attempt',0),x.get('recovery_cycle',0))),indent=2,sort_keys=True),encoding='utf-8')
    encrypt_rows([raw[k] for k in sorted(raw)],outdir/'raw_results.enc.b64',key,study_id)
    summary={'study_id':study_id,'planned_requests':len(rows),'schema_valid':len(successes),'remaining_failures':len(missing),'by_arm':by_arm,'attempts_preserved':len(attempts),'seed_schema_valid':int(seed_summary['schema_valid']),'seed_accounted_upper_bound_usd':float(seed_summary['accounted_upper_bound_usd']),'recovery_accounted_upper_bound_usd':round(recovery_spent,6),'combined_preserved_accounted_upper_bound_usd':round(float(seed_summary['accounted_upper_bound_usd'])+recovery_spent,6),'recovery_additional_cap_usd':recovery_cap,'provider_names':{k:reg['models'][k]['provider_name'] for k in eps},'endpoint_tags':{k:v['tag'] for k,v in eps.items()},'allow_fallbacks':False,'data_collection':'deny','truth_loaded':False,'all_schema_valid':len(missing)==0,'recovery_cycle_completed':cycle,'checkpoint_final':final,'recovery_note':'Operational recovery from saved S01 first-pass checkpoint after GitHub 180-minute timeout; scientific prompts/model/reasoning/schema unchanged; retry scheduling parallelized only.'}
    (outdir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True),encoding='utf-8')
    return summary


def run(seed_dir: Path, outdir: Path, recovery_cap: float, max_cycles: int, concurrency: int) -> dict:
    if os.getenv('ENABLE_PAID_STUDY_SUITE')!='I_ACCEPT_PAID_INFERENCE': raise RuntimeError('Paid authorization missing')
    key=os.getenv('OPENROUTER_API_KEY')
    if not key: raise RuntimeError('OPENROUTER_API_KEY missing')
    study_id='S01_second_model_reasoning'; reg=load_registry(); study=reg['studies'][study_id]
    if static_report(study_id)['status']!='PASS_STATIC': raise RuntimeError('S01 static preflight failed')
    seed_summary=json.load(open(seed_dir/'summary.json'))
    assert seed_summary['study_id']==study_id and seed_summary['planned_requests']==2000
    assert seed_summary['schema_valid']==1663 and seed_summary['by_arm']=={'rich_high':679,'rich_off':984}, seed_summary
    assert seed_summary['truth_loaded'] is False and seed_summary['data_collection']=='deny'
    raw_rows=decrypt_rows(seed_dir/'raw_results.enc.b64',key,study_id); raw={r['request_id']:r for r in raw_rows}; assert len(raw)==1663
    attempts=json.load(open(seed_dir/'attempts.json')); rows=build_requests(study_id); schema=json.loads(SCHEMA.read_text())
    eps={}
    for mk in sorted({r['model_key'] for r in rows}):
        cfg=reg['models'][mk]; ep=choose_endpoint(cfg['id'],key,cfg['provider_name'])
        if not endpoint_healthy(ep): raise RuntimeError(f'Endpoint unhealthy: {ep}')
        eps[mk]=ep
    if eps['deepseek_v4_flash']['tag']!='open-inference/fp8': raise RuntimeError(eps)
    recovery_spent=0.0; summary=checkpoint(outdir,key,study_id,attempts,raw,rows,study,reg,eps,seed_summary,recovery_spent,recovery_cap,0)
    print(json.dumps({'status':'S01_RECOVERY_START','seed_valid':summary['schema_valid'],'missing':summary['remaining_failures'],'concurrency':concurrency,'recovery_cap_usd':recovery_cap},indent=2))
    for cycle in range(1,max_cycles+1):
        missing=[r for r in rows if r['request_id'] not in raw]
        if not missing: break
        selected=[]; projected=recovery_spent
        for r in missing:
            c=ceiling(r,eps[r['model_key']])
            if projected+c > recovery_cap+1e-12: break
            selected.append(r); projected+=c
        if not selected: break
        print(json.dumps({'phase':'recovery_cycle_start','cycle':cycle,'missing_before':len(missing),'selected':len(selected)}))
        completed=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs={pool.submit(one,r,schema,eps[r['model_key']],key,1+cycle):r for r in selected}
            for fut in concurrent.futures.as_completed(futs):
                r=futs[fut]; rec,parsed=fut.result(); rec['recovery_cycle']=cycle; attempts.append(rec); recovery_spent += float(rec.get('accounted_upper_bound_usd') or 0)
                if parsed is not None: raw[r['request_id']]={'request_id':r['request_id'],'anon_id':r['anon_id'],'arm_id':r['arm_id'],'response':parsed}
                completed+=1
                if completed%25==0:
                    s=checkpoint(outdir,key,study_id,attempts,raw,rows,study,reg,eps,seed_summary,recovery_spent,recovery_cap,cycle)
                    print(json.dumps({'phase':'recovery_cycle_progress','cycle':cycle,'completed':completed,'valid_total':s['schema_valid'],'remaining':s['remaining_failures'],'recovery_accounted_usd':s['recovery_accounted_upper_bound_usd']}))
        summary=checkpoint(outdir,key,study_id,attempts,raw,rows,study,reg,eps,seed_summary,recovery_spent,recovery_cap,cycle)
        print(json.dumps({'phase':'recovery_cycle_end','cycle':cycle,'valid_total':summary['schema_valid'],'remaining':summary['remaining_failures'],'recovery_accounted_usd':summary['recovery_accounted_upper_bound_usd']}))
    summary=checkpoint(outdir,key,study_id,attempts,raw,rows,study,reg,eps,seed_summary,recovery_spent,recovery_cap,summary.get('recovery_cycle_completed',0),final=True)
    print(json.dumps(summary,indent=2,sort_keys=True))
    if summary['remaining_failures']: raise RuntimeError(f"S01 recovery incomplete: {summary['remaining_failures']} missing")
    print('S01_RECOVERY_2000_PASS'); return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--seed-dir',required=True); ap.add_argument('--outdir',required=True); ap.add_argument('--recovery-cap',type=float,default=0.30); ap.add_argument('--max-cycles',type=int,default=6); ap.add_argument('--concurrency',type=int,default=8)
    a=ap.parse_args(); run(Path(a.seed_dir),Path(a.outdir),a.recovery_cap,a.max_cycles,a.concurrency)
