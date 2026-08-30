from __future__ import annotations

import argparse, hashlib, json, os, random, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

MODEL_CONFIG={
    "openai/gpt-5.6-luna":{"provider":"openai","input_per_m":.20,"output_per_m":1.20},
    "google/gemini-3.7-flash":{"provider":"google-vertex","input_per_m":.375,"output_per_m":1.875},
    "anthropic/claude-sonnet-5":{"provider":"anthropic","input_per_m":2.0,"output_per_m":10.0},
}
BASE_URL="https://openrouter.ai/api/v1/chat/completions"

def load_jsonl(path):
    p=Path(path)
    if not p.exists(): return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def outcome_keys_from_schema(schema:dict)->list[str]:
    keys=list(schema.get("required") or [])
    props=schema.get("properties") or {}
    if not keys or set(keys)!=set(props):
        raise ValueError("Schema must define the same non-empty outcome keys in required and properties")
    return keys

def validate_request_rows(rows):
    if not rows: raise ValueError("No request rows found")
    pairs=[(r["anon_id"],r["condition"]) for r in rows]
    if len(pairs)!=len(set(pairs)): raise AssertionError("Duplicate anon_id/condition request pairs")
    for r in rows:
        if not all(k in r for k in ("anon_id","condition","persona","prompt")): raise AssertionError("Malformed request row")
        if not isinstance(r["condition"],str) or not r["condition"]: raise AssertionError("Invalid condition")

def validate_payload(obj:Any,outcome_keys:list[str]):
    if not isinstance(obj,dict) or set(obj)!=set(outcome_keys): raise ValueError("Wrong top-level keys")
    for k in outcome_keys:
        v=obj[k]
        if not isinstance(v,dict) or set(v)!={"answer","probability_yes"}: raise ValueError(f"Malformed {k}")
        if v["answer"] not in ("yes","no"): raise ValueError(f"Invalid answer {k}")
        p=v["probability_yes"]
        if not isinstance(p,(int,float)) or isinstance(p,bool) or not 0<=float(p)<=1: raise ValueError(f"Invalid probability {k}")
    return obj

