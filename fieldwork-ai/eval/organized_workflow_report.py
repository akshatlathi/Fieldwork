"""Summarize organized_workflow output without inferring missing ground truth."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=Path)
    args = ap.parse_args()
    folder = args.folder.resolve()
    report = json.loads((folder/'report.json').read_text())
    rows = report['cases']
    inspections = [r['issue_report']['inspection'] for r in rows if r.get('issue_report', {}).get('inspection')]
    counts = Counter(r.get('issue_report', {}).get('suggested_assessment', 'not completed') for r in rows)
    comparison_counts = Counter(c['kind'] for i in inspections for c in i['comparisons'])
    finding_counts = Counter(f['kind'] for i in inspections for f in i['findings'])
    stages = [s for r in rows for s in r['stages']]
    passed = sum(r.get('workflow_passed', False) for r in rows)
    aligned = sum(i['pairs_aligned'] for i in inspections)
    refs = sum(len(r['issue_report']['listing']['capture']['frames']) for r in rows if r.get('issue_report', {}).get('inspection'))
    lines = ['# Existing 15-garment workflow regression', '',
             'Live local API run using the current models and workflow. Each original video is the seller capture; its original photos are submitted as buyer evidence. The run uses the 15 primary videos and 44 primary photos; four files in extras are integrity-checked only. These are same-session development checks, not independent received-garment recordings or a delivery-accuracy benchmark.', '',
             f'- Full workflow completed: **{passed}/{len(rows)}** garments.',
             f'- API status checks passed: **{sum(s["http"] == s["expected"] for s in stages)}/{len(stages)}** (includes expected 401/409 safeguards).',
             f'- Suggestions: **{counts["consistent"]} consistent, {counts["differs"]} differs, {counts["cant_tell"]} can’t tell**.',
             f'- Geometrically aligned views: **{aligned}/{refs}** retained listing references. Alignment is not identity or correctness accuracy.',
             f'- Saved comparison entries: {dict(comparison_counts)}.',
             f'- Findings: {dict(finding_counts)}.', '']
    if all('seconds' in r for r in rows):
        lines += [f'- Median complete-case time: **{statistics.median(r["seconds"] for r in rows):.1f}s**.', '']
    for name in ['source_integrity_before', 'source_integrity_after']:
        if name in report:
            checks = report[name]
            lines += [f'- {name}: **{sum(c["matches_manifest"] for c in checks)}/{len(checks)}** source hashes match the original manifest.']
    lines += ['', '## Per garment', '', '| Garment | Workflow | Code read | Front / back / label | Aligned / references | Suggestion | Seconds |',
              '|---|---|---|---|---|---|---:|']
    for r in rows:
        coverage = {v['region']: v['status'] for v in r.get('listing', {}).get('capture_coverage', {}).get('views', [])}
        issue = r.get('issue_report', {}); inspection = issue.get('inspection') or {}
        lines.append(f'| {r["garment"]} | {"pass" if r.get("workflow_passed") else "failed/incomplete"} | {r.get("initial_record", {}).get("capture", {}).get("code_seen", "—")} | {" / ".join(coverage.get(v, "—") for v in ["front", "back", "label"])} | {inspection.get("pairs_aligned", "—")} / {len(issue.get("listing", {}).get("capture", {}).get("frames", []))} | {issue.get("suggested_assessment", "—")} | {r.get("seconds", "—")} |')
    lines += ['', '## Seller observations and disclosures', '',
              'Model observations below are unadjudicated. Owner reports were entered by the test script from the existing notes and visibility correction; they do not count as model detections.', '',
              '| Garment | Initial model shown findings | Saved owner issues | Grade set (no reference grade) |',
              '|---|---|---|---|']
    for r in rows:
        rec = r.get('initial_record', {})
        observed = [c['code']+' / '+c['region'] for c in rec.get('claims', []) if c['lane'] == 'shown' and c['severity'] != 'none']
        disclosed = r.get('seller_review', {}).get('issues', [])
        lines.append(f'| {r["garment"]} | {", ".join(observed) or "none reported"} | {len(disclosed)} | {rec.get("grade_set", [])} |')
    lines += ['', '## Latency', '', '| Stage | Completed calls | Median seconds | Maximum seconds |', '|---|---:|---:|---:|']
    for name in ['seller_video', 'seller_disclosure', 'buyer_evidence_question', 'received_photos_inspection']:
        times = [s['seconds'] for s in stages if s['name'] == name and s['http'] == 200]
        if times:
            lines.append(f'| {name} | {len(times)} | {statistics.median(times):.2f} | {max(times):.2f} |')
    lines += ['', '## Comparison bottlenecks', '',
              f'- No aligned views: {sum(i["pairs_aligned"] == 0 for i in inspections)}/{len(inspections)} cases.',
              f'- Some listing views unaligned: {sum("Not all listing views were compared." in i["limitations"] for i in inspections)}/{len(inspections)} cases.',
              f'- Provisional SIFT fallback used: {sum(any("Fallback alignment" in t for t in i["limitations"]) for i in inspections)}/{len(inspections)} cases.',
              f'- Aligned view without usable garment outline: {sum(any("no usable garment outline" in t for t in i["limitations"]) for i in inspections)}/{len(inspections)} cases.',
              f'- Existing listed defect uncheckable: {sum(any("Listed " in t and "could not be checked" in t for t in i["limitations"]) for i in inspections)}/{len(inspections)} cases.',
              f'- At least one uncertain Gemini crop judgment: {sum(any(c.get("unsure") for c in i["comparisons"]) for i in inspections)}/{len(inspections)} cases.',
              '', 'Categories overlap. An outline is a model-generated localization aid, not independently labelled segmentation. Excluding background protects against shared-bed matches but also reduces available correspondence on plain fabric.']
    lines += ['', '## What this checks', '',
              'Seller video ingestion and saved draft; hidden and unpurchasable draft; owner-note disclosures in the declared lane; scripted explicit publication; listing/search; a nonvisual smell question; simulated purchase/All good release; received-photo pairing and inspection; persisted human report; held funds; blocked acceptance with an open issue; reviewer access control; human request for evidence with funds still held.', '',
              'All reviewer actions are scripted state checks. Reports remain in the isolated test store with needs_evidence status and held issue escrows. The existing active app store is not modified.', '',
              '## Limits and interpretation', '']
    lines += ['- '+limit for limit in report['limits']]
    lines += ['', 'No labels establish a new delivery defect, a missing original defect, or exact whole-garment condition grades. A differs suggestion needs crop inspection; it is not a proven delivery change. A can’t-tell suggestion is an abstention, not a failed API request. Stain/hole recall and grade accuracy are not calculated.', '',
              'The reported hidden 05 hole/red stain and unclear 06 hole remain seller declarations. An automatically detected spot is not proof that it is the owner’s particular hidden defect.', '',
              '## Detailed evidence', '', '`report.json` stores records, disclosures, listing coverage, complete reports/crop URLs and per-stage timings. `store/` retains the original copies, extracted frames, comparisons, mandates and review history. `logs/cost.jsonl` records successful Gemini calls and actual model IDs.', '']
    errors = [r for r in rows if r.get('error')]
    if errors:
        lines += ['## Failures', ''] + [f'- {r["garment"]}: {r["error"]}' for r in errors]
    if (folder/'REVIEW-NOTES.md').exists():
        lines += ['', '## Interpretation and next priorities', '', '[Review notes](REVIEW-NOTES.md) explain the observed weaknesses and recommended next work.']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines[:15]))


if __name__ == '__main__':
    main()
