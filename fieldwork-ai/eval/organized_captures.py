"""Evaluate owner-annotated seller captures without inventing received-session truth.

Run with --phase local or live, an isolated local FW_STORE_DIR and Vertex settings.
Original inputs are read only. Reports are incremental and live calls resume by case.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork import config
from fieldwork.stats import rate

# Frozen before inference, from owner-corrected notes. No grade, severity or
# pixel-visibility reference is inferred. 01's defect type is explicitly unknown.
POSITIVE = {"garment-01", "garment-02", "garment-03", "garment-05", "garment-06"}
LIMITS = ["Seller capture evaluation only; no received/unboxing session or planted-change truth supplied.",
          "Owner-reported presence is not independently adjudicated visible-in-image ground truth.",
          "No grade/severity accuracy is computed without reference labels.",
          "Matching uses same-session photos/video, a shared background and visible code cards; not garment identity proof.",
          "These inspected garments are development data, not a locked final test split."]


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def photo_summary(rows):
    photos = [r for r in rows if r['track'] == 'photos']
    positives = [r for r in photos if r['owner_reports_defect']]
    negatives = [r for r in photos if not r['owner_reports_defect']]
    successful = [r for r in photos if r.get('record')]
    return {'photo_api_completed': rate(len(successful), len(photos)),
            'code_read': rate(sum(r.get('record', {}).get('capture', {}).get('code_seen', False) for r in photos), len(photos)),
            'owner_positive_with_any_shown_defect': rate(sum(bool(r.get('shown_defects')) for r in positives), len(positives)),
            'owner_negative_with_any_shown_defect': rate(sum(bool(r.get('shown_defects')) for r in negatives), len(negatives)),
            'owner_positive_processing_failures': sum(not r.get('record') for r in positives),
            'owner_negative_processing_failures': sum(not r.get('record') for r in negatives),
            'semantic_claim_review': 'pending independent review; presence checks do not establish defect type/location correctness'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--phase', choices=['local', 'live'], required=True)
    args = ap.parse_args()
    args.root = args.root.resolve(); args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    folders = sorted(p for p in args.root.glob('garment-*') if p.is_dir())
    manifest = list(csv.DictReader((args.root/'file-manifest.csv').open(encoding='utf-8-sig')))
    codes = {f"garment-{r['garment']}": r['code'] for r in manifest}
    if args.phase == 'local':
        import cv2
        import numpy as np
        import torch
        torch.set_num_threads(4)
        from fieldwork.take import frames as fr
        from fieldwork.take.grade import embed
        from fieldwork.unbox.align import align
        path = args.out/'local-report.json'
        report = json.loads(path.read_text()) if path.exists() else {
            'kind': 'real_same_session_capture_diagnostics', 'limits': LIMITS,
            'source_integrity': [], 'captures': [], 'matching': []}
        report['source_integrity'] = []
        for entry in manifest:
            source = args.root / entry['organized_path'].replace('\\', '/')
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            report['source_integrity'].append({'path':str(source), 'sha256':actual, 'matches_manifest':actual == entry['sha256']})
        for folder in folders:
            if any(r['garment'] == folder.name for r in report['captures']):
                continue
            start = time.monotonic()
            all_frames = fr.extract_frames(folder/'take.mp4', args.out/'frames'/folder.name)
            chosen = fr.select_frames(all_frames, k=8)
            cap = cv2.VideoCapture(str(folder/'take.mp4'))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps if fps else None
            cap.release()
            row = {'garment':folder.name, 'video_seconds':duration,
                   'video_bytes':(folder/'take.mp4').stat().st_size,
                   'video_over_inline_limit':(folder/'take.mp4').stat().st_size > 20*1024*1024,
                   'all_quality':fr.quality_report(all_frames), 'selected_quality':fr.quality_report(chosen),
                   'selected':[{'path':str(f.path), 't':f.t, 'sharpness':f.sharpness, 'brightness':f.brightness} for f in chosen],
                   'photo_quality':{p.name:fr.image_quality(p) for p in sorted(folder.glob('photo-*.jpg'))},
                   'extraction_seconds':round(time.monotonic()-start,2)}
            report['captures'].append(row);save(path,report)
            print('local',folder.name,'selected',len(chosen),flush=True)
        gallery = [(r['garment'], f['path']) for r in report['captures'] for f in r['selected']]
        A = embed([Path(p) for _, p in gallery])
        probes = [(folder.name,p) for folder in folders for p in sorted(folder.glob('photo-[12].jpg'))]
        B = embed([p for _,p in probes])
        for (garment, photo), scores in zip(probes, B@A.T):
            if any(r['photo'] == str(photo) for r in report['matching']):
                continue
            j = int(scores.argmax()); matched, image = gallery[j]
            # Production direction: seller reference -> received candidate. Here
            # reference=photo and candidate=video frame, same capture session only.
            result = align(photo,image)
            report['matching'].append({'garment':garment,'photo':str(photo),'matched_garment':matched,
                'matched_frame':image,'cosine':float(scores[j]),'correct_garment':garment == matched,
                'alignment_ok':bool(result.ok),'inliers':result.inliers,'inlier_ratio':result.inlier_ratio,
                'aligned_path':str(result.warped_path) if result.warped_path else None})
            save(path,report)
        report['metrics'] = {'source_hash_matches':rate(sum(r['matches_manifest'] for r in report['source_integrity']),len(manifest)),
            'selected_frames':sum(len(r['selected']) for r in report['captures']),
            'video_within_inline_limit':rate(sum(not r['video_over_inline_limit'] for r in report['captures']),len(folders)),
            'photo_to_video_top1':rate(sum(r['correct_garment'] for r in report['matching']),len(probes)),
            'matched_pair_alignment':rate(sum(r['alignment_ok'] for r in report['matching']),len(probes))}
        save(path,report)
        print(json.dumps(report['metrics'],indent=2),flush=True)
        return

    if config.STORE_KIND != 'local' or not __import__('os').getenv('FW_STORE_DIR'):
        raise SystemExit('Set an isolated local FW_STORE_DIR')
    import torch
    torch.set_num_threads(4)
    from fastapi.testclient import TestClient
    from fieldwork.api import app
    from fieldwork import gemini
    from fieldwork.store import store
    path=args.out/'live-report.json'
    report=json.loads(path.read_text()) if path.exists() else {
        'kind':'real_owner_annotated_seller_capture_evaluation', 'limits':LIMITS,
        'models':{'flash':config.MODEL_FLASH,'lite':config.MODEL_LITE},'cases':[]}
    complete={(r['garment'],r['track']) for r in report['cases']}
    with TestClient(app, raise_server_exceptions=False) as client:
        for track in ('photos','video'):
            for folder in folders:
                if (folder.name,track) in complete:continue
                row={'garment':folder.name,'track':track,'owner_reports_defect':folder.name in POSITIVE,
                     'reference_notes':(folder/'notes.txt').read_text(), 'code_expected':codes[folder.name]}
                start=time.monotonic()
                if track == 'video' and (folder/'take.mp4').stat().st_size > 20*1024*1024:
                    # Exercise the actual production guard without decoding the
                    # whole clip or making a doomed network call.
                    try:gemini.upload_video(folder/'take.mp4')
                    except ValueError as exc:row.update(status='blocked_by_production_video_guard',error=str(exc))
                    else:raise AssertionError('Video guard changed; update evaluation')
                else:
                    media = [('video',folder/'take.mp4')] if track=='video' else [('photos',p) for p in sorted(folder.glob('photo-*.jpg'))]
                    row['photo_count']=len(media) if track=='photos' else None
                    row['eligible_for_current_photo_ui']=len(media)>=3 if track=='photos' else None
                    print('start',folder.name,track,flush=True)
                    response=client.post('/take',data={'code':codes[folder.name]},
                        files=[(field,(p.name,p.read_bytes(),'video/mp4' if field=='video' else 'image/jpeg')) for field,p in media])
                    row['http']=response.status_code
                    if response.status_code==200:
                        row['record']=response.json();row['status']='completed'
                        item=row['record']['id']
                        row['listing']=client.get(f'/listings/{item}').json()
                        row['shown_defects']=[c for c in row['record']['claims'] if c['lane']=='shown' and c['severity']!='none']
                        row['store_item_dir']=str(store.item_dir(item))
                    else:row.update(status='failed',error=response.text[:250])
                row['seconds']=round(time.monotonic()-start,2)
                report['cases'].append(row);report['metrics']=photo_summary(report['cases']);save(path,report)
                print('done',folder.name,track,row['status'],row['seconds'],'defects',len(row.get('shown_defects',[])),flush=True)
    print(json.dumps(report['metrics'],indent=2),flush=True)


if __name__=='__main__':main()
