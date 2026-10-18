"""Controlled CV stress test, never a real-capture accuracy benchmark.

Uses real public garment photographs with known digital transforms/painted marks.
python eval/component_stress.py --n 12 --out data/results/components-stress
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork import config
from fieldwork.stats import rate
from fieldwork.unbox.align import align
from fieldwork.unbox.diff import change_regions
from fieldwork.unbox.pipeline import pair_frames

ROOT = Path(__file__).resolve().parent.parent


def iou(a, b):
    y0, x0, y1, x1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, y1-y0)*max(0, x1-x0)
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union > 0 else 0.


def hit(box, truth):
    return iou(box, truth) >= .1


def paint(image):
    h, w = image.shape[:2]
    border = np.concatenate([image[:8].reshape(-1, 3), image[-8:].reshape(-1, 3)])
    background = np.median(border, axis=0)
    foreground = (np.linalg.norm(image.astype(float)-background, axis=2)>35).astype(np.uint8)
    distance = cv2.distanceTransform(foreground, cv2.DIST_L2, 5)
    # A deterministic interior point avoids painting only the background.
    _, radius, _, center = cv2.minMaxLoc(distance)
    radius = int(min(radius*.4, min(h, w)*.045))
    if radius < 5:
        raise ValueError("No sufficiently large foreground interior for controlled mark")
    x, y = center
    mask = np.zeros((h,w), np.float32)
    cv2.circle(mask, (x,y), radius, 1., -1)
    mask = cv2.GaussianBlur(mask, (0,0), 2)*.75
    changed = np.clip(image*(1-mask[...,None])+np.array([30,65,125])*mask[...,None],0,255).astype(np.uint8)
    return changed, [max(0,round((y-radius-6)/h*1000)),max(0,round((x-radius-6)/w*1000)),
                     min(1000,round((y+radius+6)/h*1000)),min(1000,round((x+radius+6)/w*1000))]


def transform(image):
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w/2,h/2), 7, .92)
    matrix[:,2] += (w*.025,-h*.015)
    transformed = cv2.warpAffine(image,matrix,(w,h),borderValue=(245,245,245))
    transformed = np.clip(transformed.astype(float)*1.08+3,0,255).astype(np.uint8)
    return transformed, np.vstack([matrix,[0,0,1]])


def alignment_error(estimated, applied, shape):
    h,w = shape[:2]
    points = np.array([[[x*w,y*h] for x,y in ((.2,.2),(.8,.2),(.5,.5),(.2,.8),(.8,.8))]],np.float32)
    moved = cv2.perspectiveTransform(points, applied)
    recovered = cv2.perspectiveTransform(moved,estimated)
    return float(np.median(np.linalg.norm(recovered-points,axis=2)))


def summarise(rows):
    output = {}
    for method in ("colour","combined"):
        changed = [r for r in rows if r["variant"]=="painted_mark"]
        clean = [r for r in rows if r["variant"]=="unchanged_transform"]
        output[method] = {"mark_top3_recall": rate(sum(r.get(method,{}).get("top3_hit",False) for r in changed),len(changed)),
                          "mark_top3_recall_after_production_threshold": rate(sum(r.get(method,{}).get("threshold_hit",False) for r in changed),len(changed)),
                          "unchanged_with_candidates_above_threshold": rate(sum(r.get(method,{}).get("above_threshold",0)>0 for r in clean),len(clean))}
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n",type=int,default=12)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    if args.n < 2:
        raise SystemExit("Use at least two source photographs")
    import torch
    torch.set_num_threads(8)
    args.out.mkdir(parents=True,exist_ok=False)
    images=args.out/"images";images.mkdir()
    parquet=ROOT/"data/hf/data/test-00000-of-00001.parquet"
    sources=[];seen=set()
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=32,columns=["image"]):
        for row in batch.to_pylist():
            blob=row["image"]["bytes"];sha=hashlib.sha256(blob).hexdigest()
            if sha in seen:continue
            seen.add(sha)
            image=cv2.imdecode(np.frombuffer(blob,np.uint8),cv2.IMREAD_COLOR)
            scale=min(1.,720/max(image.shape[:2]))
            image=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
            sources.append((image,sha,row["image"].get("path")))
            if len(sources)==args.n:break
        if len(sources)==args.n:break
    rows=[];listing={};received=[];identities={}
    report={"kind":"controlled_synthetic_stress", "real_capture_accuracy":False,
            "meta":{"sources":len(sources),"seed":0,"dino":config.DINO_MODEL,"candidate_threshold":config.CHANGE_SCORE,
                    "hit_definition":"IoU >= 0.1 with known painted-mark box; fixed before running",
                    "limits":["Digital marks and transformations are not physical received-garment changes.",
                              "Closed-set retrieval of transformed copies does not establish garment identity or front/back matching.",
                              "Colour-only removes DINO while retaining the original colour weight; scores are not recalibrated."]},"cases":rows}
    def save():
        report["candidate_metrics"]=summarise(rows)
        (args.out/"report.json").write_text(json.dumps(report,indent=2))
    for i,(image,sha,path) in enumerate(sources):
        source_id=f"source-{i:02d}";ref=images/f"{source_id}-ref.jpg"
        cv2.imwrite(str(ref),image);listing[source_id]=ref
        try:
            painted,box=paint(image)
        except ValueError as exc:
            report.setdefault("generation_errors",[]).append({"source":source_id,"error":str(exc)})
            continue
        for variant,raw,truth in (("unchanged_transform",image,None),("painted_mark",painted,box)):
            transformed,matrix=transform(raw);target=images/f"{source_id}-{variant}.jpg"
            cv2.imwrite(str(target),transformed)
            if variant=="unchanged_transform":received.append(target);identities[str(target)]=source_id
            row={"source":source_id,"source_sha256":sha,"source_image_path":path,"variant":variant,"truth_box":truth,
                 "reference":str(ref),"received":str(target)}
            rows.append(row)
            start=time.monotonic()
            try:
                result=align(ref,target)
                row["aligned"]=bool(result.ok);row["inliers"]=result.inliers
                if result.ok:
                    row["alignment_error_pixels"]=alignment_error(result.H,matrix,image.shape)
                    row["aligned_path"]=str(result.warped_path)
                    for method in ("colour","combined"):
                        regions=change_regions(ref,result.warped_path,top_k=3,method=method)
                        row[method]={"regions":[asdict(r) for r in regions],
                                     "top3_hit":any(hit(r.box_2d,truth) for r in regions) if truth else None,
                                     "threshold_hit":any(r.score>=config.CHANGE_SCORE and hit(r.box_2d,truth) for r in regions) if truth else None,
                                     "above_threshold":sum(r.score>=config.CHANGE_SCORE for r in regions)}
            except Exception as exc:row["error"]=f"{type(exc).__name__}: {exc}"[:250]
            row["seconds"]=round(time.monotonic()-start,2)
            save();print(source_id,variant,"aligned",row.get("aligned"),"error",row.get("error"),flush=True)
    try:
        pairs=pair_frames(listing,received)
        correct=sum(identities[str(path)]==fid for fid,path in pairs)
        report["matching"]={"n_sources":len(listing),"accepted_pairs":len(pairs),"correct":correct,
                            "correct_over_all_sources":rate(correct,len(listing)),
                            "pairs":[{"listing":fid,"received":str(path),"correct":identities[str(path)]==fid} for fid,path in pairs]}
    except Exception as exc:report["matching_error"]=f"{type(exc).__name__}: {exc}"[:250]
    report["alignment_success"]=rate(sum(r.get("aligned",False) for r in rows),len(rows))
    save();print(json.dumps({k:v for k,v in report.items() if k not in ("cases","matching")},indent=2))


if __name__=="__main__":main()
