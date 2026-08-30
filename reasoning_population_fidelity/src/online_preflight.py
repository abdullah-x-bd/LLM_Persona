from __future__ import annotations
import json, os, sys, urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
CONFIG=HERE/"config"/"preflight.json"
BASE="https://openrouter.ai/api/v1"
REQUIRED_PARAMS={"reasoning","response_format","temperature","top_p","max_tokens"}
REQUIRED_ENABLED_EFFORTS={"low","medium"}

def get_json(url,key):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {key}","User-Agent":"LLM-Persona-RPF-ZeroCost-Preflight/1.6"})
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
    print(json.dumps({k:key_info.get(k) for k in ("is_free_tier","limit","limit_remaining","usage","usage_daily","expires_at")},indent=2))
    models=get_json(f"{BASE}/models",key).get("data",[]); by_id={m.get("id"):m for m in models}; model_id=cfg["primary_model"]["id"]
    if model_id not in by_id:
        print(f"FAIL: primary model not listed: {model_id}",file=sys.stderr); return 1
    m=by_id[model_id]; params=set(m.get("supported_parameters") or []); missing=REQUIRED_PARAMS-params
    if missing:
        print(f"FAIL: primary model missing frozen parameters: {sorted(missing)}",file=sys.stderr); return 1
    reasoning_meta=m.get("reasoning") or {}; supported_efforts=reasoning_meta.get("supported_efforts"); mandatory=bool(reasoning_meta.get("mandatory",False))
    if mandatory:
        print("FAIL: model metadata says reasoning is mandatory, so thinking-off treatment is invalid",file=sys.stderr); return 1
    if supported_efforts is not None and not REQUIRED_ENABLED_EFFORTS.issubset(set(supported_efforts)):
        print(f"FAIL: model-specific efforts do not contain low/medium: {supported_efforts}",file=sys.stderr); return 1
    arms=cfg["study_1"]["reasoning_conditions"]
    if set(arms)!={"off","low","medium"} or arms["off"].get("enabled") is not False or arms["low"].get("effort")!="low" or arms["medium"].get("effort")!="medium":
        print("FAIL: frozen config does not encode off/low/medium as expected",file=sys.stderr); return 1
    pricing=m.get("pricing") or {}; live_in=as_per_million(pricing.get("prompt")); live_out=as_per_million(pricing.get("completion")); configured=cfg["primary_model"]; mult=float(configured["max_price_multiplier_before_block"])
    if live_in is None or live_out is None:
        print("FAIL: model pricing unavailable",file=sys.stderr); return 1
    if live_in > configured["input_usd_per_million"]*mult or live_out > configured["output_usd_per_million"]*mult:
        print(f"FAIL: routed-model price exceeds guard. input={live_in}, output={live_out}",file=sys.stderr); return 1
    author,slug=model_id.split("/",1); endpoint_data=get_json(f"{BASE}/models/{author}/{slug}/endpoints",key).get("data",{}); endpoints=endpoint_data.get("endpoints") or []
    policy=cfg["run_policy"]; ceiling=policy["provider_max_price_usd_per_million"]; eligible=[]
    for ep in endpoints:
        ep_params=set(ep.get("supported_parameters") or []); ep_pricing=ep.get("pricing") or {}; pin=as_per_million(ep_pricing.get("prompt")); pout=as_per_million(ep_pricing.get("completion"))
        if not REQUIRED_PARAMS.issubset(ep_params): continue
        if pin is None or pout is None: continue
        if pin<=float(ceiling["prompt"]) and pout<=float(ceiling["completion"]):
            eligible.append({"tag":ep.get("tag"),"name":ep.get("name") or ep.get("provider_name"),"input_per_m":pin,"output_per_m":pout,"status":ep.get("status")})
    if not eligible:
        print("FAIL: no endpoint satisfies all frozen parameters plus hard price ceiling",file=sys.stderr); return 1
    provider_order=list(policy.get("provider_order") or [])
    if provider_order:
        eligible_tags={e.get("tag") for e in eligible}
        missing_pins=[p for p in provider_order if p not in eligible_tags]
        if missing_pins:
            print(f"FAIL: pinned provider is not currently eligible: {missing_pins}",file=sys.stderr); return 1
        pinned=[e for e in eligible if e.get("tag") in provider_order]
        unhealthy=[e for e in pinned if isinstance(e.get("status"),(int,float)) and e.get("status") < 0]
        if unhealthy:
            print(f"FAIL: pinned provider reports unhealthy status: {unhealthy}",file=sys.stderr); return 1
        if bool(policy.get("allow_provider_fallbacks")):
            print("FAIL: pinned Study 1 provider requires allow_provider_fallbacks=false",file=sys.stderr); return 1
    frozen=cfg["study_1"]["generation_settings"]
    print(json.dumps({"status":"PASS","model":model_id,"required_parameters":sorted(REQUIRED_PARAMS),"model_reasoning_metadata":{"supported_efforts":supported_efforts,"default_effort":reasoning_meta.get("default_effort"),"default_enabled":reasoning_meta.get("default_enabled"),"supports_max_tokens":reasoning_meta.get("supports_max_tokens"),"mandatory":mandatory},"treatment_arms":{"off":{"enabled":False},"low":{"effort":"low"},"medium":{"effort":"medium"}},"generation_settings":frozen,"live_routed_input_usd_per_million":live_in,"live_routed_output_usd_per_million":live_out,"hard_provider_price_ceiling":ceiling,"provider_order":provider_order,"allow_provider_fallbacks":bool(policy.get("allow_provider_fallbacks")),"eligible_endpoint_count":len(eligible),"eligible_endpoints":eligible[:8],"pinned_endpoints":[e for e in eligible if e.get("tag") in provider_order],"inference_endpoint_called":False},indent=2))
    print("PASS: zero-cost online preflight complete; no inference endpoint called"); return 0
if __name__=="__main__": raise SystemExit(main())
