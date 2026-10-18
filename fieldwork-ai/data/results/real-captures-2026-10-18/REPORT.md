# Real seller-capture evaluation — 18 October 2026

## Owner visibility clarification — 18 October 2026

The owner confirms that garment 05's real back hole and red stain are hidden by folds in the supplied photos/video. Garment 06's real hip hole is not properly visible. These three issues are **not established visible-defect false negatives** and must be excluded from visible-defect recall until adequate evidence is supplied. Physical presence remains owner-confirmed; lack of a detection does not establish absence. The model-proposed spot/hole on garment 05 is not confirmed as the actual hidden hole.

The earlier 4/5 owner-positive garment count describes coarse agreement with physical-condition notes, **not visible-defect recall or accuracy**. No revised visible-defect accuracy is claimed without visibility annotations for the remaining issues. These cases test coverage limitations and requests for unfolded close-ups. Broad claims such as “no holes” still need qualification when fabric is folded or obscured. Raw model outputs below are retained as historical observations. The owner annotation is in `fieldwork-ai/data/results/owner-visibility-2026-10-18.json`.

We evaluated the supplied `data/organized-garments/` collection: 15 garments, 44 main photos and 15 main videos, plus preserved extras. All 63 media files match the supplied SHA-256 manifest. Owner-corrected notes are the reference for reported condition; they were not passed to Gemini. Originals were not modified.

**Scope:** real seller-capture development evaluation, not final seller-versus-received workflow accuracy. There are no independently annotated received/unboxing sessions, physical changes, grade labels or defect boxes. These garments must not later be described as an unseen test set.

## Baseline results

The baseline process started before the EXIF correction and retained the original image handling throughout all 30 video/photo cases. Later diagnostics are saved separately.

| Measurement | Result | Interpretation |
|---|---:|---|
| Main-photo API processing | 15/15 | 14 cases meet the UI minimum; garment 09 has only two photos and is an API-only diagnostic. |
| Original videos accepted by existing inline guard | 1/15 | 14 exceed the application’s 20 MiB cap; the guard was directly exercised without attempting doomed model calls. |
| Supported original video processed | 1/1 | Garment 12 completed full seller processing, including grading/translations, in 32.20 s. |
| Expected code read from photos | 13/15 | Garments 14 and 15 were not read successfully. This does not establish freshness/authenticity. |
| Owner-positive garments with any shown defect | 4/5 | Coarse presence agreement only, not correct defect type/location or complete defect recall. |
| Owner-negative garments with a shown defect | 3/10 | Disagreements on 07, 08 and 11 require adjudication; do not assume every disagreement is a hallucination. |
| Photo → video garment retrieval | 29/30 | 30 front/back probes against 120 selected frames from 15 garments, before orientation fix. Shared session/background/code cards make this easier than delivery matching. |
| Selected pairs accepted by AKAZE alignment | 14/30 | Geometric acceptance only; no independent alignment accuracy/overlap annotations. |
| Retained video frames | 120/120 above existing blur threshold | Eight per garment; sharpness does not prove semantic view coverage. |
| Photo API latency | Median 21.39 s | Range 15.50–51.31 s, includes grading and translation. Mixed warm/cold run; not a p95 benchmark. |
| Grade usefulness | 13/15 returned [2,3,4,5] | Other sets: 07 [3,4,5], 10 [2,4,5]. No reference grades, so exact-grade accuracy is unavailable. |

Uncertainty: 4/5 presence agreement has a descriptive exact 95% interval of 28.4–99.5%; 3/10 owner-negative flags has 6.7–65.2%; code reading 13/15 has 59.5–98.3%. Retrieval/alignment probes repeat garments, so their binomial intervals in JSON do not account for garment correlation. This small development collection cannot establish generalization.

## Per-garment photo results

| Garment | Owner note | Shown defects reported | Code | Seconds |
|---|---|---|---|---:|
| 01 | Shoulder defect; type unresolved | discolour (front); loose_seam (hem) | Read | 21.57 |
| 02 | Front hole below pocket | hole (front); other (label) | Read | 51.31 |
| 03 | Mud stains near ankle | stain (back) | Read | 38.91 |
| 04 | No defects | None | Read | 18.86 |
| 05 | Front dark spots; back hole; red hip stain | stain (front); fading (whole); other (label) | Read | 34.04 |
| 06 | Hip hole; side/location unresolved | None | Read | 26.36 |
| 07 | No defects | other (label) | Read | 16.39 |
| 08 | No defects | discolour (right_armpit); discolour (left_armpit) | Read | 21.39 |
| 09 | No defects | None | Read | 41.48 |
| 10 | No defects | None | Read | 15.50 |
| 11 | No defects | discolour (waistband) | Read | 20.52 |
| 12 | No defects | None | Read | 20.69 |
| 13 | No defects | None | Read | 37.74 |
| 14 | No defects | None | Not read | 16.52 |
| 15 | No defects | None | Not read | 18.81 |

## Main failure analysis

