from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
for p in (HERE,ROOT/'reasoning_population_fidelity'/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from suite_core import SCHEMA, build_requests
from openrouter_preflight import BASE, get_json, per_m
from paid_runner import one

STUDY='S01_second_model_reasoning'
MODEL='deepseek/deepseek-v4-flash-0731'
ENDPOINT_TAG='open-inference/fp8'
CONCURRENCY=8
RESPONDENTS=4
HARD_CAP=0.02


def exact_endpoint(key:str)->dict:
    author,slug=MODEL.split('/',1)
    eps=(get_json(f'{BASE}/models/{author}/{slug}/endpoints',key).get('data',{}) or {}).get('endpoints') or []
    matches=[e for e in eps if e.get('tag')==ENDPOINT_TAG]
    if len(matches)!=1: raise RuntimeError(f'Expected exactly one {ENDPOINT_TAG} endpoint, got {len(matches)}')
    e=matches[0]; status=e.get('status'); params=set(e.get('supported_parameters') or [])
    if isinstance(status,(int,float)) and status<0: raise RuntimeError(f'Endpoint unhealthy: status={status}')
    required={'reasoning','response_format','max_tokens'}
    if not required.issubset(params): raise RuntimeError(f'Endpoint lacks {sorted(required-params)}')
    p=e.get('pricing') or {}; pin=per_m(p.get('prompt')); pout=per_m(p.get('completion'))
    if pin is None or pout is None: raise RuntimeError('Endpoint pricing missing')
    return {'tag':ENDPOINT_TAG,'name':e.get('name') or e.get('provider_name'),'status':status,'input_per_m':pin,'output_per_m':pout,'supported_parameters':sorted(params)}


def ceil_cost(row,ep):
    prompt=max(1,(len(row['prompt'])+2)//3)
    return prompt/1e6*ep['input_per_m']+int(row['max_completion_tokens'])/1e6*ep['output_per_m']


def main():
    if os.getenv('ENABLE_PROVIDER_PROBE')!='YES_ENGINEERING_ONLY': raise RuntimeError('Provider probe authorization missing')
    key=os.getenv('OPENROUTER_API_KEY')
    if not key: raise RuntimeError('OPENROUTER_API_KEY missing')
    ep=exact_endpoint(key)
    rows=build_requests(STUDY)
    ids=sorted({r['anon_id'] for r in rows})[:RESPONDENTS]; keep=set(ids)
    rows=[r for r in rows if r['anon_id'] in keep]
    assert len(rows)==RESPONDENTS*2
    schema=json.loads(SCHEMA.read_text())
    hard=sum(ceil_cost(r,ep) for r in rows)
    if hard>HARD_CAP: raise RuntimeError((hard,HARD_CAP))
    print(json.dumps({'status':'PROBE_START','scientific_data':False,'truth_loaded':False,'substantive_outputs_inspected':False,'endpoint':ep,'requests':len(rows),'concurrency':CONCURRENCY,'hard_ceiling_usd':round(hard,8),'hard_cap_usd':HARD_CAP},indent=2,sort_keys=True))
    started=time.perf_counter(); attempts=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futs={pool.submit(one,r,schema,ep,key,1):r for r in rows}
        for f in concurrent.futures.as_completed(futs):
            r=futs[f]; rec,parsed=f.result(); attempts.append(rec)
    valid=sum(1 for a in attempts if a.get('schema_valid'))
    errors={}
    for a in attempts:
        if not a.get('schema_valid'):
            err=a.get('error','unknown'); errors[err]=errors.get(err,0)+1
    known=sum(float(a.get('cost_usd') or 0) for a in attempts if a.get('cost_usd') is not None)
    lats=[float(a['latency_seconds']) for a in attempts if a.get('latency_seconds') is not None]
    length=sum(1 for a in attempts if a.get('finish_reason')=='length')
    provider_names=sorted({str(a.get('provider_name')) for a in attempts if a.get('provider_name')})
    models_returned=sorted({str(a.get('model_returned')) for a in attempts if a.get('model_returned')})
    by_arm={}
    for arm in ('rich_off','rich_high'):
        aa=[x for x in attempts if x['arm_id']==arm]
        by_arm[arm]={
            'planned':len(aa),
            'valid':sum(1 for x in aa if x.get('schema_valid')),
            'length_finishes':sum(1 for x in aa if x.get('finish_reason')=='length'),
            'max_latency_seconds':round(max(float(x.get('latency_seconds') or 0) for x in aa),4),
            'mean_latency_seconds':round(sum(float(x.get('latency_seconds') or 0) for x in aa)/len(aa),4),
            'max_reasoning_tokens':max(int(x.get('reasoning_tokens') or 0) for x in aa),
            'max_completion_tokens':max(int(x.get('completion_tokens') or 0) for x in aa),
            'known_cost_usd':round(sum(float(x.get('cost_usd') or 0) for x in aa if x.get('cost_usd') is not None),8),
        }
    out={
        'status':'PASS' if valid==len(rows) and length==0 else 'FAIL',
        'scientific_data':False,'truth_loaded':False,'substantive_outputs_inspected':False,
        'endpoint':ep,'requests':len(rows),'schema_valid':valid,'length_finishes':length,'errors':errors,
        'concurrency':CONCURRENCY,'wall_seconds':round(time.perf_counter()-started,4),
        'known_realized_cost_usd':round(known,8),'hard_ceiling_usd':round(hard,8),'hard_cap_usd':HARD_CAP,
        'max_latency_seconds':round(max(lats),4) if lats else None,'provider_names_returned':provider_names,'models_returned':models_returned,'by_arm':by_arm,
    }
    Path('/tmp/deepseek_openinference_probe').mkdir(parents=True,exist_ok=True)
    Path('/tmp/deepseek_openinference_probe/summary.json').write_text(json.dumps(out,indent=2,sort_keys=True),encoding='utf-8')
    Path('/tmp/deepseek_openinference_probe/attempts.json').write_text(json.dumps(attempts,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(out,indent=2,sort_keys=True))
    if out['status']!='PASS': raise SystemExit(2)

if __name__=='__main__': main()
