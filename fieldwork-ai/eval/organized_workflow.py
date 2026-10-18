"""Live API regression on existing seller captures, NOT delivery accuracy.

Seller video -> draft/disclosure/publication -> buyer original photos -> review.
The photos are from the same session, not independently captured received goods.
Use isolated FW_STORE_DIR/FW_LOG_DIR; incremental reports support resume.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if not os.getenv('FW_STORE_DIR') or not os.getenv('FW_REVIEW_TOKEN') or os.getenv('FW_STORE', 'local') != 'local':
        raise SystemExit('Require isolated local FW_STORE_DIR and FW_REVIEW_TOKEN')
    if Path(os.environ['FW_STORE_DIR']).resolve() != out / 'store':
        raise SystemExit('FW_STORE_DIR must be <out>/store')
    import torch
    torch.set_num_threads(4)
    from fastapi.testclient import TestClient
    from fieldwork.api import app
    from fieldwork import config
    from fieldwork.store import store
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'report.json'
    report = json.loads(path.read_text()) if path.exists() else {
        'kind': 'same_session_full_workflow_regression', 'accuracy_benchmark': False,
        'limits': ['Seller videos and buyer photos are from the same original capture session.',
                   'No delivery changes, independent received session, or grade truth are supplied.',
                   'Assessment counts are diagnostics; no change recall or delivery accuracy is computed.',
                   'Scripted approvals and reviewer decisions test state transitions, not human judgment.',
                   'Garment 05 hidden hole/red stain and 06 unclear hole are not established visible-defect misses.',
                   'Inspected development data; browser UI and agent chats are not exercised.'],
        'models': {'flash': config.MODEL_FLASH, 'lite': config.MODEL_LITE, 'dino': config.DINO_MODEL},
        'cases': []}
    manifest = list(csv.DictReader((root/'file-manifest.csv').open(encoding='utf-8-sig')))
    codes = {'garment-'+r['garment']: r['code'] for r in manifest}
    # Owner notes, independent of model output; exact missing locations stay unknown.
    issues = {
        'garment-01': [('other', 'whole', 'Owner reports a defect near left shoulder; type and exact size unresolved.')],
        'garment-02': [('hole', 'front', 'Owner reports a visible hole on front below pocket; exact size unresolved.')],
        'garment-03': [('stain', 'hem', 'Owner reports mud stains near ankle; exact side and dimensions unresolved.')],
        'garment-05': [('other', 'front', 'Owner reports dark marks/spots on front; cause unresolved.'),
                       ('hole', 'back', 'Owner reports back hole hidden by folds in original media; not visually established.'),
                       ('stain', 'whole', 'Owner reports red hip stain hidden by folds; exact side unresolved; not visually established.')],
        'garment-06': [('hole', 'whole', 'Owner reports hip hole not properly visible in original media; exact side/front/back unresolved.')]}

    def hashes():
        return [{'path': r['organized_path'].replace('\\', '/'),
                 'matches_manifest': hashlib.sha256((root/r['organized_path'].replace('\\', '/')).read_bytes()).hexdigest() == r['sha256']}
                for r in manifest]

    def save():
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(report, indent=2)); tmp.replace(path)

    report['source_integrity_before'] = hashes(); save()
    with TestClient(app, raise_server_exceptions=False) as client:
        for folder in sorted(root.glob('garment-*')):
            if not folder.is_dir() or any(r['garment'] == folder.name for r in report['cases']):
                continue
            row = {'garment': folder.name, 'stages': [], 'reference_notes': (folder/'notes.txt').read_text()}
            report['cases'].append(row); save()
            start_case = time.monotonic()

            def call(name, method, route, expected=200, **kwargs):
                start = time.monotonic()
                response = getattr(client, method)(route, **kwargs)
                stage = {'name': name, 'http': response.status_code, 'expected': expected,
                         'seconds': round(time.monotonic()-start, 2)}
                row['stages'].append(stage); save()
                print(folder.name, name, response.status_code, stage['seconds'], flush=True)
                assert response.status_code == expected, f'{name}: {response.text[:500]}'
                return response.json()

            try:
                video = folder/'take.mp4'
                rec = call('seller_video', 'post', '/take', data={'code': codes[folder.name]},
                           files={'video': (video.name, video.read_bytes(), 'video/mp4')})
                item = row['item_id'] = rec['id']; row['initial_record'] = rec
                draft = call('seller_review', 'get', f'/seller/drafts/{item}')
                assert item not in json.dumps(call('draft_hidden', 'get', '/search'))
                purchase = {'item_id': item, 'payer': 'regression-buyer', 'payee': 'regression-seller',
                            'amount': 1500, 'currency': 'INR'}
                call('draft_purchase_blocked', 'post', '/escrow', expected=409, json=purchase)
                disclosed = [{'code': c, 'region': r, 'description': d} for c, r, d in issues.get(folder.name, [])]
                draft = call('seller_disclosure', 'post', f'/seller/drafts/{item}/declarations', json={
                    'revision': draft['revision'], 'answer': 'issues_reported' if disclosed else 'none_known', 'issues': disclosed})
                assert len([c for c in draft['record']['claims'] if c['id'].startswith('seller_issue_') and c['lane'] == 'declared']) == len(disclosed)
                row['seller_review'] = draft
                draft = call('seller_price', 'post', f'/seller/drafts/{item}/price', json={
                    'revision': draft['revision'], 'asking_price': 1500, 'currency': 'INR'})  # explicit test actor
                call('scripted_publication', 'post', f'/seller/drafts/{item}/publish', json={
                    'revision': draft['revision'], 'acknowledge_limitations': True})
                row['listing'] = call('published_listing', 'get', f'/listings/{item}')
                assert item in json.dumps(call('buyer_search', 'get', '/search'))
                row['answer'] = call('buyer_evidence_question', 'post', '/ask', json={
                    'item_id': item, 'question': 'Can you establish how this garment smells from these captures?'})
                assert row['answer']['state'] == 'cant_judge'
                accept_item = item + '_accept_control'
                control_record = store.get_json('records', item); control_record['id'] = accept_item
                control_listing = store.get_json('listings', item); control_listing['id'] = accept_item
                store.put_json('records', accept_item, control_record)
                store.put_json('listings', accept_item, control_listing)
                accepted = call('purchase_accept_branch', 'post', '/escrow', json={**purchase, 'item_id': accept_item})
                assert call('explicit_all_good', 'post', f"/escrow/{accepted['id']}/accept")['status'] == 'released'
                held = call('purchase_issue_branch', 'post', '/escrow', json=purchase)
                row['mandate_id'] = held['id']
                photos = sorted(folder.glob('photo-*.jpg'))
                issue = call('received_photos_inspection', 'post', '/issues',
                    data={'item_id': item, 'mandate_id': held['id'],
                          'buyer_text': 'Development regression using original same-session photos; no new damage is asserted.'},
                    files=[('photos', (p.name, p.read_bytes(), 'image/jpeg')) for p in photos])
                row['issue_report'] = issue
                assert issue['status'] == 'awaiting_review' and issue['inspection'] is not None
                assert call('funds_held', 'get', f"/escrow/{held['id']}")['status'] == 'held'
                call('accept_blocked_while_issue_open', 'post', f"/escrow/{held['id']}/accept", expected=409)
                call('reviewer_access_protected', 'get', '/review', expected=401)
                auth = {'Authorization': 'Bearer '+os.environ['FW_REVIEW_TOKEN']}
                assert issue['id'] in json.dumps(call('human_review_queue', 'get', '/review', headers=auth))
                decision = call('human_requests_evidence', 'post', f"/issues/{issue['id']}/decision", headers=auth,
                    json={'action': 'request_evidence', 'reviewer': 'regression-state-check',
                          'note': 'Scripted transition check. Independent received capture still needed.'})
                assert decision['status'] == 'needs_evidence'
                assert call('funds_still_held', 'get', f"/escrow/{held['id']}")['status'] == 'held'
                # All reports remain inspectable and held; no fabricated human assessment.
                row['workflow_passed'] = True
            except Exception as exc:
                row.update(workflow_passed=False, error=f'{type(exc).__name__}: {exc}'[:800])
            finally:
                row['seconds'] = round(time.monotonic()-start_case, 2); save()
                print('DONE', folder.name, row.get('workflow_passed'), row.get('error', ''), flush=True)
    report['source_integrity_after'] = hashes()
    report['summary'] = {'cases': len(report['cases']), 'workflow_passed': sum(r.get('workflow_passed', False) for r in report['cases']),
                         'assessment_counts': {a: sum(r.get('issue_report', {}).get('suggested_assessment') == a for r in report['cases']) for a in ['consistent', 'differs', 'cant_tell']}}
    save(); print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
