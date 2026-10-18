# Workflow priorities implemented — 18 October 2026

## Owner visibility clarification — 18 October 2026

The owner confirms that garment 05's real back hole and red stain are hidden by folds in the supplied photos/video. Garment 06's real hip hole is not properly visible. These three issues are **not established visible-defect false negatives** and must be excluded from visible-defect recall until adequate evidence is supplied. Physical presence remains owner-confirmed; lack of a detection does not establish absence. The model-proposed spot/hole on garment 05 is not confirmed as the actual hidden hole.

The earlier 4/5 owner-positive garment count describes coarse agreement with physical-condition notes, **not visible-defect recall or accuracy**. No revised visible-defect accuracy is claimed without visibility annotations for the remaining issues. These cases test coverage limitations and requests for unfolded close-ups. Broad claims such as “no holes” still need qualification when fabric is folded or obscured. Raw model outputs below are retained as historical observations. The owner annotation is in `fieldwork-ai/data/results/owner-visibility-2026-10-18.json`.

These are development checks on the same inspected garments. They are not an unseen accuracy benchmark or a seller-versus-received delivery test. Earlier results remain in `../real-captures-2026-10-18/`. All 63 supplied original media hashes remain unchanged. No trained artifact was replaced and no deployment occurred.

## Video uploads

- Added a bundled FFmpeg runtime (`imageio-ffmpeg`) to requirements, pyproject and uv.lock; installed in the fieldwork conda environment.
- Original phone videos are retained. Larger clips receive an H.264/AAC analysis copy with longest side at most 1280 pixels and 24 fps; full-resolution evidence frames still come from the original. FFmpeg applies display rotation and retains an existing audio stream. Already small MP4/WebM inputs retain their bytes.
- Input limits: 128 MiB and 60 seconds; oversized source uploads return 413, unreadable/too-long videos return actionable 422 responses. The seller page now supports recorded-video upload alongside camera recording and photos, including MOV filename handling.
- All 15 originals prepare and decode successfully. Previously only one fit the 20 MiB application guard. The 14 compressed analysis copies are about 2.5–3.2 MB; the already supported garment-12 clip stays unchanged. Audio presence is retained on all 15. Preparation took about 2–5 seconds for these compressed clips.
- This validates local preparation, not cloud ingress/body limits. Large-video cloud upload limits and deployment behavior still need separate validation. Compression can hide fine details; high-resolution frames and targeted close-ups remain necessary.

## Capture coverage

- Candidate selection preserves every prior sharpness-selected frame and adds the sharpest candidate from time intervals. Candidate count is bounded at twice the original budget; this collection uses 166 candidates versus 120 previously. No baseline candidate is replaced by the time-sampling ablation that previously traded one error for another.
- The existing Gemini record call now explicitly audits front, back and label evidence. A shown region must cite a valid retained frame and box. Missing/unclear regions receive targeted guidance. A logo is not evidence that a label was readable.
- Coverage is saved under `listing.capture_coverage` and displayed on the Garment Pass. ConditionRecord is unchanged. Coverage does not certify small-defect absence. Legacy listings without coverage remain readable.
- All claim/coverage-cited frames are retained as reference evidence. Redundant uncited candidates remain stored but do not inflate the listing reference set. This avoids requiring later inspection to compare every redundant time sample.

## Alignment and comparison

- Pairing keeps up to three received candidates above the existing similarity threshold. The gate tries another only if the preceding candidate cannot align; pairs_total counts distinct reference views.
- AKAZE remains first; classical SIFT can provide a fallback without adding a pretrained model. Acceptance keeps the original inlier-count/homography guards and adds minimum inlier ratio .25 and image overlap .30.
- Explicit warped valid-pixel masks replace darkness-based guesses when available. Black fabric remains comparable; empty warp borders are excluded. A listed flaw outside the overlap is uncheckable rather than missing. Insufficient eroded comparison area produces an inconclusive result rather than an empty/no-change result.
- Negative controls matter: 8/30 deliberately different-garment pairs also passed geometric alignment (7 SIFT, 1 AKAZE), often through the shared background. Geometric success is not garment identity or validated garment-surface registration.
- Accordingly, SIFT-assisted comparisons are explicitly provisional. A fallback alone cannot produce consistent; absent a positive difference finding, the assessment remains cant_tell and the report names the limitation. All issues still require human review regardless of assessment.

## Results

| Check | Earlier baseline | Updated check |
|---|---:|---:|
| Original videos locally preparable | 1/15 | 15/15 |
| Same-session photo → video top-1 matching | 29/30 | 30/30 |
| Geometric comparison acceptance | 14/30 | 26/30 (17 AKAZE, 9 provisional SIFT) |
| Representative full video API submissions | Selected clips previously blocked | 4/4 HTTP 200 |

Alignment counts compare a bundle of changes (orientation handling, candidate coverage, alternatives and fallback), not an isolated SIFT accuracy effect. The local test tries up to three same-garment candidates because the probe identity is known; global retrieval is scored separately. The original and updated samples overlap, two probes share each garment, and controls were selected for diagnostics. No claim of final real-world accuracy follows.

| Live original video | Seconds | Retained frames | Front | Back | Label |
|---|---:|---:|---|---|---|
| garment-01 | 39.44 | 2 | shown | shown | unclear |
| garment-05 | 34.50 | 3 | shown | shown | not_shown |
| garment-06 | 23.11 | 2 | shown | shown | unclear |
| garment-14 | 54.68 | 2 | shown | shown | unclear |

The four live videos were deliberately selected: large 4K input (01), reported missing defects (05/06), and the lost-front-view case (14). They are functional/regression diagnostics, not an unbiased accuracy sample. Garment 14 now retains both front and back. All four request a clearer label view. The reported back hole/red stain on 05 and hip hole on 06 remain unresolved/unreported; no defect-recall improvement is claimed.

## Validation and use

- 101 focused/evaluation checks passed, including 12 new priority checks for proxy audio/duration, invalid uploads, frame preservation, evidence-backed coverage, bounded candidates, overlap masking and conservative fallback behavior. Twelve legacy harness checks pass separately.
- Frontend production build and TypeScript checks pass. The initial sandbox build could not fetch its existing Google Fonts; the network-enabled build succeeded. Dependency lock consistency was checked offline.
- Restart the backend to load the new processing code. The Next development server will reload UI edits; restart it if necessary. No running user server was stopped or replaced.
- Artifacts: `video-preparation.json`, `local-checks.json`, `live-videos.json`, `fallback-alignment-review.jpg`, stored records/media under `store/`, usage logs under `logs/`.
- Reproduce the local comparison with `python eval/priority_checks.py`; `--live` runs/resumes the four original-video API checks with an isolated `FW_STORE_DIR` pointing to this result folder’s `store`, Vertex ADC and log settings.

Next: collect/regenerate clear label and defect close-ups; independently adjudicate owner/model disagreements. Garment-aware matching masks or landmarks need validation to address shared-background alignment. Independent received captures remain necessary for DINO/Gemini change detection and full human-review accuracy.
