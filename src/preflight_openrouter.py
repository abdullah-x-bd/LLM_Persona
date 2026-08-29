from __future__ import annotations
import json,os,sys,urllib.request
MODELS={"openai/gpt-5.6-luna":"openai","google/gemini-3.7-flash":"google-vertex","anthropic/claude-sonnet-5":"anthropic"};BASE="https://openrouter.ai/api/v1"
def get_json(url,key):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {key}","User-Agent":"LLM-Persona-Preflight/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
def main():
    key=os.getenv("OPENROUTER_API_KEY")
    if not key:print("FAIL: OPENROUTER_API_KEY is missing",file=sys.stderr);return 2
    info=get_json(f"{BASE}/key",key).get("data",{});print("PASS: API key authenticated");print(json.dumps({k:info.get(k) for k in ["label","is_free_tier","limit","limit_remaining","expires_at"]},indent=2));models=get_json(f"{BASE}/models",key).get("data",[]);by_id={m.get("id"):m for m in models};failed=False
    for model,provider in MODELS.items():
        if model not in by_id:print(f"FAIL: model not listed: {model}");failed=True;continue
        params=set(by_id[model].get("supported_parameters") or []);structured=("response_format" in params) or ("structured_outputs" in params);print(f"PASS: model listed: {model}; structured_outputs={structured}");failed|=not structured;author,slug=model.split("/",1);eps=get_json(f"{BASE}/models/{author}/{slug}/endpoints",key).get("data",{}).get("endpoints",[]);matches=[]
        for ep in eps:
            tag=(ep.get("tag") or "").lower();name=(ep.get("name") or ep.get("provider_name") or "").lower()
            if tag==provider or tag.startswith(provider+"/") or provider.replace("-"," ") in name:
                ep_params=set(ep.get("supported_parameters") or []);matches.append({"tag":ep.get("tag"),"name":ep.get("name") or ep.get("provider_name"),"structured":("response_format" in ep_params) or ("structured_outputs" in ep_params),"status":ep.get("status")})
        if not matches:print(f"WARN: pinned provider endpoint not identified for {model}: {provider}")
        else:
            print(f"PASS: provider endpoint candidates for {model}: {json.dumps(matches)}")
            if not any(x["structured"] for x in matches):print(f"FAIL: no pinned endpoint advertises structured output for {model}");failed=True
    if failed:return 1
    print("PASS: no-cost preflight complete; no inference endpoint was called");return 0
if __name__=="__main__":raise SystemExit(main())
