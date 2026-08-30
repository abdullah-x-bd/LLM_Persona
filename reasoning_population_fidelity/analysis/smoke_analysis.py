from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

OUTCOMES=["mobile_ability","mobile_3m","computer_ability","internet_ability","internet_3m","copy_paste"]

def load_jsonl(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def run(responses_path,out_path):
    rows=load_jsonl(responses_path); by=defaultdict(list)
    for r in rows: by[r["reasoning"]].append(r)
    summary=[]
    for cond,grp in sorted(by.items()):
        for y in OUTCOMES:
            probs=[float(r["response"][y]["probability_yes"]) for r in grp]; answers=[r["response"][y]["answer"]=="yes" for r in grp]
            summary.append({"reasoning":cond,"outcome":y,"n":len(grp),"yes_prevalence":sum(answers)/len(answers),"mean_probability_yes":sum(probs)/len(probs)})
    Path(out_path).write_text(json.dumps({"rows":summary},indent=2),encoding="utf-8"); return summary
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--responses",required=True); ap.add_argument("--out",required=True); args=ap.parse_args(); print(json.dumps(run(args.responses,args.out),indent=2))
