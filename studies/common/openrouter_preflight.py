from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_core import load_registry, static_report, projection_report

BASE = "https://openrouter.ai/api/v1"
REQUIRED = {"response_format", "max_tokens"}


def get_json(url: str, key: str) -> dict:
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {key}","User-Agent":"LLM-Persona-Followup-ZeroCost/1.3"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def per_m(v): return None if v is None else float(v)*1_000_000


def choose_endpoint(model_id: str, key: str, provider_name: str) -> dict:
    author,slug=model_id.split("/",1)
    data=get_json(f"{BASE}/models/{author}/{slug}/endpoints",key).get("data",{})
    matches=[]
    for ep in data.get("endpoints") or []:
        name=str(ep.get("name") or ep.get("provider_name") or ""); tag=str(ep.get("tag") or "")
        if provider_name.lower() not in name.lower() and provider_name.lower() not in tag.lower(): continue
        pin=per_m((ep.get("pricing") or {}).get("prompt")); pout=per_m((ep.get("pricing") or {}).get("completion"))
        if pin is None or pout is None: continue
        matches.append({"name":name,"tag":tag,"input_per_m":pin,"output_per_m":pout,"supported_parameters":sorted(set(ep.get("supported_parameters") or [])),"status":ep.get("status")})
    if not matches: raise RuntimeError(f"No {provider_name} endpoint found for {model_id}")
    # Prefer healthy endpoints first, then price. A negative numeric status is treated as unhealthy.
    def health_rank(x):
        s=x.get("status")
        unhealthy=isinstance(s,(int,float)) and s<0
        return (1 if unhealthy else 0,x["output_per_m"],x["input_per_m"],x["tag"])
    matches.sort(key=health_rank)
    return matches[0]


def endpoint_healthy(ep: dict) -> bool:
    s=ep.get("status")
    return not (isinstance(s,(int,float)) and s<0)


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("study_id"); ap.add_argument("--out"); ap.add_argument("--allow-projection",action="store_true"); a=ap.parse_args()
    reg=load_registry(); study=reg["studies"][a.study_id]
    static=static_report(a.study_id)
    projection=False
    if static["status"]=="BLOCKED_DATA" and a.allow_projection:
        static=projection_report(a.study_id); projection=True
    elif static["status"]=="BLOCKED_DATA":
        print(json.dumps(static,indent=2,sort_keys=True)); return 3
    elif static["status"]!="PASS_STATIC":
        print(json.dumps(static,indent=2,sort_keys=True)); return 2

    key=os.getenv("OPENROUTER_API_KEY")
    if not key: print("OPENROUTER_API_KEY missing",file=sys.stderr); return 2
    key_info=get_json(f"{BASE}/key",key).get("data",{})
    models=get_json(f"{BASE}/models",key).get("data",[]); by_id={m.get("id"):m for m in models}
    provider_name=reg["privacy"]["provider_name"]; live_models={}; live_total=0.0; endpoint_health_ok=True
    for mk in sorted({arm["model"] for arm in study["arms"]}):
        mid=reg["models"][mk]["id"]
        if mid not in by_id: raise RuntimeError(f"Model no longer listed: {mid}")
        m=by_id[mid]; params=set(m.get("supported_parameters") or []); missing=REQUIRED-params
        if missing: raise RuntimeError(f"{mid} missing required parameters: {sorted(missing)}")
        arms=[arm for arm in study["arms"] if arm["model"]==mk]; off_present=any(x["reasoning"]=="off" for x in arms); enabled={x["reasoning"] for x in arms if x["reasoning"]!="off"}; reasoning_meta=m.get("reasoning") or {}
        if enabled:
            if "reasoning" not in params: raise RuntimeError(f"{mid} does not advertise reasoning")
            if off_present and reasoning_meta.get("mandatory"): raise RuntimeError(f"{mid} metadata says reasoning mandatory, invalidating off arm")
            supported=reasoning_meta.get("supported_efforts")
            if supported is not None and enabled-set(supported): raise RuntimeError(f"{mid} does not advertise frozen efforts {sorted(enabled-set(supported))}; supported={supported}")
        ep=choose_endpoint(mid,key,provider_name); ep_params=set(ep["supported_parameters"])
        if not REQUIRED.issubset(ep_params): raise RuntimeError(f"Pinned endpoint {ep['tag']} lacks structured output/max_tokens")
        if enabled and "reasoning" not in ep_params: raise RuntimeError(f"Pinned endpoint {ep['tag']} lacks reasoning")
        healthy=endpoint_healthy(ep); endpoint_health_ok = endpoint_health_ok and healthy
        svals=static["models"][mk]; cost=svals["approx_input_tokens"]/1e6*ep["input_per_m"]+svals["hard_completion_tokens"]/1e6*ep["output_per_m"]; live_total+=cost
        live_models[mk]={"model":mid,"reasoning_metadata":reasoning_meta,"frozen_enabled_efforts":sorted(enabled),"endpoint":ep,"endpoint_healthy":healthy,"hard_single_pass_ceiling_usd":round(cost,6)}

    cap=float(study["study_spend_cap_usd"]); remaining=key_info.get("limit_remaining")
    report={"study_id":a.study_id,"status":"PASS_LIVE_PROJECTION" if projection else "PASS_LIVE","projection_only":projection,"launch_ready":not projection and endpoint_health_ok,"paid_inference_performed":False,"chat_completions_called":False,"provider_name":provider_name,"allow_fallbacks":False,"data_collection":"deny","endpoint_health_ok":endpoint_health_ok,"models":live_models,"hard_single_pass_live_ceiling_usd":round(live_total,6),"study_spend_cap_usd":cap,"openrouter_key":{"is_free_tier":key_info.get("is_free_tier"),"limit":key_info.get("limit"),"limit_remaining":remaining,"usage":key_info.get("usage")},"static":static}
    if not endpoint_health_ok:
        report["status"]="BLOCKED_ENDPOINT_HEALTH_PROJECTION" if projection else "BLOCKED_ENDPOINT_HEALTH"
    elif live_total>cap+1e-9:
        report["status"]="BLOCKED_LIVE_PRICE_PROJECTION" if projection else "BLOCKED_LIVE_PRICE"
    elif not projection and remaining is not None and float(remaining)<min(live_total,cap):
        report["status"]="BLOCKED_BALANCE"
    if a.out: Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if report["status"] in {"PASS_LIVE","PASS_LIVE_PROJECTION"} else 4

if __name__=="__main__": raise SystemExit(main())
