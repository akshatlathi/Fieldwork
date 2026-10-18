"""Development checks for upload, retained candidates and alignment improvements.

Uses cached original frame extraction, preserving earlier benchmark artifacts.
--live submits four representative original phone videos through the full API.
"""
import argparse
import csv
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--live',action='store_true')
    args=ap.parse_args();root=Path('data/organized-garments').resolve()
    baseline=Path('data/results/real-captures-2026-10-18').resolve()
    out=Path('data/results/workflow-priorities-2026-10-18').resolve();out.mkdir(exist_ok=True)
    import torch
    torch.set_num_threads(4)
    if args.live:
        from fastapi.testclient import TestClient
        from fieldwork.api import app
        from fieldwork import config
        if config.STORE_DIR.resolve() != (out/'store').resolve():raise SystemExit('Use isolated results store')
        codes={f"garment-{r['garment']}":r['code'] for r in csv.DictReader((root/'file-manifest.csv').open(encoding='utf-8-sig'))}
        path=out/'live-videos.json';rows=json.loads(path.read_text()) if path.exists() else []
        with TestClient(app,raise_server_exceptions=False) as client:
            for name in ('garment-01','garment-05','garment-06','garment-14'):
                if any(r['garment']==name for r in rows):continue
                start=time.monotonic();print('start',name,flush=True)
                source=root/name/'take.mp4';response=client.post('/take',data={'code':codes[name]},
                    files={'video':('take.mp4',source.read_bytes(),'video/mp4')})
                row={'garment':name,'http':response.status_code,'seconds':round(time.monotonic()-start,2)}
                if response.status_code==200:
                    row['record']=response.json()
                    row['listing']=client.get('/listings/'+row['record']['id']).json()
                else:row['error']=response.text[:300]
                rows.append(row);path.write_text(json.dumps(rows,indent=2));print(name,row['http'],row['seconds'],flush=True)
        return

    import cv2
    import numpy as np
    from fieldwork.take.frames import Frame,_gray_metrics,evidence_candidates
    from fieldwork.take.grade import embed
    from fieldwork.unbox.align import align
    original=json.loads((baseline/'local-report.json').read_text())
    report={'scope':'same-session development diagnostics; no semantic alignment accuracy labels or received truth',
            'selected':{},'matches':[],'negative_geometric_controls':[]}
    gallery=[]
    for row in original['captures']:
        name=row['garment'];cap=cv2.VideoCapture(str(root/name/'take.mp4'));fps=cap.get(cv2.CAP_PROP_FPS);cap.release()
        frames=[];step=max(1,round(.25*fps))
        for i,p in enumerate(sorted((baseline/'frames'/name).glob('f[0-9][0-9][0-9][0-9].jpg'))):
            sharp,bright=_gray_metrics(cv2.imread(str(p)));frames.append(Frame(p.stem,p,i*step/fps,sharp,bright))
        chosen=evidence_candidates(frames,k=8)
        report['selected'][name]=[{'path':str(f.path),'t':f.t} for f in chosen]
        for f in chosen:
            target=out/'candidate-frames'/name/f.path.name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(f.path,target);gallery.append((name,target))
    A=embed([p for _,p in gallery]);probes=[(r['garment'],Path(r['photo'])) for r in original['matching']]
    B=embed([p for _,p in probes])
    names=sorted(report['selected'])
    for (name,photo),scores in zip(probes,B@A.T):
        j=int(scores.argmax());matched,image=gallery[j]
        own=[int(i) for i in np.argsort(-scores) if gallery[int(i)][0]==name][:3]
        attempts=[]
        for i in own:
            result=align(photo,gallery[i][1])
            attempts.append({'frame':str(gallery[i][1]),'ok':bool(result.ok),'method':result.method,
                'inliers':result.inliers,'ratio':result.inlier_ratio,'overlap':result.overlap_fraction,
                'aligned_path':str(result.warped_path) if result.warped_path else None})
            if result.ok:break
        report['matches'].append({'garment':name,'photo':str(photo),'matched_garment':matched,
            'correct_garment':name==matched,'cosine':float(scores[j]),'attempts':attempts,
            'alignment_ok':any(a['ok'] for a in attempts)})
        # Distinct garment controls reveal shared-background alignment. Geometric
        # acceptance must never be reported as proof of garment identity.
        other=names[(names.index(name)+1)%len(names)]
        index=next(int(i) for i in np.argsort(-scores) if gallery[int(i)][0]==other)
        negative=align(photo,gallery[index][1])
        report['negative_geometric_controls'].append({'garment':name,'other':other,'ok':bool(negative.ok),'method':negative.method})
        (out/'local-checks.json').write_text(json.dumps(report,indent=2))
        print(name,photo.name,'match',matched,'aligned',attempts[-1]['ok'],attempts[-1]['method'],flush=True)
    report['metrics']={'retrieval_correct':sum(r['correct_garment'] for r in report['matches']),'retrieval_total':len(probes),
        'alignment_accepted':sum(r['alignment_ok'] for r in report['matches']),
        'cross_garment_geometry_accepted':sum(r['ok'] for r in report['negative_geometric_controls']),
        'candidate_frames':len(gallery)}
    (out/'local-checks.json').write_text(json.dumps(report,indent=2));print(report['metrics'],flush=True)


if __name__=='__main__':main()
