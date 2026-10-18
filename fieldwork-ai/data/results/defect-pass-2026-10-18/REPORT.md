# Seller defect-pass experiment

Same 30 original front/back photographs, grouped by 15 garments. Baseline: current seller draft_record on each two-photo group. Candidate: dedicated per-photo inspection with overview plus four fixed overlapping tiles. Owner notes are not passed to either arm. No active app records or models are changed.

**Development diagnostic, not a defect-accuracy benchmark.** Visible-in-image reference boxes, defect-free region labels and independent adjudication are incomplete. Findings below are proposals, not confirmed true defects. Candidate changes prompt, context, number of calls and image crops together; it does not isolate cropping alone.

| Garment | Baseline findings | Regional definite proposals | Regional uncertain proposals | Rejected boxes |
|---|---|---|---|---|
| garment-01 | discolour: 1, loose_seam: 1 | discolour: 2, hole: 1, loose_seam: 1 | loose_seam: 1 | 0 |
| garment-02 | hole: 1 | hole: 1 | none | 0 |
| garment-03 | none | stain: 2 | stain: 3 | 0 |
| garment-04 | none | none | none | 0 |
| garment-05 | stain: 1 | hole: 1, stain: 2 | none | 0 |
| garment-06 | none | stain: 1 | snag: 1 | 0 |
| garment-07 | none | discolour: 1 | discolour: 1 | 0 |
| garment-08 | discolour: 1 | discolour: 3, stain: 1 | stain: 1 | 0 |
| garment-09 | none | stain: 1 | snag: 1 | 0 |
| garment-10 | none | none | stain: 1 | 0 |
| garment-11 | none | stain: 1 | stain: 1 | 0 |
| garment-12 | none | none | other: 1, stain: 1 | 0 |
| garment-13 | none | none | none | 0 |
| garment-14 | none | none | none | 0 |
| garment-15 | none | none | none | 0 |

## Runtime and usage

- baseline: 15 saved attempts; 15 completed; 380.56s cumulative wall time; 15 successful logged calls; 89431 total logged input/output/thinking tokens.
  Actual successful models: {'gemini-3.8-flash': 15}.
- candidate: 30 saved attempts; 30 completed; 740.41s cumulative wall time; 30 successful logged calls; 229891 total logged input/output/thinking tokens.
  Actual successful models: {'gemini-3.8-flash': 29, 'gemini-3.7-flash': 1}.
- Original source hashes unchanged: True.

## Interpretation

- More proposals do not establish better recall. Review localization and false alarms before promotion.
- No visible-defect recall, precision, IoU accuracy or grade accuracy is computed from owner-level notes alone.
- The hidden 05 hole/red stain and unclear 06 hole are excluded from established visible-positive counts.
- A no-finding result is not evidence that all physical defects are absent.
- These garments were inspected in earlier development runs; this is not a held-out test.

`manifest.json` freezes original hashes and derived-view geometry. `report.json` retains raw responses, mapped boxes, errors, timings and per-attempt successful-call logs. `review-reference.json` keeps owner notes and pending independent annotations separate from prompts. `crops/` contains source-pixel tiles and `evidence/` contains each proposed finding crop.

[Visual review and decision](REVIEW-NOTES.md)
