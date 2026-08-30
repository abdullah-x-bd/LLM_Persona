from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from core import build_prompt, validate_persona, write_jsonl

HOUSEHOLD_KEY=["ST","NSS","DIST","STRM","SSTRM","SR","SRO","FC","FSU","SSS","SSU"]
PERSON_KEY=HOUSEHOLD_KEY+["SRL"]
STATE_MAP={1:"Jammu and Kashmir",2:"Himachal Pradesh",3:"Punjab",4:"Chandigarh",5:"Uttarakhand",6:"Haryana",7:"Delhi",8:"Rajasthan",9:"Uttar Pradesh",10:"Bihar",11:"Sikkim",12:"Arunachal Pradesh",13:"Nagaland",14:"Manipur",15:"Mizoram",16:"Tripura",17:"Meghalaya",18:"Assam",19:"West Bengal",20:"Jharkhand",21:"Odisha",22:"Chhattisgarh",23:"Madhya Pradesh",24:"Gujarat",25:"Dadra and Nagar Haveli and Daman and Diu",27:"Maharashtra",28:"Andhra Pradesh",29:"Karnataka",30:"Goa",31:"Lakshadweep",32:"Kerala",33:"Tamil Nadu",34:"Puducherry",35:"Andaman and Nicobar Islands",36:"Telangana",37:"Ladakh"}
GENDER_MAP={1:"man",2:"woman"}; SECTOR_MAP={1:"rural",2:"urban"}
RELATION_MAP={1:"head of the household",2:"spouse of the household head",3:"married child of the household head",4:"spouse of a married child of the household head",5:"unmarried child of the household head",6:"grandchild of the household head",7:"parent or parent-in-law of the household head",8:"sibling, sibling-in-law, or other relative of the household head",9:"non-relative member of the household"}
MARITAL_MAP={1:"never married",2:"currently married or living with a partner",3:"widowed",4:"divorced or separated"}
ENROLMENT_MAP={1:"currently enrolled in formal education or training",2:"previously enrolled in formal education or training but not currently enrolled",3:"never enrolled in formal education or training"}
ECON_MAP={1:"engaged in economic activity for at least one hour during the last seven days",2:"not engaged in economic activity during the last seven days"}
RELIGION_MAP={1:"Hindu",2:"Muslim",3:"Christian",4:"Sikh",5:"Jain",6:"Buddhist",7:"Zoroastrian",9:"another religion"}
SOCIAL_MAP={1:"Scheduled Tribe",2:"Scheduled Caste",3:"Other Backward Class",9:"other social group"}
LANGUAGE_MAP={1:"Assamese",2:"Bengali",3:"Gujarati",4:"Hindi",5:"Kannada",6:"Kashmiri",7:"Konkani",8:"Malayalam",9:"Manipuri",10:"Marathi",11:"Nepali",12:"Odia",13:"Punjabi",14:"Sanskrit",15:"Sindhi",16:"Tamil",17:"Telugu",18:"Urdu",19:"English",20:"Bodo",22:"Dogri",23:"Khasi",24:"Garo",25:"Mizo",26:"Bhutia",27:"Lepcha",28:"Limboo",29:"French",39:"Santhali",51:"Maithili",99:"another language"}
OUTCOME_COLS={"mobile_ability":"BL32C3","mobile_3m":"BL32C4","computer_ability":"BL32C6","internet_ability":"BL32C7","internet_3m":"BL32C8","copy_paste":"BL33C3"}

def age_group(age):
    if age<=24:return "15-24"
    if age<=34:return "25-34"
    if age<=44:return "35-44"
    if age<=59:return "45-59"
    return "60+"

def weighted_quantiles(values,weights,qs=(.2,.4,.6,.8)):
    order=np.argsort(values); v=values[order]; w=weights[order]; c=(np.cumsum(w)-.5*w)/w.sum(); return np.interp(qs,c,v)

def allocate_proportional(strata,n):
    raw=strata["W"]/strata["W"].sum()*n; base=np.floor(raw).astype(int); rem=int(n-base.sum()); order=np.argsort(-(raw-base).to_numpy(),kind="stable"); alloc=base.copy()
    for i in order[:rem]: alloc.iloc[i]+=1
    return alloc

