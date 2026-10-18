"""Inspect two stress-test failures using the actual production-selected crops.

Cases are selected after inspecting the stress results: diagnostic, not unbiased accuracy.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fieldwork import config
from fieldwork.unbox import judge
from fieldwork.unbox.diff import crop_pair


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stress-report",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    report=json.loads(args.stress_report.read_text())
    selected=[]
    for row in report["cases"]:
        candidates=[r for r in row.get("combined",{}).get("regions",[]) if r["score"]>=config.CHANGE_SCORE]
        if not candidates:continue
        if row["variant"]=="unchanged_transform":selected.append(("unchanged_false_proposal",row,candidates[0]))
        elif not row["combined"].get("top3_hit"):selected.append(("poor_localisation",row,candidates[0]))
    args.out.mkdir(parents=True,exist_ok=False)
    output={"kind":"posthoc_synthetic_selected_crop_diagnostics","accuracy_benchmark":False,"checks":[]}
    for reason,row,region in selected[:2]:
        a,b=crop_pair(row["reference"],row["aligned_path"],region["box_2d"],out_dir=args.out/row["source"])
        start=time.monotonic();response=judge.compare(a,b)
        result={"reason_selected":reason,"source":row["source"],"variant":row["variant"],"region":region,
                "listing_crop":str(a),"received_crop":str(b),"response":response.model_dump(),
                "seconds":round(time.monotonic()-start,2)}
        output["checks"].append(result)
        (args.out/"report.json").write_text(json.dumps(output,indent=2))
        print(json.dumps(result),flush=True)


if __name__=="__main__":main()