- **Garment 06:** the record and listing reported no visible flaws/rips/holes, despite the owner reporting a hip hole. The buyer answer repeated no visible holes, while adding sensible close-up limitations. Grounded Q&A can propagate an upstream inspection error. Exact defect position/visibility is pending owner clarification.
- **Garment 05:** front spots were reported, but the owner-reported back hole and red hip stain were not explicitly reported. Three reported claims do not mean three correct owner defects: the other claims were general fading and a worn care label.
- **Owner-negative disagreements:** 07 was flagged for pen writing on its label, 08 for underarm yellowing, and 11 for inner-waistband discoloration. Garment-condition labels need a clear policy on label markings, minor wear and illumination; the owner/model discrepancies need independent review.
- **Garment 14 coverage:** the greedy sharpness/time-gap selector retained only back views, starting at 5 s, while its front is present earlier. Its front photo retrieved garment 12 at cosine .757, above the production .6 minimum. High similarity is not sufficient evidence of a matching view.
- **Phone orientation:** 43/44 main photos contain nonidentity EXIF orientation (32 orientation 6, 10 orientation 8, one orientation 3). On garment 08, Gemini’s collar box landed on a sleeve after OpenCV’s orientation correction, while that same box located the collar in raw sideways JPEG coordinates. Coordinate bounds validation alone cannot catch this mismatch.

## Fix applied and separate follow-up

Gemini image serialization now sends upright pixels when EXIF rotation/reflection is present. SigLIP preprocessing applies the same EXIF transform. Original files and hashes remain unchanged; already upright images are passed to Gemini without reencoding. No thresholds or trained model artifacts were changed.

A targeted live collar-location call on garment 08 after the fix returned a crop containing the collar and neck opening; the crop was manually inspected. Nine tests cover rotations/reflections, unchanged originals, unchanged upright image bytes and upright embedding inputs. Existing pre-fix photo claim coordinates should be regenerated before relying on their crops. Restart the local backend to apply the code change.

Orientation-corrected retrieval remained 29/30. This demonstrates that the coordinate fix does not by itself resolve missing view coverage. No all-garment post-fix defect-quality benchmark was run; the baseline defect results above must not be presented as post-fix accuracy.

Three targeted buyer-answer states matched the intended checks: recorded front hole → shown; fabric softness → cannot judge; missing size label → not in take. The fourth garment-06 answer is error analysis rather than a scored independent accuracy sample. All checks were selected after baseline inspection.

## Frame-selection experiment

A posthoc development ablation reserved time intervals and chose the sharpest frame in each interval. It restored garment 14’s early front view and correct retrieval, but introduced a new garment-11 versus garment-03 confusion. Aggregate retrieval stayed 29/30; alignment acceptance changed from 14/30 to 16/30. This small, selected development comparison is insufficient for adoption; production selection is unchanged. Semantic front/back/label coverage needs explicit tracking, not time sampling alone.

## Work still needed

1. Add a reliable upload path for normal phone videos: preserve originals and use a documented compressed analysis copy or authorized GCS ingestion. Validate audio, rotation and small-defect visibility after compression. Improve the current upload error path; only garment 12 worked unchanged.
2. Regenerate records with corrected image orientation; independently check evidence boxes and condition claims. Obtain close-ups/locations for the reported missing defects on 05 and 06.
3. Track required front/back/label/flaw coverage explicitly and request targeted retakes. Do not rely on eight sharp frames as proof of coverage.
4. Improve view pairing and alignment, with top-candidate checks/overlap diagnostics and clear abstention. Don’t loosen geometric thresholds solely to make these development cases pass.
5. Keep weak grading experimental; evaluate visible-defect supervision and higher-resolution/local features before model promotion.
6. Record independent received sessions (unchanged, added defects, look-alikes, missing views) to measure DINO candidate recall, Gemini change judgments and human-review usefulness end to end. No received truth or planted changes were invented here.

## Reproduction and artifacts

- `eval/organized_captures.py --phase local`: hash checks, frame quality, closed-set matching and alignment; resumes saved results.
- `eval/organized_captures.py --phase live`: full `/take` photo API, supported original video, production size-guard checks. Requires isolated local `FW_STORE_DIR`, Vertex ADC/project settings, and writable logs. Live cases resume by garment/track; use a new output directory for a different code version.
- `eval/temporal_coverage.py`: the separate development selector experiment.
- `eval/real_capture_followup.py`: selected orientation and buyer-answer diagnostics.
- `live-report.json`: every owner note, record, listing, timing, price/grade output and failure reason.
- `local-report.json`: hashes, frame metrics, all 30 matching/alignment outcomes.
- `temporal-ablation.json` and `followup-report.json`: separate posthoc experiments.
- `inventory.jpg` and `frames-1.jpg` through `frames-3.jpg`: source photos and retained video-frame contact sheets.
- `orientation-diagnostic.jpg` and `orientation-fixed-collar.jpg`: the concrete coordinate error and corrected live crop.

Baseline usage: 32 successful Gemini calls; 75,724 input tokens and 25,127 output/thinking tokens, using gemini-3.8-flash and gemini-3.5-flash-lite. Five selected follow-up calls are logged separately. Dollar estimates are withheld; placeholder prices are not used.

Validation: 86 focused software checks plus 3 evaluation checks passed; 12 legacy harness checks passed separately. These are software checks, not additional garment samples. No cloud deployment occurred.
