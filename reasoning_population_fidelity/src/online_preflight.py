from __future__ import annotations
import json, os, sys, urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
CONFIG=HERE/"config"/"preflight.json"
BASE="https://openrouter.ai/api/v1"

def get_json(url,key):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {key}","User-Agent":"LLM-Persona-RPF-ZeroCost-Preflight/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode("utf-8"))

def as_per_million(value):
    if value is None: return None
    return float(value)*1_000_000

def main():
    key=os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("FAIL: OPENROUTER_API_KEY missing",file=sys.stderr); return 2
    cfg=json.loads(CONFIG.read_text(encoding="utf-8")); key_info=get_json(f"{BASE}/key",key).get("data",{})
    print("PASS: OpenRouter key authenticated")
    print(json.dumps({k:key_info.get(k) for k in ("label","is_free_tier","limit","limit_remaining","expires_at")},indent=2))
    models=get_json(f"{BASE}/models",key).get("data",[]); by_id={m.get("id"):m for m in models}; model_id=cfg["primary_model"]["id"]
    if model_id not in by_id:
        print(f"FAIL: primary model not listed: {model_id}",file=sys.stderr); return 1
    m=by_id[model_id]; params=set(m.get("supported_parameters") or []); missing={"reasoning","response_format"}-params
    if missing:
        print(f"FAIL: primary model missing parameters: {sorted(missing)}",file=sys.stderr); return 1
    pricing=m.get("pricing") or {}; live_in=as_per_million(pricing.get("prompt")); live_out=as_per_million(pricing.get("completion")); configured=cfg["primary_model"]; mult=float(configured["max_price_multiplier_before_block"])
    if live_in is None or live_out is None:
        print("FAIL: model pricing unavailable",file=sys.stderr); return 1
    if live_in > configured["input_usd_per_million"]*mult or live_out > configured["output_usd_per_million"]*mult:
        print(f"FAIL: live price exceeds guard. input={live_in}, output={live_out}",file=sys.stderr); return 1
    print(json.dumps({"status":"PASS","model":model_id,"supports_reasoning":True,"supports_response_format":True,"live_input_usd_per_million":live_in,"live_output_usd_per_million":live_out,"configured_price_guard_multiplier":mult,"inference_endpoint_called":False},indent=2))
    print("PASS: zero-cost online preflight complete; no inference endpoint called"); return 0
if __name__=="__main__": raise SystemExit(main())
