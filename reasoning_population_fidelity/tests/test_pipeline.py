from __future__ import annotations
import csv, json, sys, tempfile, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
SRC=HERE/"src"
sys.path.insert(0,str(SRC))
from core import deterministic_mock, validate_persona, validate_response
from pipeline import fixture_personas, expand, load_config

def test_persona_leakage_guard():
    validate_persona("A 40-year-old man living in rural Bihar, India, in a household of five people.")
    try: validate_persona("A 40-year-old smartphone user living in Bihar.")
    except AssertionError: pass
    else: raise AssertionError("Leakage guard failed")

def test_response_schema_guard():
    good=deterministic_mock({"anon_id":"x","reasoning":"off"}); validate_response(good)
    bad=dict(good); bad["mobile_ability"]={"answer":"maybe","probability_yes":0.5}
    try: validate_response(bad)
    except ValueError: pass
    else: raise AssertionError("Response validator accepted invalid answer")

def test_identical_prompt_across_reasoning():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); base=td/"base.jsonl"; exp=td/"expanded.jsonl"; rows=fixture_personas(); base.write_text("".join(json.dumps(r)+"\n" for r in rows)); expand(base,exp); expanded=[json.loads(x) for x in exp.read_text().splitlines()]; cfg=load_config()
        for anon in {r["anon_id"] for r in expanded}:
            group=[r for r in expanded if r["anon_id"]==anon]
            assert len({r["prompt"] for r in group})==1
            assert {r["reasoning"] for r in group}=={"off","low","medium"}
            assert all(r["generation_settings"]==cfg["study_1"]["generation_settings"] for r in group)
            assert len({json.dumps(r["generation_settings"],sort_keys=True) for r in group})==1
            off=[r for r in group if r["reasoning"]=="off"][0]
            low=[r for r in group if r["reasoning"]=="low"][0]
            medium=[r for r in group if r["reasoning"]=="medium"][0]
            assert off["reasoning_settings"]=={"enabled":False,"max_completion_tokens":250}
            assert low["reasoning_settings"]=={"effort":"low","max_completion_tokens":900}
            assert medium["reasoning_settings"]=={"effort":"medium","max_completion_tokens":1500}

def make_tiny_cams_zip(path):
    hh_fields=["ST","NSS","DIST","STRM","SSTRM","SR","SRO","FC","FSU","SSS","SSU","BL41I1","BL41I2","BL41I3","BL41I4","BL6I6"]
    mem_fields=["ST","NSS","DIST","STRM","SSTRM","SR","SRO","FC","FSU","SSS","SSU","SRL","SEC","BL31C3","BL31C4","BL31C5","BL31C6","BL31C7","BL31C8","BL32C3","BL32C4","BL32C6","BL32C7","BL32C8","BL33C3","MULT"]
    households=[]; members=[]; i=0; ages=[19,29,39,49,66]
    for sec in [1,2]:
      for gender in [1,2]:
       for age in ages:
        for rep in range(4):
          i+=1; key={"ST":10 if sec==1 else 7,"NSS":1,"DIST":1,"STRM":1,"SSTRM":1,"SR":1,"SRO":1,"FC":1,"FSU":i,"SSS":1,"SSU":1}
          households.append({**key,"BL41I1":4,"BL41I2":1 if rep%2==0 else 2,"BL41I3":3,"BL41I4":4,"BL6I6":12000+100*i})
          members.append({**key,"SRL":1,"SEC":sec,"BL31C3":1,"BL31C4":gender,"BL31C5":age,"BL31C6":2,"BL31C7":2,"BL31C8":1,"BL32C3":1 if (age<60 or sec==2) else 3,"BL32C4":1 if age<60 else 4,"BL32C6":1 if age<50 and sec==2 else 2,"BL32C7":1 if age<60 else 4,"BL32C8":1 if age<50 else 2,"BL33C3":1 if age<40 and sec==2 else 2,"MULT":100+rep})
    with tempfile.TemporaryDirectory() as td:
      td=Path(td); d=td/"CSV_CAMS_79"; d.mkdir()
      for name,fields,rows in [("NSS79CAMS_Household.csv",hh_fields,households),("NSS79CAMS_Member.csv",mem_fields,members)]:
        with (d/name).open("w",newline="",encoding="utf-8") as f:
          w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
      with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for f in d.iterdir(): z.write(f,arcname=f"CSV_CAMS_79/{f.name}")

def test_real_column_parser_and_sampling():
    import prepare_cams
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); z=td/"cams.zip"; out=td/"out"; make_tiny_cams_zip(z); manifest=prepare_cams.prepare(z,out,n=40,seed=123); assert manifest["n"]==40
        base=[json.loads(x) for x in (out/"requests_base.jsonl").read_text().splitlines()]; assert len(base)==40; assert len({x["anon_id"] for x in base})==40
        for x in base: validate_persona(x["persona"])

def test_live_is_locked():
    from pipeline import live_guard
    try: live_guard()
    except RuntimeError: pass
    else: raise AssertionError("Paid guard unexpectedly open")

def run_all():
    tests=[v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]; results=[]
    for fn in tests: fn(); results.append({"test":fn.__name__,"status":"PASS"})
    return results
if __name__=="__main__": print(json.dumps(run_all(),indent=2))
