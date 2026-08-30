from __future__ import annotations
import argparse, json, os, time
from collections import defaultdict
from pathlib import Path
from core import (
    ALLOWED_REASONING, approx_tokens, build_prompt, deterministic_mock, load_jsonl,
    request_id, sha256_text, validate_persona, validate_response, write_jsonl
)

HERE=Path(__file__).resolve().parents[1]
DEFAULT_CONFIG=HERE/"config"/"preflight.json"
DEFAULT_SCHEMA=HERE/"prompts"/"response_schema.json"

def load_config(path=DEFAULT_CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def fixture_personas():
    rows=[
      ("DRY-001","A 19-year-old woman living in rural Bihar, India. She is an unmarried child of the household head, currently enrolled in formal education, lives in a household of 6 people, the household religion is Hindu, the social group is Other Backward Class, the main household language is Hindi, and household consumption is in the second fifth of the national distribution."),
      ("DRY-002","A 46-year-old man living in urban Delhi, India. He is the household head, currently married, engaged in economic activity during the last seven days, lives in a household of 4 people, the household religion is Muslim, the social group is other, the main household language is Urdu, and household consumption is in the fourth fifth of the national distribution."),
      ("DRY-003","A 67-year-old woman living in rural Kerala, India. She is a parent of the household head, widowed, not currently enrolled in formal education, not engaged in economic activity during the last seven days, lives in a household of 5 people, the household religion is Christian, the social group is other, the main household language is Malayalam, and household consumption is in the middle fifth of the national distribution."),
      ("DRY-004","A 31-year-old man living in urban Karnataka, India. He is the household head, currently married, previously enrolled in formal education, engaged in economic activity during the last seven days, lives in a household of 3 people, the household religion is Hindu, the social group is Scheduled Caste, the main household language is Kannada, and household consumption is in the highest fifth of the national distribution."),
      ("DRY-005","A 23-year-old woman living in urban West Bengal, India. She is an unmarried child of the household head, currently enrolled in formal education, not engaged in economic activity during the last seven days, lives in a household of 4 people, the household religion is Hindu, the social group is other, the main household language is Bengali, and household consumption is in the middle fifth of the national distribution."),
      ("DRY-006","A 54-year-old man living in rural Rajasthan, India. He is the household head, currently married, previously enrolled in formal education, engaged in economic activity during the last seven days, lives in a household of 7 people, the household religion is Hindu, the social group is Other Backward Class, the main household language is Hindi, and household consumption is in the lowest fifth of the national distribution.")
    ]
    out=[]
    for anon,persona in rows:
        validate_persona(persona)
        out.append({"anon_id":anon,"persona":persona,"prompt":build_prompt(persona)})
    return out

def make_fixture(out_path):
    rows=fixture_personas(); write_jsonl(out_path,rows)
    return {"base_requests":len(rows),"path":str(out_path)}

def expand(base_path,out_path,config_path=DEFAULT_CONFIG,schema_path=DEFAULT_SCHEMA):
    cfg=load_config(config_path); base=load_jsonl(base_path)
    schema_hash=sha256_text(Path(schema_path).read_text(encoding="utf-8"))
    model=cfg["primary_model"]["id"]; conditions=cfg["study_1"]["reasoning_conditions"]; rows=[]
    for b in base:
        validate_persona(b["persona"])
        if b["prompt"] != build_prompt(b["persona"]):
            raise AssertionError(f"Prompt/persona mismatch for {b['anon_id']}")
        for condition,settings in conditions.items():
            if condition not in ALLOWED_REASONING: raise AssertionError(f"Unknown reasoning condition: {condition}")
            row={"anon_id":b["anon_id"],"reasoning":condition,"reasoning_settings":settings,"persona":b["persona"],"prompt":b["prompt"],"prompt_sha256":sha256_text(b["prompt"]),"schema_sha256":schema_hash,"model":model}
            row["request_id"]=request_id(row); rows.append(row)
    rows.sort(key=lambda r:(r["anon_id"],r["reasoning"])); write_jsonl(out_path,rows)
    return {"expanded_requests":len(rows),"respondents":len(base),"path":str(out_path)}

def estimate_full_cost(rows,cfg):
    pm=cfg["primary_model"]; total_in=sum(approx_tokens(r["prompt"]) for r in rows)
    total_out=sum(int(r["reasoning_settings"]["max_completion_tokens"]) for r in rows)
    return {"request_count":len(rows),"conservative_input_tokens":total_in,"hard_capped_completion_tokens":total_out,"worst_case_cost_usd":round(total_in/1e6*pm["input_usd_per_million"]+total_out/1e6*pm["output_usd_per_million"],6)}

def validate_expanded(rows,cfg):
    errors=[]; seen=set(); by_person=defaultdict(list); schema_expected=sha256_text(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    for r in rows:
        pair=(r.get("anon_id"),r.get("reasoning"))
        if pair in seen: errors.append(f"duplicate pair {pair}")
        seen.add(pair); by_person[r.get("anon_id")].append(r)
        try: validate_persona(r["persona"])
        except Exception as e: errors.append(f"{r.get('anon_id')} persona: {e}")
        if r.get("reasoning") not in ALLOWED_REASONING: errors.append(f"bad reasoning {pair}")
        if r.get("prompt_sha256") != sha256_text(r.get("prompt","")): errors.append(f"prompt hash mismatch {pair}")
        if r.get("schema_sha256") != schema_expected: errors.append(f"schema hash mismatch {pair}")
        if r.get("request_id") != request_id(r): errors.append(f"request id mismatch {pair}")
        if r.get("model") != cfg["primary_model"]["id"]: errors.append(f"model mismatch {pair}")
    expected=set(cfg["study_1"]["reasoning_conditions"])
    for anon,grp in by_person.items():
        if {g["reasoning"] for g in grp} != expected: errors.append(f"{anon}: incomplete condition set")
        if len({g["prompt_sha256"] for g in grp})!=1 or len({g["prompt"] for g in grp})!=1: errors.append(f"{anon}: prompt changed across reasoning conditions")
    return errors

def mock_run(requests_path,out_path):
    rows=load_jsonl(requests_path); out=[]
    for r in rows:
        payload=deterministic_mock(r); validate_response(payload)
        out.append({"request_id":r["request_id"],"anon_id":r["anon_id"],"reasoning":r["reasoning"],"model_requested":"deterministic/mock","response":payload,"usage":{"prompt_tokens":approx_tokens(r["prompt"]),"completion_tokens":120,"cost_usd":0.0}})
    write_jsonl(out_path,out); return {"mock_responses":len(out),"parse_errors":0,"cost_usd":0.0,"path":str(out_path)}

def preflight(requests_path,report_path,config_path=DEFAULT_CONFIG):
    cfg=load_config(config_path); rows=load_jsonl(requests_path); checks=[]
    def add(name,ok,detail): checks.append({"check":name,"status":"PASS" if ok else "FAIL","detail":detail})
    add("paid_disabled",cfg["paid_runs_enabled"] is False,f"paid_runs_enabled={cfg['paid_runs_enabled']}")
    add("budget_identity",abs(cfg["budget_usd"]-(cfg["hard_spend_cap_usd"]+cfg["reserve_usd"]))<1e-9,f"budget={cfg['budget_usd']}, cap={cfg['hard_spend_cap_usd']}, reserve={cfg['reserve_usd']}")
    errors=validate_expanded(rows,cfg); add("request_integrity",not errors,"no integrity errors" if not errors else "; ".join(errors[:8]))
    mock=[deterministic_mock(r) for r in rows[:min(10,len(rows))]]
    try:
        for m in mock: validate_response(m)
        parser_ok=True; parser_detail=f"{len(mock)} mock payloads validated"
    except Exception as e: parser_ok=False; parser_detail=repr(e)
    add("schema_parser",parser_ok,parser_detail); cost=estimate_full_cost(rows,cfg)
    add("cost_estimator",cost["worst_case_cost_usd"]>=0,json.dumps(cost,sort_keys=True))
    report={"generated_at_unix":time.time(),"config_sha256":sha256_text(Path(config_path).read_text(encoding="utf-8")),"requests_sha256":sha256_text(Path(requests_path).read_text(encoding="utf-8")),"checks":checks,"cost_projection":cost,"all_passed":all(x["status"]=="PASS" for x in checks),"paid_inference_performed":False}
    Path(report_path).parent.mkdir(parents=True,exist_ok=True); Path(report_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    if not report["all_passed"]: raise SystemExit(2)
    return report

def live_guard(config_path=DEFAULT_CONFIG):
    cfg=load_config(config_path)
    if not cfg["paid_runs_enabled"]: raise RuntimeError("Paid inference is locked by config. This is intentional.")
    if os.getenv("RPF_ENABLE_PAID") != "YES_I_ACCEPT_COST": raise RuntimeError("Paid inference also requires RPF_ENABLE_PAID=YES_I_ACCEPT_COST.")
    return True

def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("fixture"); p.add_argument("--out",required=True)
    p=sp.add_parser("expand"); p.add_argument("--base",required=True); p.add_argument("--out",required=True)
    p=sp.add_parser("mock"); p.add_argument("--requests",required=True); p.add_argument("--out",required=True)
    p=sp.add_parser("preflight"); p.add_argument("--requests",required=True); p.add_argument("--report",required=True)
    sp.add_parser("assert-live-locked"); args=ap.parse_args()
    if args.cmd=="fixture": result=make_fixture(Path(args.out))
    elif args.cmd=="expand": result=expand(args.base,args.out)
    elif args.cmd=="mock": result=mock_run(args.requests,args.out)
    elif args.cmd=="preflight": result=preflight(args.requests,args.report)
    elif args.cmd=="assert-live-locked":
        try: live_guard()
        except RuntimeError as e: result={"locked":True,"reason":str(e)}
        else: raise SystemExit("FAIL: live guard unexpectedly open")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
