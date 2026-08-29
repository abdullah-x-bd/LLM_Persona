from __future__ import annotations

import argparse, hashlib, json, os, random, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

OUTCOME_KEYS=["mobile_ability","mobile_3m","computer_ability","internet_ability","internet_3m","copy_paste"]
MODEL_CONFIG={"openai/gpt-5.6-luna":{"provider":"openai","input_per_m":.20,"output_per_m":1.20},"google/gemini-3.7-flash":{"provider":"google-vertex","input_per_m":.375,"output_per_m":1.875},"anthropic/claude-sonnet-5":{"provider":"anthropic","input_per_m":2.0,"output_per_m":10.0}}
BASE_URL="https://openrouter.ai/api/v1/chat/completions"

def load_jsonl(path):return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
def validate_request_rows(rows):
    if not rows:raise ValueError("No request rows found")
    pairs=[(r["anon_id"],r["condition"]) for r in rows]
    if len(pairs)!=len(set(pairs)):raise AssertionError("Duplicate anon_id/condition request pairs")
    if not {r["condition"] for r in rows}.issubset({"thin","rich"}):raise AssertionError("Unexpected condition")
    for r in rows:
        if not all(k in r for k in ("anon_id","condition","persona","prompt")):raise AssertionError("Malformed request row")
def validate_payload(obj:Any):
    if not isinstance(obj,dict) or set(obj)!=set(OUTCOME_KEYS):raise ValueError("Wrong top-level keys")
    for k in OUTCOME_KEYS:
        v=obj[k]
        if not isinstance(v,dict) or set(v)!={"answer","probability_yes"}:raise ValueError(f"Malformed {k}")
        if v["answer"] not in ("yes","no"):raise ValueError(f"Invalid answer {k}")
        p=v["probability_yes"]
        if not isinstance(p,(int,float)) or not 0<=float(p)<=1:raise ValueError(f"Invalid probability {k}")
    return obj
def estimate_cost(rows,model,assumed_output_tokens=180):
    cfg=MODEL_CONFIG[model];inp=sum(max(1,len(r["prompt"])//4) for r in rows);out=len(rows)*assumed_output_tokens
    return {"requests":len(rows),"approx_input_tokens":inp,"approx_output_tokens":out,"approx_cost_usd":inp/1e6*cfg["input_per_m"]+out/1e6*cfg["output_per_m"]}
def deterministic_mock(row):
    out={}
    for k in OUTCOME_KEYS:
        h=hashlib.sha256(f"{row['anon_id']}|{row['condition']}|{k}".encode()).digest();p=(int.from_bytes(h[:4],"big")%10001)/10000
        out[k]={"answer":"yes" if p>=.5 else "no","probability_yes":p}
    return out
def response_format(schema):return {"type":"json_schema","json_schema":{"name":"cams_survey_response","strict":True,"schema":schema}}
def post_json(payload,key,timeout=90):
    req=urllib.request.Request(BASE_URL,data=json.dumps(payload).encode(),method="POST",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://github.com/abdullah-x-bd/LLM_Persona","X-OpenRouter-Title":"LLM Persona CAMS Validation","User-Agent":"LLM-Persona/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
def run_one(row,model,schema,provider,key,max_retries):
    body={"model":model,"messages":[{"role":"user","content":row["prompt"]}],"response_format":response_format(schema),"max_tokens":450,"provider":{"require_parameters":True,"data_collection":"deny"}}
    if provider:body["provider"].update({"only":[provider],"allow_fallbacks":False})
    last=None
    for attempt in range(max_retries+1):
        try:
            t=time.perf_counter();resp=post_json(body,key);lat=time.perf_counter()-t;parsed=validate_payload(json.loads(resp["choices"][0]["message"]["content"]));usage=resp.get("usage") or {}
            return {"anon_id":row["anon_id"],"condition":row["condition"],"model_requested":model,"model_returned":resp.get("model"),"provider_returned":resp.get("provider"),"response_id":resp.get("id"),"latency_seconds":lat,"prompt_tokens":usage.get("prompt_tokens"),"completion_tokens":usage.get("completion_tokens"),"total_tokens":usage.get("total_tokens"),"response":parsed,"attempts":attempt+1}
        except Exception as e:
            last=repr(e)
            if attempt<max_retries:time.sleep(min(8,2**attempt+random.random()))
    return {"anon_id":row["anon_id"],"condition":row["condition"],"model_requested":model,"error":last,"attempts":max_retries+1}
def run_live(rows,schema,out_path,model,provider,concurrency,max_retries):
    key=os.getenv("OPENROUTER_API_KEY")
    if not key:raise RuntimeError("OPENROUTER_API_KEY is not set")
    existing=set()
    if out_path.exists():
        for r in load_jsonl(out_path):
            if "error" not in r:existing.add((r["anon_id"],r["condition"]))
    todo=[r for r in rows if (r["anon_id"],r["condition"]) not in existing];out_path.parent.mkdir(parents=True,exist_ok=True);lock=threading.Lock();failures=0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures={ex.submit(run_one,r,model,schema,provider,key,max_retries):r for r in todo}
        for fut in as_completed(futures):
            result=fut.result();failures+=int("error" in result)
            with lock,out_path.open("a",encoding="utf-8") as f:f.write(json.dumps(result,ensure_ascii=False)+"\n")
    print(json.dumps({"already_complete":len(existing),"attempted":len(todo),"failures":failures},indent=2))
    if failures:raise RuntimeError(f"{failures} requests failed; runner is resumable")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--requests",required=True);ap.add_argument("--schema",required=True);ap.add_argument("--out",required=True);ap.add_argument("--model",default="openai/gpt-5.6-luna",choices=sorted(MODEL_CONFIG));ap.add_argument("--provider");ap.add_argument("--concurrency",type=int,default=20);ap.add_argument("--max-retries",type=int,default=3);ap.add_argument("--limit",type=int);ap.add_argument("--condition",choices=["thin","rich"]);ap.add_argument("--dry-run",action="store_true");ap.add_argument("--mock",action="store_true");args=ap.parse_args();rows=load_jsonl(args.requests)
    if args.condition:rows=[r for r in rows if r["condition"]==args.condition]
    if args.limit is not None:rows=rows[:args.limit]
    validate_request_rows(rows);schema=json.loads(Path(args.schema).read_text(encoding="utf-8"));print(json.dumps(estimate_cost(rows,args.model),indent=2))
    if args.dry_run:return
    if args.mock:
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("w",encoding="utf-8") as f:
            for r in rows:f.write(json.dumps({"anon_id":r["anon_id"],"condition":r["condition"],"model_requested":"mock","response":validate_payload(deterministic_mock(r))})+"\n")
        return
    provider=args.provider if args.provider is not None else MODEL_CONFIG[args.model]["provider"];run_live(rows,schema,Path(args.out),args.model,provider,args.concurrency,args.max_retries)
if __name__=="__main__":main()
