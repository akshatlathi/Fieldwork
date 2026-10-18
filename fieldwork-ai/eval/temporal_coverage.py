"""Development ablation: time-bin frame selection versus current sharpness ranking.

Uses real captures already extracted by organized_captures.py --phase local.
Does not change production selection or establish semantic view coverage accuracy.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork.take.frames import Frame, select_frames, DARK, BRIGHT, _gray_metrics
from fieldwork.stats import rate


def time_bin_frames(frames, k=8):
    """Reserve each time interval, choosing its sharpest usable frame."""
    if not frames or k < 1:
        return []
    end = max(f.t for f in frames) + 1e-6
    bins = [[] for _ in range(k)]
    for frame in frames:
        if DARK < frame.brightness < BRIGHT:
            bins[min(k-1, int(frame.t/end*k))].append(frame)
    return [max(bucket, key=lambda f:f.sharpness) for bucket in bins if bucket]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--results',type=Path,required=True)
    args=ap.parse_args();args.root=args.root.resolve();args.results=args.results.resolve()
    import cv2
    import numpy as np
    import torch
    from fieldwork.take.grade import embed
    from fieldwork.unbox.align import align
    torch.set_num_threads(4)
    base=json.loads((args.results/'local-report.json').read_text())
    report={'kind':'development_time_bin_selection_ablation',
        'limits':['Posthoc development experiment prompted by baseline garment-14 failure; not held-out evidence.',
                  'Time coverage does not prove semantic region coverage.',
                  'Same-session retrieval shares background and code-card cues.',
                  'Alignment success is a geometric acceptance flag, not independently verified alignment accuracy.'],
        'baseline_metrics':base['metrics'],'selected':{},'matching':[]}
    gallery=[]
    for capture in base['captures']:
        garment=capture['garment'];cap=cv2.VideoCapture(str(args.root/garment/'take.mp4'))
        fps=cap.get(cv2.CAP_PROP_FPS);cap.release();step=max(1,round(.25*fps))
        frames=[]
        for i,path in enumerate(sorted((args.results/'frames'/garment).glob('f*.jpg'))):
            sharp,bright=_gray_metrics(cv2.imread(str(path)))
            frames.append(Frame(path.stem,path,i*step/fps,sharp,bright))
        chosen=time_bin_frames(frames)
        report['selected'][garment]=[{'path':str(f.path),'t':f.t,'sharpness':f.sharpness} for f in chosen]
        gallery.extend((garment,f.path) for f in chosen)
    A=embed([p for _,p in gallery])
    probes=[(r['garment'],Path(r['photo'])) for r in base['matching']]
    B=embed([p for _,p in probes])
    for (garment,photo),scores in zip(probes,B@A.T):
        j=int(scores.argmax());matched,image=gallery[j];result=align(photo,image)
        report['matching'].append({'garment':garment,'photo':str(photo),'matched_garment':matched,
            'matched_frame':str(image),'cosine':float(scores[j]),'correct_garment':garment==matched,
            'alignment_ok':bool(result.ok),'inliers':result.inliers})
    report['metrics']={'photo_to_video_top1':rate(sum(r['correct_garment'] for r in report['matching']),len(probes)),
        'matched_pair_alignment':rate(sum(r['alignment_ok'] for r in report['matching']),len(probes)),
        'selected_frames':len(gallery)}
    (args.results/'temporal-ablation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report['metrics'],indent=2))


if __name__=='__main__':main()
