"""Frozen same-input overview vs regional inspection; no production changes.

Use Vertex env and isolated FW_LOG_DIR. Original owner notes never enter prompts.
Run: python eval/defect_pass_experiment.py --out data/results/defect-pass-2026-10-18
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.regional_defects import SYSTEM, inspect, prepare_views
from fieldwork import config
from fieldwork.take.record import SYSTEM as BASE_SYSTEM, draft_record, to_claims


def save(path, data):
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(data, indent=2)); temp.replace(path)


def summarize(report, out):
    rows = report['cases']
    lines = ['# Seller defect-pass experiment', '',
             'Same 30 original front/back photographs, grouped by 15 garments. Baseline: current seller draft_record on each two-photo group. Candidate: dedicated per-photo inspection with overview plus four fixed overlapping tiles. Owner notes are not passed to either arm. No active app records or models are changed.', '',
             '**Development diagnostic, not a defect-accuracy benchmark.** Visible-in-image reference boxes, defect-free region labels and independent adjudication are incomplete. Findings below are proposals, not confirmed true defects. Candidate changes prompt, context, number of calls and image crops together; it does not isolate cropping alone.', '',
             '| Garment | Baseline findings | Regional definite proposals | Regional uncertain proposals | Rejected boxes |',
             '|---|---|---|---|---|']
    def counts(items):
        return ', '.join(f'{k}: {v}' for k, v in sorted(Counter(f['code'] for f in items).items())) or 'none'
    for row in rows:
        candidate = [f for p in row['photos'] for f in p.get('candidate', {}).get('findings', [])]
        definite = [f for f in candidate if f['status'] == 'visible_defect']
        uncertain = [f for f in candidate if f['status'] == 'uncertain']
        baseline = row.get('baseline', {}).get('findings', [])
        rejected = sum(len(p.get('candidate', {}).get('rejected', [])) for p in row['photos'])
        lines.append(f'| {row["garment"]} | {counts(baseline) if "baseline" in row else "pending/error"} | {counts(definite)} | {counts(uncertain)} | {rejected} |')
    lines += ['', '## Runtime and usage', '']
    for arm in ['baseline', 'candidate']:
        entries = ([r[arm] for r in rows if arm in r] if arm == 'baseline' else
                   [p[arm] for r in rows for p in r['photos'] if arm in p])
        calls = [c for entry in entries for c in entry.get('calls', [])]
        tokens = sum((c.get('in_tokens') or 0)+(c.get('out_tokens') or 0)+(c.get('thinking_tokens') or 0) for c in calls)
        lines += [f'- {arm}: {len(entries)} saved attempts; {sum("error" not in e for e in entries)} completed; '
                  f'{sum(e.get("seconds", 0) for e in entries):.2f}s cumulative wall time; '
                  f'{len(calls)} successful logged calls; {tokens} total logged input/output/thinking tokens.']
        lines += [f'  Actual successful models: {dict(Counter(c["model"] for c in calls))}.']
    if 'source_hashes_unchanged' in report:
        lines += [f'- Original source hashes unchanged: {report["source_hashes_unchanged"]}.']
    lines += ['', '## Interpretation', '',
              '- More proposals do not establish better recall. Review localization and false alarms before promotion.',
              '- No visible-defect recall, precision, IoU accuracy or grade accuracy is computed from owner-level notes alone.',
              '- The hidden 05 hole/red stain and unclear 06 hole are excluded from established visible-positive counts.',
              '- A no-finding result is not evidence that all physical defects are absent.',
              '- These garments were inspected in earlier development runs; this is not a held-out test.', '',
              '`manifest.json` freezes original hashes and derived-view geometry. `report.json` retains raw responses, mapped boxes, errors, timings and per-attempt successful-call logs. `review-reference.json` keeps owner notes and pending independent annotations separate from prompts. `crops/` contains source-pixel tiles and `evidence/` contains each proposed finding crop.', '']
    if (out/'REVIEW-NOTES.md').exists():
        lines += ['[Visual review and decision](REVIEW-NOTES.md)', '']
    (out/'REPORT.md').write_text('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=Path('data/organized-garments'))
    args = ap.parse_args(); out = args.out.resolve(); root = args.root.resolve()
    if config.LOG_DIR.resolve() != out/'logs':
        raise SystemExit('Set FW_LOG_DIR to <out>/logs for isolated experiment usage')
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'protocol': 'overview-vs-regional-v1', 'requested_model': config.MODEL_FLASH,
                'prompt_sha256': hashlib.sha256((BASE_SYSTEM+'\n'+SYSTEM).encode()).hexdigest(), 'images': []}
    for folder in sorted(root.glob('garment-*')):
        for source in sorted(folder.glob('photo-[12].jpg')):
            manifest['images'].append({'garment': folder.name, 'photo': source.name, 'source': str(source),
                'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    assert len(manifest['images']) == 30, 'Expected fixed 15 front/back photo pairs'
    manifest_path = out/'manifest.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        frozen_sources = {**previous, 'images': [{k: v for k, v in i.items() if k != 'views'} for i in previous['images']]}
        assert frozen_sources == manifest, 'Frozen inputs/model/prompt changed'
        manifest = previous
    else:
        for image in manifest['images']:
            image['views'] = prepare_views(Path(image['source']), out/'crops'/image['garment']/Path(image['photo']).stem)
        save(manifest_path, manifest)
    # Compare only source fields on resume; view metadata is derived, never a new input.
    report_path = out/'report.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {
        'kind': 'same_image_defect_pass_development', 'accuracy_benchmark': False, 'cases': []}
    if not (out/'review-reference.json').exists():
        save(out/'review-reference.json', {
            'annotation_status': 'pending independent per-image visibility, boxes and negative-region review',
            'not_model_input': True,
            'owner_visibility': json.loads((config.ROOT/'data/results/owner-visibility-2026-10-18.json').read_text()),
            'garments': [{'id': g, 'owner_notes': (root/g/'notes.txt').read_text(),
                          'per_image_truth': [{'photo': i['photo'], 'visible_defects': None, 'reviewer': None}
                                              for i in manifest['images'] if i['garment'] == g]}
                         for g in sorted({i['garment'] for i in manifest['images']})]})
    log = config.LOG_DIR/'cost.jsonl'
    def run(fn):
        offset = log.stat().st_size if log.exists() else 0
        started = time.monotonic()
        try:
            result = fn()
        except Exception as exc:
            result = {'error': f'{type(exc).__name__}: {exc}'[:600]}
        result['seconds'] = round(time.monotonic()-started, 2)
        if log.exists():
            with log.open('rb') as stream:
                stream.seek(offset)
                result['calls'] = [json.loads(line) for line in stream if line.strip()]
        return result
    def persist():
        save(report_path, report); summarize(report, out)
    for garment in sorted({i['garment'] for i in manifest['images']}):
        row = next((r for r in report['cases'] if r['garment'] == garment), None)
        if row is None:
            images = [i for i in manifest['images'] if i['garment'] == garment]
            row = {'garment': garment, 'photos': images}; report['cases'].append(row)
        if 'baseline' not in row:
            def baseline():
                draft = draft_record(None, [(p['photo'], Path(p['views'][0]['path'])) for p in row['photos']])
                claims = to_claims(draft, {p['photo'] for p in row['photos']})
                findings = [c.model_dump(mode='json') for c in claims if c.lane == 'shown' and c.severity != 'none']
                return {'draft': draft.model_dump(mode='json'), 'findings': findings}
            row['baseline'] = run(baseline); persist()
            print(garment, 'baseline', row['baseline'].get('error', len(row['baseline'].get('findings', []))), flush=True)
        for photo in row['photos']:
            if 'candidate' in photo:
                continue
            photo['candidate'] = run(lambda: inspect(photo['views'])); persist()
            print(garment, photo['photo'], 'regional', photo['candidate'].get('error',
                  [(f['code'], f['status']) for f in photo['candidate'].get('findings', [])]), flush=True)
    report['source_hashes_unchanged'] = all(hashlib.sha256(Path(i['source']).read_bytes()).hexdigest() == i['sha256'] for i in manifest['images'])
    # Produce tight source crops for visual review, never an edited source image.
    from PIL import Image
    for row in report['cases']:
        for photo in row['photos']:
            with Image.open(photo['views'][0]['path']) as im:
                w, h = im.size
                for n, f in enumerate(photo.get('candidate', {}).get('findings', [])):
                    y0, x0, y1, x1 = f['source_box_2d']
                    path = out/'evidence'/row['garment']/f'{Path(photo["photo"]).stem}-{n}-{f["code"]}.jpg'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    im.crop((int(x0*w/1000), int(y0*h/1000), max(int(x0*w/1000)+1, round(x1*w/1000)),
                             max(int(y0*h/1000)+1, round(y1*h/1000)))).save(path, quality=95)
                    f['evidence_crop'] = str(path)
    persist()
    print('FINISHED', len(report['cases']), 'garments; originals unchanged:', report['source_hashes_unchanged'], flush=True)


if __name__ == '__main__':
    main()