def estimate_cost(rows,model,assumed_output_tokens=180):
    cfg=MODEL_CONFIG[model]
    inp=sum(max(1,len(r["prompt"])//4) for r in rows); out=len(rows)*assumed_output_tokens
    return {"requests":len(rows),"approx_input_tokens":inp,"approx_output_tokens":out,
            "approx_cost_usd":inp/1e6*cfg["input_per_m"]+out/1e6*cfg["output_per_m"]}

def deterministic_mock(row,outcome_keys):
    out={}
    for k in outcome_keys:
        h=hashlib.sha256(f"{row['anon_id']}|{row['condition']}|{k}".encode()).digest(); p=(int.from_bytes(h[:4],"big")%10001)/10000
        out[k]={"answer":"yes" if p>=.5 else "no","probability_yes":p}
    return out

def response_format(schema): return {"type":"json_schema","json_schema":{"name":"matched_survey_response","strict":True,"schema":schema}}

def post_json(payload,key,timeout=90):
    req=urllib.request.Request(BASE_URL,data=json.dumps(payload).encode(),method="POST",headers={
        "Authorization":f"Bearer {key}","Content-Type":"application/json",
        "HTTP-Referer":"https://github.com/abdullah-x-bd/LLM_Persona",
        "X-OpenRouter-Title":"LLM Persona Survey Validation","User-Agent":"LLM-Persona/2.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())

def run_one(row,model,schema,outcome_keys,provider,key,max_retries):
    body={"model":model,"messages":[{"role":"user","content":row["prompt"]}],
          "response_format":response_format(schema),"max_tokens":450,
          "provider":{"require_parameters":True,"data_collection":"deny"}}
    if provider: body["provider"].update({"only":[provider],"allow_fallbacks":False})
    last=None
    for attempt in range(max_retries+1):
        try:
            t=time.perf_counter(); resp=post_json(body,key); lat=time.perf_counter()-t
            parsed=validate_payload(json.loads(resp["choices"][0]["message"]["content"]),outcome_keys)
            usage=resp.get("usage") or {}
            return {"anon_id":row["anon_id"],"condition":row["condition"],"survey":row.get("survey"),
                    "model_requested":model,"model_returned":resp.get("model"),"provider_returned":resp.get("provider"),
                    "response_id":resp.get("id"),"latency_seconds":lat,"prompt_tokens":usage.get("prompt_tokens"),
                    "completion_tokens":usage.get("completion_tokens"),"total_tokens":usage.get("total_tokens"),
                    "response":parsed,"attempts":attempt+1,"saved_at_unix":time.time()}
        except Exception as e:
            last=repr(e)
            if attempt<max_retries: time.sleep(min(8,2**attempt+random.random()))
    return {"anon_id":row["anon_id"],"condition":row["condition"],"survey":row.get("survey"),
            "model_requested":model,"error":last,"attempts":max_retries+1,"saved_at_unix":time.time()}

def durable_append(path:Path,obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    line=(json.dumps(obj,ensure_ascii=False)+"\n").encode("utf-8")
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
    try: os.write(fd,line); os.fsync(fd)
    finally: os.close(fd)

def atomic_json(path:Path,obj:dict):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8") as f: json.dump(obj,f,indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
    try: dfd=os.open(path.parent,os.O_RDONLY); os.fsync(dfd); os.close(dfd)
    except OSError: pass

def successful_pairs(path:Path):
    return {(r["anon_id"],r["condition"]) for r in load_jsonl(path) if "error" not in r}

def run_live(rows,schema,outcome_keys,out_path,model,provider,concurrency,max_retries,checkpoint_path=None,error_path=None):
    key=os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("OPENROUTER_API_KEY is not set")
    checkpoint_path=checkpoint_path or out_path.with_suffix(out_path.suffix+".checkpoint.json")
    error_path=error_path or out_path.with_suffix(out_path.suffix+".errors.jsonl")
    existing=successful_pairs(out_path); todo=[r for r in rows if (r["anon_id"],r["condition"]) not in existing]
    lock=threading.Lock(); failures=0; completed_now=0; started=time.time(); already=len(existing)
    atomic_json(checkpoint_path,{"model":model,"total_requested":len(rows),"already_complete":already,"remaining":len(todo),"status":"running","updated_at_unix":time.time()})
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures={ex.submit(run_one,r,model,schema,outcome_keys,provider,key,max_retries):r for r in todo}
            for fut in as_completed(futures):
                result=fut.result()
                with lock:
                    if "error" in result: failures+=1; durable_append(error_path,result)
                    else: durable_append(out_path,result); completed_now+=1; existing.add((result["anon_id"],result["condition"]))
                    atomic_json(checkpoint_path,{"model":model,"total_requested":len(rows),"already_complete_at_start":already,
                        "completed_total":len(existing),"remaining":len(rows)-len(existing),"completed_this_run":completed_now,
                        "failures_this_run":failures,"status":"running","elapsed_seconds":time.time()-started,"updated_at_unix":time.time()})
    finally:
        atomic_json(checkpoint_path,{"model":model,"total_requested":len(rows),"completed_total":len(existing),
            "remaining":len(rows)-len(existing),"completed_this_run":completed_now,"failures_this_run":failures,
            "status":"complete" if len(existing)==len(rows) else "interrupted_or_incomplete",
            "elapsed_seconds":time.time()-started,"updated_at_unix":time.time()})
    print(json.dumps({"already_complete":already,"attempted":len(todo),"saved_successfully":completed_now,"failures":failures,"remaining":len(rows)-len(existing)},indent=2))
    if failures or len(existing)!=len(rows): raise RuntimeError(f"Run incomplete: {failures} failures, {len(rows)-len(existing)} remaining; safe to resume")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--requests",required=True); ap.add_argument("--schema",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--model",default="openai/gpt-5.6-luna",choices=sorted(MODEL_CONFIG)); ap.add_argument("--provider")
    ap.add_argument("--concurrency",type=int,default=20); ap.add_argument("--max-retries",type=int,default=3); ap.add_argument("--limit",type=int)
    ap.add_argument("--condition"); ap.add_argument("--checkpoint"); ap.add_argument("--errors"); ap.add_argument("--dry-run",action="store_true"); ap.add_argument("--mock",action="store_true")
    args=ap.parse_args(); rows=load_jsonl(args.requests)
    if args.condition: rows=[r for r in rows if r["condition"]==args.condition]
    if args.limit is not None: rows=rows[:args.limit]
    validate_request_rows(rows); schema=json.loads(Path(args.schema).read_text(encoding="utf-8")); outcome_keys=outcome_keys_from_schema(schema)
    print(json.dumps(estimate_cost(rows,args.model),indent=2))
    if args.dry_run:return
    if args.mock:
        out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
        for r in rows: durable_append(out,{"anon_id":r["anon_id"],"condition":r["condition"],"survey":r.get("survey"),"model_requested":"mock","response":validate_payload(deterministic_mock(r,outcome_keys),outcome_keys)})
        return
    provider=args.provider if args.provider is not None else MODEL_CONFIG[args.model]["provider"]
    run_live(rows,schema,outcome_keys,Path(args.out),args.model,provider,args.concurrency,args.max_retries,Path(args.checkpoint) if args.checkpoint else None,Path(args.errors) if args.errors else None)
if __name__=="__main__": main()