def pps_systematic(g,n,rng):
    if n==0:return g.iloc[0:0].copy()
    if n>len(g): raise ValueError("Requested more units than stratum contains")
    g=g.sort_values(PERSON_KEY,kind="stable").copy(); weights=g["MULT"].astype(float).to_numpy(); total=float(weights.sum()); interval=total/n
    if float(weights.max()) >= interval:
        probs=weights/weights.sum(); idx=rng.choice(len(g),size=n,replace=False,p=probs); s=g.iloc[np.sort(idx)].copy(); s["analysis_weight"]=s["MULT"].astype(float); s["sampling_mode"]="weighted_wor_fallback"; return s
    start=float(rng.uniform(0,interval)); thresholds=start+interval*np.arange(n); idx=np.searchsorted(np.cumsum(weights),thresholds,side="left")
    if len(np.unique(idx))!=n: raise AssertionError("Duplicate PPS selection")
    s=g.iloc[idx].copy(); s["analysis_weight"]=total/n; s["sampling_mode"]="systematic_pps"; return s

def build_persona(row):
    base=f"You are a {int(row.age)}-year-old {row.gender} living in {row.sector} {row.state_name}, India."
    persona=" ".join([base,f"You are the {row.relationship}.",f"Your marital status is {row.marital_status}.",f"You are {row.enrolment_status}.",f"You were {row.economic_activity_status}.",f"You live in a household of {int(row.household_size)} people.",f"Your household religion is {row.religion}.",f"Your household social group is {row.social_group}.",f"The main language spoken in your household is {row.household_language}.",f"Your household's per-person monthly consumption level is in the {row.mpce_band} of the national distribution."])
    validate_persona(persona); return persona

def load_cams(zip_path):
    member_cols=PERSON_KEY+["SEC","BL31C3","BL31C4","BL31C5","BL31C6","BL31C7","BL31C8","BL32C3","BL32C4","BL32C6","BL32C7","BL32C8","BL33C3","MULT"]
    hh_cols=HOUSEHOLD_KEY+["BL41I1","BL41I2","BL41I3","BL41I4","BL6I6"]
    with zipfile.ZipFile(zip_path) as zf:
        names=set(zf.namelist()); member_name=next((n for n in names if n.endswith("NSS79CAMS_Member.csv")),None); hh_name=next((n for n in names if n.endswith("NSS79CAMS_Household.csv")),None)
        if not member_name or not hh_name: raise FileNotFoundError("Required CAMS member/household CSV files not found inside ZIP")
        member=pd.read_csv(zf.open(member_name),usecols=member_cols); hh=pd.read_csv(zf.open(hh_name),usecols=hh_cols)
    if hh.duplicated(HOUSEHOLD_KEY).any(): raise AssertionError("Household key is not unique")
    df=member.merge(hh,on=HOUSEHOLD_KEY,how="left",validate="many_to_one")
    if df["BL41I1"].isna().any(): raise AssertionError("Member-household merge failure")
    df=df[(df["BL31C5"]>=15)&df["BL31C4"].isin([1,2])].copy(); df["age"]=df["BL31C5"].astype(int); df["gender"]=df["BL31C4"].map(GENDER_MAP); df["gender_binary"]=df["BL31C4"].map({1:"male",2:"female"}); df["sector"]=df["SEC"].map(SECTOR_MAP); df["state_name"]=df["ST"].map(STATE_MAP); df["relationship"]=df["BL31C3"].map(RELATION_MAP); df["marital_status"]=df["BL31C6"].map(MARITAL_MAP); df["enrolment_status"]=df["BL31C7"].map(ENROLMENT_MAP); df["economic_activity_status"]=df["BL31C8"].map(ECON_MAP); df["household_size"]=df["BL41I1"].astype(int); df["religion"]=df["BL41I2"].map(RELIGION_MAP); df["social_group"]=df["BL41I3"].map(SOCIAL_MAP); df["household_language"]=df["BL41I4"].map(LANGUAGE_MAP); df["age_group"]=df["age"].map(age_group); df["mpce"]=df["BL6I6"].astype(float)/df["BL41I1"].replace(0,np.nan).astype(float)
    needed=["gender","sector","state_name","relationship","marital_status","enrolment_status","economic_activity_status","household_size","religion","social_group","household_language","mpce"]; miss=df[needed].isna().sum()
    if int(miss.sum()): raise AssertionError(f"Missing persona values: {miss[miss>0].to_dict()}")
    cuts=weighted_quantiles(df["mpce"].to_numpy(float),df["MULT"].to_numpy(float)); labels=["lowest fifth","second fifth","middle fifth","fourth fifth","highest fifth"]; df["mpce_band"]=pd.cut(df["mpce"],[-np.inf,*cuts,np.inf],labels=labels,include_lowest=True).astype(str)
    df["mobile_ability"]=df["BL32C3"].isin([1,2]).astype(int); df["mobile_3m"]=df["BL32C4"].isin([1,2,3]).astype(int); df["computer_ability"]=df["BL32C6"].eq(1).astype(int); df["internet_ability"]=df["BL32C7"].isin([1,2,3]).astype(int); df["internet_3m"]=df["BL32C8"].eq(1).astype(int); df["copy_paste"]=df["BL33C3"].eq(1).astype(int); return df

