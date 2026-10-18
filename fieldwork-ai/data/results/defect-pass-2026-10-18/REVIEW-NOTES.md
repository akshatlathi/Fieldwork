# Visual review and decision

This compares the current seller overview inspector against a dedicated regional pass on the same 30 primary front/back photos. Both arms receive upright copies derived from the same originals. Original owner notes, hidden-defect descriptions and reference annotations are excluded from the prompts. The 14 primary label photos are outside this defect-focused experiment.

## What the evidence supports

All 15 baseline attempts and 30 regional attempts completed. The baseline produced five findings; the regional pass produced 18 definite proposals and 12 uncertain proposals. Owner-described defect-free garments with a definite finding increased from 1/10 to 4/10. This is a disagreement count, not an adjudicated false-positive rate. Original source hashes are unchanged, and resuming the completed experiment added no model calls. Thirty focused geometry/orientation/evidence tests pass.

Baseline cumulative wall time was 380.56 seconds versus 740.41 seconds for the regional arm (two calls per garment). Total logged input/output/thinking tokens were 89,431 versus 229,891, about 2.57 times as many. These are measured development-run totals, not dollar costs or production latency percentiles. All baseline calls and 29 regional calls used gemini-3.8-flash; garment-10 photo-2 used the configured gemini-3.7-flash fallback and produced no findings. That fallback is a model-control limitation; the important 01/02/03/05 cases used the same primary model. The three context checks use separate usage logs and are excluded from those arm totals.

| Case | Current overview | Regional pass | Review interpretation |
|---|---|---|---|
| 02 front hole | Found and localized | Found and localized | Both point to the small visible opening below the pocket. This is a useful regression anchor, not evidence of a new recall gain. |
| 03 hem marks | No defect reported | Brown specks/smudges localized on photo-2, plus other uncertain front candidates | Source-crop inspection shows brown spots near the back hem. This is a useful additional visible finding, consistent with the owner's general ankle-stain note. Image appearance alone does not establish the cause as mud. Other proposed stains remain unresolved. |
| 01 proposed extra hole | No hole reported | Called a vertical sequence beneath the graphic a hole | Inspected crop appears to follow lettering/pressed fabric texture. The model's subsequent full-photo/context check rejects it as not_supported. It should not become a shown hole claim. |
| 05 back dark spot | No hole reported | Proposed a small hole | The separate context check returns uncertain: pixels cannot establish a through-opening versus stain/lint. This is NOT confirmed as the owner's real hole, which the owner says is hidden by folds. |
| 06 reported hip hole | Not reported | Not reported as a hole | Owner says it is not properly visible. Do not count this as a demonstrated visible-defect miss or claim physically absent. The regional stain/snag proposals are separate, unconfirmed observations. |

The visual reviews above are development checks with prior exposure to earlier results, not independent human adjudication. `visual-review-reference.json` records the provisional garment-02 anchor and its provenance. Remaining per-image reference labels are explicitly pending in `review-reference.json`. A second model opinion is also not ground truth.

## Context check

After the regional pass produced a likely lettering-related false alarm, an additional experimental recheck was run on **every regional hole proposal**. It receives the full photograph and the source crop, without the original detector's explanatory note or owner condition labels. Its outputs are stored separately in `context-checks.json`, with usage under `context-logs/`.

This is a posthoc development test, not a preregistered third arm or independent validation. It illustrates a possible detector → contextual confirmation → human-review path. It does not justify an accuracy claim or automatic removal of a seller disclosure.

## Decision

**Keep this experimental; do not enable the raw regional pass for all seller listings yet.** It adds useful detail in 03, but also adds questionable proposals and changes severity descriptions. In particular, a definite-sounding detector label must not bypass context review. Proposed holes and stains must remain tied to their original source frame/box, and unresolved findings must stay uncertain.

The initial experiment bundles dedicated prompting, separate per-photo calls and overlapping crops. It therefore cannot identify which of those changes caused a difference. Before broad integration, annotate visible defect locations and clean review regions independently; test a context-confirmed regional candidate against the same baseline; measure both false alarms and missed visible issues. Use additional real visible holes for calibration and a separate final test set. The current 15 inspected garments cannot establish general hole accuracy.

For runtime, four tiles per photo are a diagnostic sweep, not a validated production sampling policy. A later experiment can test a bounded set of high-wear/uncertain regions, retaining overview context and evidence coordinates. Selection must be measured for misses: inspecting only suspicious regions can overlook defects elsewhere.

The condition-grade heads, pricing/search behavior, production seller pipeline and human-review/payment boundaries are unchanged. This experiment does not train or promote any model.

## Inspect the evidence

- [Side-by-side gallery](review.html) contains baseline and regional crops with model notes and statuses.
- [Results](REPORT.md) contains per-garment outputs and measured usage/latency.
- `report.json` retains raw baseline drafts, raw candidate responses, accepted/rejected/deduplicated boxes and successful-call logs.
- `manifest.json` freezes the 30 source hashes and the geometry of all derived views.

### Reproduce

From `fieldwork-ai/`, use the existing Vertex configuration and set `FW_LOG_DIR` to the result folder's `logs` directory. Run `python eval/defect_pass_experiment.py --out data/results/defect-pass-2026-10-18`. Saved attempts resume; frozen input/model/prompt mismatches are rejected. Generate the gallery using `python eval/defect_pass_review.py data/results/defect-pass-2026-10-18`.

For the separate posthoc check, set `FW_LOG_DIR` to this folder's `context-logs` directory and run `python eval/defect_context_check.py data/results/defect-pass-2026-10-18`. All model calls go through the normal Gemini wrapper. No API keys are stored in these files.
