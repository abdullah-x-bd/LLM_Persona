from __future__ import annotations

import json
import os
import urllib.request

BASE="https://openrouter.ai/api/v1"
REQUIRED={"reasoning","response_format","max_tokens"}
PROVIDER="akashml"
MAX_GENERIC_OUTPUT_PER_M=5.0
MAX_CANDIDATES_TO_PROBE=60


def get_json(url: str, key: str) -> dict:
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {key}","User-Agent":"LLM-Persona-SecondModel-Scanner/1.1"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def per_m(v):
    return None if v is None else float(v)*1_000_000


def main():
    key=os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("OPENROUTER_API_KEY missing")
    models=get_json(f"{BASE}/models",key).get("data",[])
    pool=[]
    for m in models:
        mid=m.get("id")
        if not mid or mid.startswith("qwen/"): continue
        params=set(m.get("supported_parameters") or [])
        if not REQUIRED.issubset(params): continue
        reasoning=m.get("reasoning") or {}
        if reasoning.get("mandatory"): continue
        efforts=list(reasoning.get("supported_efforts") or [])
        if not efforts: continue
        usable=[x for x in ("low","medium","high") if x in efforts]
        if not usable: continue
        pricing=m.get("pricing") or {}
        pin=per_m(pricing.get("prompt")); pout=per_m(pricing.get("completion"))
        if pin is None or pout is None or pout>MAX_GENERIC_OUTPUT_PER_M: continue
        pool.append({"model":mid,"generic_input_per_m":pin,"generic_output_per_m":pout,"reasoning":reasoning,"usable_efforts":usable})
    pool.sort(key=lambda x:(x["generic_output_per_m"],x["generic_input_per_m"],x["model"]))
    results=[]
    for c in pool[:MAX_CANDIDATES_TO_PROBE]:
        author,slug=c["model"].split("/",1)
        try:
            eps=(get_json(f"{BASE}/models/{author}/{slug}/endpoints",key).get("data",{}) or {}).get("endpoints") or []
        except Exception:
            continue
        for ep in eps:
            name=str(ep.get("name") or ep.get("provider_name") or ""); tag=str(ep.get("tag") or "")
            if PROVIDER not in name.lower() and PROVIDER not in tag.lower(): continue
            params=set(ep.get("supported_parameters") or [])
            if not REQUIRED.issubset(params): continue
            status=ep.get("status")
            healthy=not (isinstance(status,(int,float)) and status<0)
            pricing=ep.get("pricing") or {}; pin=per_m(pricing.get("prompt")); pout=per_m(pricing.get("completion"))
            if pin is None or pout is None: continue
            results.append({**c,"endpoint_name":name,"endpoint_tag":tag,"endpoint_status":status,"endpoint_healthy":healthy,"endpoint_input_per_m":pin,"endpoint_output_per_m":pout})
    results.sort(key=lambda x:(not x["endpoint_healthy"],x["endpoint_output_per_m"],x["endpoint_input_per_m"],x["model"]))
    report={"paid_inference_performed":False,"chat_completions_called":False,"provider":"AkashML","candidate_count":len(results),"healthy_candidate_count":sum(1 for x in results if x["endpoint_healthy"]),"top_candidates":results[:25]}
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