def prepare(zip_path,out_dir,n,seed):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); df=load_cams(zip_path); n=min(n,len(df)); strata_cols=["sector","gender_binary","age_group"]; strata=df.groupby(strata_cols,observed=True)["MULT"].sum().reset_index(name="W").sort_values(strata_cols).reset_index(drop=True); strata["n"]=allocate_proportional(strata,n); rng=np.random.default_rng(seed); parts=[]
    for _,cell in strata.iterrows():
        mask=np.ones(len(df),dtype=bool)
        for col in strata_cols: mask &= (df[col].to_numpy()==cell[col])
        parts.append(pps_systematic(df.loc[mask],int(cell["n"]),rng))
    sample=pd.concat(parts,ignore_index=True)
    if len(sample)!=n: raise AssertionError(f"Sample size mismatch {len(sample)} != {n}")
    if sample.duplicated(PERSON_KEY).any(): raise AssertionError("Duplicate selected person")
    sample=sample.sample(frac=1,random_state=seed).reset_index(drop=True); sample["anon_id"]=[f"CAMS-RPF-{i:05d}" for i in range(1,len(sample)+1)]
    private_cols=["anon_id",*PERSON_KEY,"age","gender","gender_binary","sector","state_name","relationship","marital_status","enrolment_status","economic_activity_status","household_size","religion","social_group","household_language","mpce_band","age_group","MULT","analysis_weight","sampling_mode",*OUTCOME_COLS.keys()]; sample[private_cols].to_csv(out/"matched_sample_private.csv",index=False)
    base=[]
    for _,r in sample.iterrows():
        persona=build_persona(r); base.append({"anon_id":r["anon_id"],"persona":persona,"prompt":build_prompt(persona)})
    write_jsonl(out/"requests_base.jsonl",base); benchmarks=[]
    for k in OUTCOME_COLS: benchmarks.append({"outcome":k,"full_cams_weighted":float(np.average(df[k],weights=df["MULT"])),"sample_weighted":float(np.average(sample[k],weights=sample["analysis_weight"]))})
    manifest={"dataset":"NSO CAMS 2022-23","seed":seed,"n":len(sample),"analytic_population":"age 15+, recorded gender male/female","strata":strata.to_dict("records"),"benchmarks":benchmarks,"private_targets_sha256":hashlib.sha256((out/"matched_sample_private.csv").read_bytes()).hexdigest()}; (out/"sample_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8"); return manifest

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--zip",required=True); ap.add_argument("--out",required=True); ap.add_argument("--n",type=int,default=2500); ap.add_argument("--seed",type=int,default=30082026); args=ap.parse_args(); print(json.dumps(prepare(args.zip,args.out,args.n,args.seed),indent=2))
if __name__=="__main__":main()
