from __future__ import annotations

import argparse
import base64
import concurrent.futures
import gzip
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
for p in (HERE, ROOT/"reasoning_population_fidelity"/"src"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from suite_core import SCHEMA, build_requests, load_registry, static_report
from openrouter_preflight import choose_endpoint
from paid_pilot import BASE, request_json, usage_record

LOCK=threading.Lock()
AAD=b"LLM_PERSONA_FOLLOWUP_SUITE_V1"


def validate_compact(obj: dict) -> None:
    if not isinstance(obj,dict) or set(obj)!={"a","p"}: raise ValueError("wrong top-level keys")
    if not isinstance(obj["a"],list) or len(obj["a"])!=6 or any(type(x) is not int or x not in (0,1) for x in obj["a"]): raise ValueError("bad a")
    if not isinstance(obj["p"],list) or len(obj["p"])!=6: raise ValueError("bad p")
    for x in obj["p"]:
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not 0 <= float(x) <= 1: raise ValueError("bad probability")


def reasoning_payload(level: str) -> dict:
    if level=="off": return {"enabled":False,"exclude":True}
    if level=="medium": return {"effort":"medium","exclude":True}
    raise ValueError(level)


def payload(row: dict, schema: dict, endpoint: dict, cap_prices: dict) -> dict:
    return {
        "model":row["model"],
        "messages":[{"role":"user","content":row["prompt"]}],
        "temperature":0,
        "top_p":1,
        "max_tokens":int(row["max_completion_tokens"]),
        "reasoning":reasoning_payload(row["reasoning"]),
        "response_format":{"type":"json_schema","json_schema":{"name":"population_simulation_response","strict":True,"schema":schema}},
        "provider":{
            "order":[endpoint["tag"]],
            "allow_fallbacks":False,
            "require_parameters":True,
            "data_collection":"deny",
            "max_price":{"prompt":cap_prices["input_per_m"],"completion":cap_prices["output_per_m"]}
        },
        "usage":{"include":True}
    }


def ceiling(row: dict, ep: dict) -> float:
    prompt_tokens=max(1,(len(row["prompt"])+2)//3)
    return prompt_tokens/1e6*float(ep["input_per_m"])+int(row["max_completion_tokens"])/1e6*float(ep["output_per_m"])


def encrypt_rows(rows: list[dict], out: Path, key: str, study_id: str) -> None:
    raw="".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in rows).encode()
    comp=gzip.compress(raw,9); nonce=os.urandom(12)
    aes=hashlib.sha256(AAD+b"|"+study_id.encode()+b"|"+key.encode()).digest()
    blob=nonce+AESGCM(aes).encrypt(nonce,comp,AAD+b"|"+study_id.encode())
    out.write_text(base64.b64encode(blob).decode("ascii"),encoding="ascii")


def one(row: dict, schema: dict, ep: dict, key: str, attempt: int) -> tuple[dict,dict|None]:
    start=time.perf_counter(); c=ceiling(row,ep)
    try:
        response=request_json(f"{BASE}/chat/completions",key,payload(row,schema,ep,ep),timeout=180)
        accounting=usage_record(response,key)
        choice=(response.get("choices") or [{}])[0]; content=(choice.get("message") or {}).get("content")
        parsed=json.loads(content); validate_compact(parsed)
        rec={"request_id":row["request_id"],"anon_id":row["anon_id"],"arm_id":row["arm_id"],"model":row["model"],"reasoning":row["reasoning"],"attempt":attempt,"schema_valid":True,"finish_reason":choice.get("finish_reason"),"latency_seconds":round(time.perf_counter()-start,4),**accounting}
        rec["accounted_upper_bound_usd"]=float(rec.get("cost_usd")) if rec.get("cost_usd") is not None else c
        return rec,parsed
    except Exception as exc:
        return {"request_id":row["request_id"],"anon_id":row["anon_id"],"arm_id":row["arm_id"],"model":row["model"],"reasoning":row["reasoning"],"attempt":attempt,"schema_valid":False,"error":f"{type(exc).__name__}:{str(exc)[:240]}","latency_seconds":round(time.perf_counter()-start,4),"cost_usd":None,"accounted_upper_bound_usd":c},None


def run(study_id: str, spend_cap: float, outdir: Path) -> dict:
    if os.getenv("ENABLE_PAID_STUDY_SUITE") != "I_ACCEPT_PAID_INFERENCE":
        raise RuntimeError("Paid authorization environment variable is not set")
    key=os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("OPENROUTER_API_KEY is not set")
    reg=load_registry(); study=reg["studies"][study_id]
    if spend_cap > float(study["study_spend_cap_usd"])+1e-12: raise RuntimeError("Requested cap exceeds registered study cap")
    st=static_report(study_id)
    if st["status"]!="PASS_STATIC": raise RuntimeError(f"Static preflight not ready: {st['status']}")
    rows=build_requests(study_id); schema=json.loads(SCHEMA.read_text())
    eps={}
    for mk in sorted({r["model_key"] for r in rows}): eps[mk]=choose_endpoint(reg["models"][mk]["id"],key,reg["privacy"]["provider_name"])
    single=sum(ceiling(r,eps[r["model_key"]]) for r in rows)
    if single > spend_cap+1e-12: raise RuntimeError(f"Live hard single-pass ceiling {single:.6f} exceeds cap {spend_cap:.6f}")
    attempts=[]; successes={}; raw={}
    concurrency=6
    print(json.dumps({"status":"PAID_STUDY_START","study_id":study_id,"requests":len(rows),"respondents":len({r['anon_id'] for r in rows}),"single_pass_ceiling_usd":round(single,6),"spend_cap_usd":spend_cap,"endpoints":eps,"truth_loaded":False},indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures={pool.submit(one,r,schema,eps[r["model_key"]],key,1):r for r in rows}
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            r=futures[f]; rec,parsed=f.result(); attempts.append(rec)
            if parsed is not None: successes[r["request_id"]]=rec; raw[r["request_id"]]={"request_id":r["request_id"],"anon_id":r["anon_id"],"arm_id":r["arm_id"],"response":parsed}
            if i%100==0: print(json.dumps({"phase":"first_pass","completed":i,"schema_valid":len(successes),"accounted_usd":round(sum(float(x.get('accounted_upper_bound_usd') or 0) for x in attempts),6)}))
    missing=[r for r in rows if r["request_id"] not in successes]
    for attempt_no in (2,3):
        if not missing: break
        for r in list(missing):
            spent=sum(float(x.get("accounted_upper_bound_usd") or 0) for x in attempts); c=ceiling(r,eps[r["model_key"]])
            if spent+c > spend_cap+1e-12: continue
            rec,parsed=one(r,schema,eps[r["model_key"]],key,attempt_no); attempts.append(rec)
            if parsed is not None: successes[r["request_id"]]=rec; raw[r["request_id"]]={"request_id":r["request_id"],"anon_id":r["anon_id"],"arm_id":r["arm_id"],"response":parsed}
        missing=[r for r in rows if r["request_id"] not in successes]
    outdir.mkdir(parents=True,exist_ok=True)
    attempts_safe=sorted(attempts,key=lambda x:(x["request_id"],x["attempt"]))
    (outdir/"attempts.json").write_text(json.dumps(attempts_safe,indent=2,sort_keys=True),encoding="utf-8")
    encrypt_rows([raw[k] for k in sorted(raw)],outdir/"raw_results.enc.b64",key,study_id)
    by_arm={arm["id"]:0 for arm in study["arms"]}
    for rid in successes: by_arm[next(r["arm_id"] for r in rows if r["request_id"]==rid)]+=1
    summary={"study_id":study_id,"planned_requests":len(rows),"schema_valid":len(successes),"remaining_failures":len(missing),"by_arm":by_arm,"attempts":len(attempts),"accounted_upper_bound_usd":round(sum(float(x.get("accounted_upper_bound_usd") or 0) for x in attempts),6),"spend_cap_usd":spend_cap,"provider_name":reg["privacy"]["provider_name"],"endpoint_tags":{k:v["tag"] for k,v in eps.items()},"allow_fallbacks":False,"data_collection":"deny","truth_loaded":False,"all_schema_valid":len(missing)==0}
    (outdir/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))
    if missing: raise RuntimeError(f"Study incomplete: {len(missing)} unresolved requests")
    return summary


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("study_id"); ap.add_argument("--spend-cap",type=float,required=True); ap.add_argument("--outdir",default="/tmp/followup_study")
    a=ap.parse_args(); run(a.study_id,a.spend_cap,Path(a.outdir))

if __name__=="__main__": main()
