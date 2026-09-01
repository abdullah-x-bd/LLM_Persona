from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))
from unified_analysis import (OUTCOMES, BOOT_REPS, BOOT_SEED, truth_and_demo, decrypt_qwen,
    decrypt_followup, build_cell, metrics, outcome_metrics, paired_bootstrap,
    fourway_heterogeneity, subgroup_table, age_reasoning_bootstrap,
    probability_tail, pattern_dist, entropy, js, weighted_corr)

LEGACY=[
 {"cell":"luna_thin","method_class":"LLM","model":"Luna","condition":"thin","intervention":"persona","n":1000,"individual_brier":0.16941,"probability_prevalence_mae":0.10172,"hard_prevalence_mae":0.14556},
 {"cell":"luna_rich","method_class":"LLM","model":"Luna","condition":"rich","intervention":"persona","n":1000,"individual_brier":0.15075,"probability_prevalence_mae":0.09656,"hard_prevalence_mae":0.17753},
 {"cell":"claude_thin","method_class":"LLM","model":"Claude","condition":"thin","intervention":"persona","n":250,"individual_brier":0.15822,"probability_prevalence_mae":0.08300,"hard_prevalence_mae":0.12073},
 {"cell":"claude_rich","method_class":"LLM","model":"Claude","condition":"rich","intervention":"persona","n":250,"individual_brier":0.14365,"probability_prevalence_mae":0.09364,"hard_prevalence_mae":0.07662},
]
PRIMARY=["individual_brier","log_loss","hard_accuracy","probability_prevalence_mae","hard_prevalence_mae"]

def joint_tables(cells):
    ref=cells["qwen_off"]
    h=pattern_dist(ref["Y"],ref["w"]); hc=weighted_corr(ref["Y"],ref["w"]); tri=np.triu_indices(6,1)
    rows=[{"cell":"human","entropy_bits":entropy(h),"largest_pattern_share":float(h.max()),"joint_tv":0.0,"joint_js":0.0,"correlation_rmse":0.0}]
    patt=[{"cell":"human","pattern":format(k,"06b"),"share":float(h[k])} for k in range(64)]
    for cid,c in cells.items():
        d=pattern_dist(c["A"],c["w"]); cc=weighted_corr(c["A"],c["w"])
        rows.append({"cell":cid,"entropy_bits":entropy(d),"largest_pattern_share":float(d.max()),"joint_tv":float(.5*np.abs(d-h).sum()),"joint_js":js(d,h),"correlation_rmse":float(np.sqrt(np.mean((cc[tri]-hc[tri])**2)))})
        patt += [{"cell":cid,"pattern":format(k,"06b"),"share":float(d[k])} for k in range(64)]
    return pd.DataFrame(rows),pd.DataFrame(patt)

