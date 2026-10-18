# Defect evidence and garment-region matching — 18 October 2026

## Owner visibility clarification — 18 October 2026

The owner confirms that garment 05's real back hole and red stain are hidden by folds in the supplied photos/video. Garment 06's real hip hole is not properly visible. These three issues are **not established visible-defect false negatives** and must be excluded from visible-defect recall until adequate evidence is supplied. Physical presence remains owner-confirmed; lack of a detection does not establish absence. The model-proposed spot/hole on garment 05 is not confirmed as the actual hidden hole.

The earlier 4/5 owner-positive garment count describes coarse agreement with physical-condition notes, **not visible-defect recall or accuracy**. No revised visible-defect accuracy is claimed without visibility annotations for the remaining issues. These cases test coverage limitations and requests for unfolded close-ups. Broad claims such as “no holes” still need qualification when fabric is folded or obscured. Raw model outputs below are retained as historical observations. The owner annotation is in `fieldwork-ai/data/results/owner-visibility-2026-10-18.json`.

Completed software work:

- A seller video and supplementary photos now reach the same inspection. Previously photos sent with video were ignored. The seller page allows choosing both before submission; camera recording can also include selected photos.
- Capture guidance now suggests garment-specific detail views, including hips, pockets, crotch/inseams and hems for trousers. These are suggestions, not claims that the details are absent. Overview status still describes only front/back/label coverage.
- Gemini's existing record call can supply a garment silhouette on the first cited front/back frame. Invalid/degenerate outlines are discarded. Coordinates are never transplanted to another cited image.
- Reference keypoints and difference maps can be restricted to the garment silhouette, with uncertain boundary features excluded. Production inspections without usable outlines cannot conclude consistent from background alignment. Existing records need regeneration for outlines. SIFT comparisons remain provisional and every issue still goes to human review.
- Read-only Gemini generation now retries transient HTTP transport disconnections within its existing bounded retry budget. Agent/purchase retry behavior is unchanged.

## Selected development diagnostics

Six real reference views were selected after earlier failures. Gemini-generated masks were visually inspected for plausibility, not scored against independent segmentation ground truth. Controls use the same shared backgrounds and code cards; no final identity accuracy is claimed.

| Geometric acceptance | Unrestricted | Garment-focused |
|---|---:|---:|
| Same-garment top candidate | 5/6 | 3/6 |
| Different-garment control | 3/6 | 0/6 |

The method rejects misleading background matches but also abstains more on genuine pairs. This is not a blanket improvement in coverage or a final delivery benchmark. Only the top candidate was measured in this selected diagnostic; production can try up to three. Code cards, model mask errors and plain fabric remain limitations.

Four zoomed upper-garment photo checks were run without giving the visual inspector the owner's condition notes. Garment 05's back crop produced a possible hole candidate; the preview shows a localized dark/frayed spot, but the owner still needs to confirm its identity and location. The reported red hip stain remains unresolved. Garment 06's front crop returned no flaws; the back crop proposed a snag and scuff, not a confirmed hip hole. No proposals were automatically promoted into production records or scored as independently confirmed true defects. Cropping enlarges existing pixels; it is not new physical evidence.

A full live submission of garment 06's original video plus three original photos completed HTTP 200 in 37.14 seconds. All three supplemental photos were retained, and two valid garment masks were produced. The hip hole was still not reported. This establishes mixed-media integration, not improved defect recall.

## Validation and remaining input

113 focused/evaluation tests pass; the separately run legacy harness passed 12 checks. Frontend production build and TypeScript checks pass. The first diagnostic run hit a connection disconnect after three saved results; resuming reused those results and completed the remaining checks. No cloud deployment occurred.

The targeted follow-up packet is at `data/capture-kit/defect-followup/README.md`, with incomplete owner-annotation templates for 05 and 06. It requests exact side/location, contextual photos and close-ups. No captures or truth labels were invented. Separate received-session recordings are still required for final DINO/Gemini change and human-review evaluation.

Artifacts: `report.json`, `mixed-media-live.json`, `outline-review.jpg`, `zoom-candidate-review.jpg`, masks/previews and logs. Reproduce selected diagnostics with `python eval/defect_region_checks.py --out data/results/defect-regions-2026-10-18` using Vertex ADC and isolated logs; completed diagnostic calls resume from saved results. Restart the local backend to apply changes; regenerate older seller records before expecting garment outlines.
