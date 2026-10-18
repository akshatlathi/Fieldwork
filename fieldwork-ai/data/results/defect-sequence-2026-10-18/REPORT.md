# Context-confirmed defect sequence

Frozen existing 30-photo inputs: cached overview → cached regional proposals → new full-photo/crop contextual confirmation. Overview and regional evidence are unioned; overlapping same-code boxes are deduplicated without deleting provenance. No owner labels or detector explanations enter the confirmation prompt.

**Development diagnostic. Context-supported is a model opinion, not independent truth or a production shown claim.** No defect accuracy, clean-item guarantee, grade accuracy or delivery accuracy is calculated.

- Photos completed: 30/30.
- Unique proposals: 31; outcomes: {'supported': 17, 'uncertain': 12, 'not_supported': 2}.
- Posthoc conservative agreement policy: {'supported': 12, 'uncertain': 17, 'not_supported': 2}. Detector-uncertain proposals stay uncertain even when context supports them.
- New context calls: 15; errors: 4.
- Added context wall time: 1034.65 seconds; logged input/output/thinking tokens: 58620.
- Actual context models: {'gemini-3.8-flash': 15}.

| Garment | Overview findings | Regional definite / uncertain | Union proposals | Supported | Rejected | Uncertain |
|---|---:|---:|---:|---:|---:|---:|
| garment-01 | 2 | 4 / 1 | 5 | 2 | 1 | 2 |
| garment-02 | 1 | 1 / 0 | 1 | 1 | 0 | 0 |
| garment-03 | 0 | 2 / 3 | 5 | 3 | 0 | 2 |
| garment-04 | 0 | 0 / 0 | 0 | 0 | 0 | 0 |
| garment-05 | 1 | 3 / 0 | 4 | 4 | 0 | 0 |
| garment-06 | 0 | 1 / 1 | 2 | 2 | 0 | 0 |
| garment-07 | 0 | 1 / 1 | 2 | 1 | 0 | 1 |
| garment-08 | 1 | 4 / 1 | 5 | 1 | 0 | 4 |
| garment-09 | 0 | 1 / 1 | 2 | 1 | 1 | 0 |
| garment-10 | 0 | 0 / 1 | 1 | 1 | 0 | 0 |
| garment-11 | 0 | 1 / 1 | 2 | 1 | 0 | 1 |
| garment-12 | 0 | 0 / 2 | 2 | 0 | 0 | 2 |
| garment-13 | 0 | 0 / 0 | 0 | 0 | 0 | 0 |
| garment-14 | 0 | 0 / 0 | 0 | 0 | 0 | 0 |
| garment-15 | 0 | 0 / 0 | 0 | 0 | 0 | 0 |

## Limits

- Detection stages are cached; this isolates incremental confirmation. The old three-hole-only checks are not reused because this prompt evaluates all defect types uniformly.
- Both definite and uncertain proposals are checked. An uncertain proposal may become context-supported, but this is not independent visual validation.
- No-proposal photos skip a context model call; that does not establish no defects. A confirmation stage cannot recover a defect neither detector proposed.
- Missing/duplicate candidate IDs or failed calls leave proposals uncertain; no failure can create a supported finding.
- The same model can repeat an earlier mistake or reject a real defect. No independent precision/recall comparison is available.
- The conservative agreement policy is a posthoc analysis added after seeing context support detector-uncertain findings. It is not a preregistered arm or independent accuracy result.
- Hidden 05 hole/red stain and unclear 06 hole remain excluded from established visible-positive metrics. Seller disclosures are not changed.
- Inputs were already inspected in development. The earlier regional stage used one configured fallback on garment-10 photo-2, which had no proposals.
- Upstream time/token totals are historical stage measurements; adding them estimates sequential stage cost, not a newly measured end-to-end app latency.

`report.json` retains upstream snapshots, candidate provenance, all new raw decisions, errors and successful-call usage. `manifest.json` freezes input hashes and the context prompt. `crops/` retains context evidence.

[Visual review and interpretation](REVIEW-NOTES.md)

[Evidence gallery](review.html)

Original source hashes unchanged: True.