def legacy_effects():
    d=pd.DataFrame(LEGACY).set_index("cell"); rows=[]
    for name,a,b in [("luna_rich_minus_thin","luna_thin","luna_rich"),("claude_rich_minus_thin","claude_thin","claude_rich")]:
        for m in ["individual_brier","probability_prevalence_mae","hard_prevalence_mae"]:
            rows.append({"contrast":name,"metric":m,"estimate":float(d.loc[b,m]-d.loc[a,m]),"ci_low":np.nan,"ci_high":np.nan,"n":int(d.loc[a,"n"]),"bootstrap_reps":np.nan,"source":"frozen_original_analysis"})
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--qwen-dir",type=Path,required=True); ap.add_argument("--s01-dir",type=Path,required=True); ap.add_argument("--s03-dir",type=Path,required=True); ap.add_argument("--baseline-dir",type=Path,required=True); ap.add_argument("--outdir",type=Path,required=True); a=ap.parse_args(); a.outdir.mkdir(parents=True,exist_ok=True)
    key=os.environ["OPENROUTER_API_KEY"]; truth,wcol=truth_and_demo()
    q=decrypt_qwen(a.qwen_dir/"raw_results.enc.b64",key); d1=decrypt_followup(a.s01_dir/"raw_results.enc.b64",key,"S01_second_model_reasoning"); d3=decrypt_followup(a.s03_dir/"raw_results.enc.b64",key,"S03_persona_reasoning_factorial")
    cells={
      "qwen_off":build_cell(q,"reasoning","off",truth,wcol),"qwen_low":build_cell(q,"reasoning","low",truth,wcol),"qwen_medium":build_cell(q,"reasoning","medium",truth,wcol),
      "deepseek_thin_off":build_cell(d3,"arm_id","thin_off",truth,wcol),"deepseek_thin_high":build_cell(d3,"arm_id","thin_high",truth,wcol),
      "deepseek_rich_off":build_cell(d1,"arm_id","rich_off",truth,wcol),"deepseek_rich_high":build_cell(d1,"arm_id","rich_high",truth,wcol)}
    assert all(len(c["ids"])==1000 for c in cells.values())
    rows=list(LEGACY); out=[]
    meta={"qwen_off":("Qwen","off","reasoning"),"qwen_low":("Qwen","low","reasoning"),"qwen_medium":("Qwen","medium","reasoning"),"deepseek_thin_off":("DeepSeek","thin/off","factorial"),"deepseek_thin_high":("DeepSeek","thin/high","factorial"),"deepseek_rich_off":("DeepSeek","rich/off","factorial"),"deepseek_rich_high":("DeepSeek","rich/high","factorial")}
    for cid,c in cells.items():
        model,cond,intv=meta[cid]; rows.append({"cell":cid,"method_class":"LLM","model":model,"condition":cond,"intervention":intv,"n":1000,**metrics(c)}); out += outcome_metrics(c,cid)
    bm=pd.read_csv(a.baseline_dir/"baseline_metrics.csv")
    for _,r in bm.iterrows():
        rows.append({"cell":"baseline_"+r.model,"method_class":"supervised_crossfit","model":r.model,"condition":"OOF","intervention":"supervised_reference","n":1000,"individual_brier":float(r.individual_brier),"log_loss":float(r.log_loss),"hard_accuracy":float(r.hard_accuracy),"probability_prevalence_mae":float(r.probability_prevalence_mae),"hard_prevalence_mae":float(r.hard_prevalence_mae),"joint_tv":float(r.joint_tv),"joint_js":float(r.joint_js),"entropy_bits":float(r.hard_pattern_entropy_bits),"correlation_rmse":float(r.hard_correlation_rmse)})
    cell_df=pd.DataFrame(rows)

    contrasts=legacy_effects()
    specs=[("qwen_low_minus_off","qwen_off","qwen_low"),("qwen_medium_minus_off","qwen_off","qwen_medium"),("deepseek_thin_high_minus_off","deepseek_thin_off","deepseek_thin_high"),("deepseek_rich_high_minus_off","deepseek_rich_off","deepseek_rich_high"),("deepseek_persona_off_rich_minus_thin","deepseek_thin_off","deepseek_rich_off"),("deepseek_persona_high_rich_minus_thin","deepseek_thin_high","deepseek_rich_high")]
    for i,(name,x,y) in enumerate(specs):
        for r in paired_bootstrap(cells[x],cells[y],PRIMARY,BOOT_SEED+i): contrasts.append({"contrast":name,**r,"source":"harmonized_raw_reanalysis"})
    for r in fourway_heterogeneity(cells["deepseek_thin_off"],cells["deepseek_thin_high"],cells["deepseek_rich_off"],cells["deepseek_rich_high"],PRIMARY,BOOT_SEED+50): contrasts.append({"contrast":"deepseek_persona_x_reasoning_interaction",**r,"source":"harmonized_raw_reanalysis"})
    for r in fourway_heterogeneity(cells["qwen_off"],cells["qwen_medium"],cells["deepseek_rich_off"],cells["deepseek_rich_high"],PRIMARY,BOOT_SEED+60): contrasts.append({"contrast":"deepseek_minus_qwen_reasoning_effect",**r,"source":"harmonized_raw_reanalysis"})
    con=pd.DataFrame(contrasts)

    joint,patt=joint_tables(cells); sub=subgroup_table(cells,truth,wcol); age=age_reasoning_bootstrap(cells,truth); tails=probability_tail(cells); outdf=pd.DataFrame(out)
    effects=[]
    for name,x,y in specs:
        gx=outdf[outdf.cell==x].set_index("outcome"); gy=outdf[outdf.cell==y].set_index("outcome")
        for o in OUTCOMES:
            for m in ["brier","log_loss","hard_accuracy","probability_prevalence_abs_error","hard_prevalence_abs_error"]:
                effects.append({"contrast":name,"outcome":o,"metric":m,"effect":float(gy.loc[o,m]-gx.loc[o,m])})

    cell_df.to_csv(a.outdir/"cell_metrics.csv",index=False); con.to_csv(a.outdir/"contrasts.csv",index=False); outdf.to_csv(a.outdir/"outcome_metrics.csv",index=False); pd.DataFrame(effects).to_csv(a.outdir/"outcome_effects.csv",index=False); joint.to_csv(a.outdir/"joint_metrics.csv",index=False); patt.to_csv(a.outdir/"pattern_distribution.csv",index=False); sub.to_csv(a.outdir/"subgroup_metrics.csv",index=False); age.to_csv(a.outdir/"age_reasoning_effects.csv",index=False); tails.to_csv(a.outdir/"probability_tail.csv",index=False)
    evidence=con[con.contrast.isin(["luna_rich_minus_thin","claude_rich_minus_thin","qwen_medium_minus_off","deepseek_rich_high_minus_off","deepseek_persona_x_reasoning_interaction","deepseek_minus_qwen_reasoning_effect"])]; evidence.to_csv(a.outdir/"evidence_matrix.csv",index=False)
    summary={"status":"MANUSCRIPT_READY_ZERO_INFERENCE_SYNTHESIS","paid_inference":False,"respondent_plaintext_emitted":False,"bootstrap_reps":BOOT_REPS,"bootstrap_seed":BOOT_SEED,"raw_reanalysis_cells":{k:len(v["ids"]) for k,v in cells.items()},"legacy_truth_linked_cells":["luna_thin","luna_rich","claude_thin","claude_rich"],"supervised_comparators":bm.model.tolist(),"note":"Luna and Claude point metrics are carried from their frozen analyses; Qwen and DeepSeek are recomputed from authoritative raw encrypted outputs with one harmonized metric implementation."}
    (a.outdir/"summary.json").write_text(json.dumps(summary,indent=2)); print("FINAL_ZERO_INFERENCE_SYNTHESIS_PASS"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
