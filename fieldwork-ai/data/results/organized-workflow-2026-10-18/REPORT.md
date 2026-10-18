# Existing 15-garment workflow regression

Live local API run using the current models and workflow. Each original video is the seller capture; its original photos are submitted as buyer evidence. The run uses the 15 primary videos and 44 primary photos; four files in extras are integrity-checked only. These are same-session development checks, not independent received-garment recordings or a delivery-accuracy benchmark.

- Full workflow completed: **15/15** garments.
- API status checks passed: **285/285** (includes expected 401/409 safeguards).
- Suggestions: **0 consistent, 0 differs, 15 can’t tell**.
- Geometrically aligned views: **15/33** retained listing references. Alignment is not identity or correctness accuracy.
- Saved comparison entries: {'aligned_view': 15, 'candidate_change': 24, 'existing_flaw': 2}.
- Findings: {}.

- Median complete-case time: **53.8s**.

- source_integrity_before: **63/63** source hashes match the original manifest.
- source_integrity_after: **63/63** source hashes match the original manifest.

## Per garment

| Garment | Workflow | Code read | Front / back / label | Aligned / references | Suggestion | Seconds |
|---|---|---|---|---|---|---:|
| garment-01 | pass | True | shown / shown / not_shown | 0 / 2 | cant_tell | 46.68 |
| garment-02 | pass | True | shown / shown / not_shown | 0 / 3 | cant_tell | 45.67 |
| garment-03 | pass | True | shown / shown / not_shown | 0 / 2 | cant_tell | 43.31 |
| garment-04 | pass | True | shown / shown / unclear | 1 / 2 | cant_tell | 62.08 |
| garment-05 | pass | True | shown / shown / not_shown | 0 / 3 | cant_tell | 31.25 |
| garment-06 | pass | True | shown / shown / unclear | 2 / 2 | cant_tell | 53.8 |
| garment-07 | pass | False | shown / shown / unclear | 0 / 2 | cant_tell | 40.51 |
| garment-08 | pass | True | shown / shown / not_shown | 1 / 2 | cant_tell | 137.35 |
| garment-09 | pass | True | shown / shown / not_shown | 3 / 3 | cant_tell | 135.17 |
| garment-10 | pass | True | shown / shown / unclear | 0 / 2 | cant_tell | 37.03 |
| garment-11 | pass | False | shown / shown / not_shown | 1 / 2 | cant_tell | 94.14 |
| garment-12 | pass | True | shown / shown / unclear | 2 / 2 | cant_tell | 56.52 |
| garment-13 | pass | True | shown / shown / unclear | 2 / 2 | cant_tell | 36.17 |
| garment-14 | pass | False | shown / shown / unclear | 2 / 2 | cant_tell | 60.69 |
| garment-15 | pass | False | shown / shown / unclear | 1 / 2 | cant_tell | 76.48 |

## Seller observations and disclosures

Model observations below are unadjudicated. Owner reports were entered by the test script from the existing notes and visibility correction; they do not count as model detections.

| Garment | Initial model shown findings | Saved owner issues | Grade set (no reference grade) |
|---|---|---|---|
| garment-01 | discolour / front | 1 | [2, 3, 4, 5] |
| garment-02 | hole / front | 1 | [2, 3, 4, 5] |
| garment-03 | none reported | 1 | [2, 3, 4, 5] |
| garment-04 | none reported | 0 | [2, 3, 4, 5] |
| garment-05 | stain / front, stain / front | 3 | [2, 3, 5] |
| garment-06 | none reported | 1 | [2, 3, 4, 5] |
| garment-07 | none reported | 0 | [2, 3, 4, 5] |
| garment-08 | none reported | 0 | [2, 3, 4, 5] |
| garment-09 | stain / back, stain / front | 0 | [2, 3, 4, 5] |
| garment-10 | none reported | 0 | [2, 4, 5] |
| garment-11 | none reported | 0 | [2, 3, 4, 5] |
| garment-12 | none reported | 0 | [2, 3, 4, 5] |
| garment-13 | none reported | 0 | [2, 3, 4, 5] |
| garment-14 | none reported | 0 | [2, 3, 4, 5] |
| garment-15 | none reported | 0 | [2, 3, 4, 5] |

## Latency

| Stage | Completed calls | Median seconds | Maximum seconds |
|---|---:|---:|---:|
| seller_video | 15 | 33.21 | 82.40 |
| seller_disclosure | 15 | 2.02 | 3.95 |
| buyer_evidence_question | 15 | 3.45 | 6.11 |
| received_photos_inspection | 15 | 7.48 | 102.38 |

## Comparison bottlenecks

- No aligned views: 6/15 cases.
- Some listing views unaligned: 10/15 cases.
- Provisional SIFT fallback used: 1/15 cases.
- Aligned view without usable garment outline: 1/15 cases.
- Existing listed defect uncheckable: 3/15 cases.
- At least one uncertain Gemini crop judgment: 5/15 cases.

Categories overlap. An outline is a model-generated localization aid, not independently labelled segmentation. Excluding background protects against shared-bed matches but also reduces available correspondence on plain fabric.

## What this checks

Seller video ingestion and saved draft; hidden and unpurchasable draft; owner-note disclosures in the declared lane; scripted explicit publication; listing/search; a nonvisual smell question; simulated purchase/All good release; received-photo pairing and inspection; persisted human report; held funds; blocked acceptance with an open issue; reviewer access control; human request for evidence with funds still held.

All reviewer actions are scripted state checks. Reports remain in the isolated test store with needs_evidence status and held issue escrows. The existing active app store is not modified.

## Limits and interpretation

- Seller videos and buyer photos are from the same original capture session.
- No delivery changes, independent received session, or grade truth are supplied.
- Assessment counts are diagnostics; no change recall or delivery accuracy is computed.
- Scripted approvals and reviewer decisions test state transitions, not human judgment.
- Garment 05 hidden hole/red stain and 06 unclear hole are not established visible-defect misses.
- Inspected development data; browser UI and agent chats are not exercised.

No labels establish a new delivery defect, a missing original defect, or exact whole-garment condition grades. A differs suggestion needs crop inspection; it is not a proven delivery change. A can’t-tell suggestion is an abstention, not a failed API request. Stain/hole recall and grade accuracy are not calculated.

The reported hidden 05 hole/red stain and unclear 06 hole remain seller declarations. An automatically detected spot is not proof that it is the owner’s particular hidden defect.

## Detailed evidence

`report.json` stores records, disclosures, listing coverage, complete reports/crop URLs and per-stage timings. `store/` retains the original copies, extracted frames, comparisons, mandates and review history. `logs/cost.jsonl` records successful Gemini calls and actual model IDs.


## Interpretation and next priorities

[Review notes](REVIEW-NOTES.md) explain the observed weaknesses and recommended next work.
