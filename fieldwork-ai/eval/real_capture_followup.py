"""Posthoc diagnostics after the real-capture EXIF-coordinate failure.

Retains baseline reports. These selected checks are not held-out accuracy results.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fieldwork import ask, gemini
from fieldwork.spec import Box, ConditionRecord
from fieldwork.stats import rate


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--results',type=Path,required=True)
    args=ap.parse_args();out=args.results.resolve()
    baseline=json.loads((out/'live-report.json').read_text())
    rows={r['garment']:r for r in baseline['cases'] if r['track']=='photos' and r.get('record')}
    report={'kind':'posthoc_orientation_and_question_diagnostics',
        'limits':['Selected after baseline errors; not unbiased accuracy estimates.',
                  'Answer states are checked separately from semantic correctness.',
                  'Owner-reported defects may need close-ups before adjudicating visibility.'],
        'questions':[]}
    def save(): (out/'followup-report.json').write_text(json.dumps(report,indent=2))
    for garment,question,expected in [
        ('garment-02','What visible hole is recorded on the front?','shown'),
        ('garment-04','Can you establish whether this fabric feels soft against skin?','cant_judge'),
        ('garment-09','What exact size is printed on the size label?','not_in_take'),
        ('garment-06','Are there any holes? Please state the limitations of the evidence.',None)]:
        start=time.monotonic();row={'garment':garment,'question':question,'expected_state':expected}
        try:row['answer']=ask.ask(ConditionRecord(**rows[garment]['record']),question).model_dump()
        except Exception as exc:row['error']=f'{type(exc).__name__}: {exc}'[:250]
        row['seconds']=round(time.monotonic()-start,2);report['questions'].append(row);save()
        print(garment,row,flush=True)
    # A concrete coordinate check on the garment whose old collar box hit a sleeve.
    start=time.monotonic();source=Path(rows['garment-08']['store_item_dir'])/'p1.jpg'
    box=gemini.generate('orientation_collar_diagnostic',[
        'frame_id: p1',gemini.image_part(source),
        'Locate the striped collar, including its neck opening, in frame p1. Return its tight normalized box [ymin,xmin,ymax,xmax] in 0–1000.'],
        schema=Box,system='Locate only the requested visible garment region.',temperature=0)
    from PIL import Image
    # Show exactly the upright bytes submitted to Gemini, with its returned box.
    with Image.open(BytesIO(gemini.image_part(source).inline_data.data)) as im:
        w,h=im.size;y0,x0,y1,x1=box.box_2d
        crop=im.crop((int(x0*w/1000),int(y0*h/1000),int(x1*w/1000),int(y1*h/1000)))
        crop.save(out/'orientation-fixed-collar.jpg')
    report['orientation_collar']={'box':box.model_dump(),'seconds':round(time.monotonic()-start,2),
        'crop':str(out/'orientation-fixed-collar.jpg'),'visual_review':'pending'}
    save()
    import torch
    from fieldwork.take.grade import embed
    torch.set_num_threads(4)
    local=json.loads((out/'local-report.json').read_text())
    gallery=[(r['garment'],Path(f['path'])) for r in local['captures'] for f in r['selected']]
    probes=[(r['garment'],Path(r['photo'])) for r in local['matching']]
    A=embed([p for _,p in gallery]);B=embed([p for _,p in probes])
    matches=[]
    for (garment,photo),scores in zip(probes,B@A.T):
        j=int(scores.argmax());matched,image=gallery[j]
        matches.append({'garment':garment,'photo':str(photo),'matched_garment':matched,
            'matched_frame':str(image),'cosine':float(scores[j]),'correct_garment':garment==matched})
    report['matching_after_orientation_fix']=matches
    report['matching_top1']=rate(sum(r['correct_garment'] for r in matches),len(matches))
    save();print(json.dumps(report['matching_top1'],indent=2),flush=True)


if __name__=='__main__':main()
