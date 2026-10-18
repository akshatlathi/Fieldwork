# Fieldwork evaluation protocol — 17 October 2026

## Status and scope

The connected seller/buyer/reviewer path passed one live functional smoke run on demo media with a digital edit. This establishes integration, not accuracy. Classifier benchmarking and real-capture evaluation are separate tracks. No automatic deployment or model promotion is part of a training run.

## Public-dataset classifiers

- Source: `fnauman/fashion-second-hand-front-only-rgb`, 28,248 training and 3,390 test rows; source release: https://zenodo.org/records/13788681 (CC-BY 4.0).
- `train/audit.py` fingerprints source shards, lists image hashes, checks cached labels, counts exact duplicates and label conflicts.
- Grade labels must be integers 1–5. Defect positives: case-insensitive Yes/Minor/Major. Explicit negatives: No/None. Null, empty and unrecognised values are unknown.
- Missing defect values are not proven absent. An explicitly named null-as-negative sensitivity experiment is permitted but cannot be presented as validated accuracy.
- Generate remaining frozen SigLIP2 features with `train/embed_full.py`. Existing features are reused only after raw label alignment and sampled numerical encoder checks. Model/source/output fingerprints are recorded per shard. Sample checks do not verify every legacy feature.
- Use the union of preserved source filenames and exact image hashes for 60% fitting, 15% validation/model selection, 25% calibration. Exclude any train/test identity overlap. Count each identity group once per task and exclude conflicting known labels. Timestamp filenames are a garment-identity proxy; near duplicates and independently verified garment IDs remain a limitation.
- Compare ordinal logistic and multiclass logistic heads at C = .01, .1, 1, 10. Select once on validation QWK; binary heads use validation AP. Refit selected configurations on fit+validation; calibrate grade sets on the reserved calibration partition.
- Evaluate against the current app model and fitting-majority baseline on identical cleaned test rows. Report sample counts, confusion matrices, exact accuracy with binomial intervals, within-one accuracy, QWK, log loss, grade-set coverage/size/empty rate. For defects report AP and precision/recall at a stated threshold only when both test classes are supported.
- The provided test set was already examined during earlier runs. Report it as a comparative dataset benchmark, not an untouched final test. Keep final real capture garments separate.
- Save candidates/reports in new run directories. Incomplete or unsupported heads must never replace the app artifact implicitly.

## Real capture pilot

Collect 30 distinct garments initially, with approximately 10 development, 10 calibration, and 10 held-out final-test garments. This is a small pilot with wide intervals, not a production accuracy benchmark. Assign garment IDs/splits before inspecting model outputs. Every capture of the same garment, and both members of a deliberate look-alike pair, stay in one split. Add garments to increase statistical power before making broad claims.

Each garment needs the seller take, front/back/label photos, independently written flaws/attributes, received take(s), and a physical change log. Distinguish actual damage from removable proxies: lint is not a labelled fabric tear; a pin is not automatically a hole. Do not infer defect severity from how a change was created. Annotate what is actually visible. Keep digitally edited media in a separate synthetic stress-test track.

Cases should include unchanged re-shoots, real visible changes, different similar garments, lighting/fold changes, missing views, blur, and replayed listing media. Failed uploads and interrupted processing are orchestration tests, not visual accuracy samples.

Reference annotations must be made before viewing system predictions. Two people independently review final-test flaws/change labels where possible; record and adjudicate disagreement. Unknown/occluded regions remain unknown. Store evidence locations in source photos or frame timestamps, never invented coordinates.

## Measurements by stage

| Stage | Reference | Metrics |
|---|---|---|
| Seller attributes | Human-readable labels and visible garment attributes | Attribute accuracy, abstention rate, unsupported claims |
| Seller flaws | Visible flaw code, region, severity, frame/time and box | Precision/recall, severity agreement, localisation, invalid/missing evidence |
| Frame selection | Required regions and usable frames | Coverage, sharp usable views, redundancy |
| Grade output | Independent rubric-based graders | Exact/within-one/QWK, grade-set coverage and size; keep sorter and phone-capture results separate |
| Listing and translation | Evidence record plus bilingual review | Invented details, omitted defects, changed severity/meaning |
| Buyer answers | Answerable and deliberately unanswerable questions | Correctness, supported citations, unknown handling |
| Pairing/alignment | Corresponding views/landmarks | Matching precision, coverage, alignment error, justified rejection |
| DINO/colour proposals | Marked visible change regions | Change recall within top-k, false proposals per garment, localisation |
| Gemini crop checks | Changed/unchanged/unclear labelled pairs | Missed changes, false alarms, severity agreement, uncertainty |
| Python assessment/report | Human-reviewed full evidence package | Case confusion matrix, changed-case recall, unchanged false alarms, can't-tell rate, report completeness |
| Buyer/seller agents | Fixed scenarios and expected tools/states | Completion, unnecessary calls, explicit confirmation, price constraints, failure recovery |
| Human review | Expected state transitions | Escrow stays held, reviewer authentication, additional evidence/history, idempotent decisions |
| Runtime | Repeated representative executions | p50/p95 latency, errors, retries, token counts, actual model-specific cost |

Headline visual metrics use garments/cases, not an inflated count of correlated crops. Report the number of distinct garments and cases, uncertainty intervals, all failures and exclusions. Report can't-tell separately and include it in coverage/recall denominators so abstention cannot hide misses. Existing note keyword matching is preliminary and does not establish complete ground truth.

## Controlled comparisons

Use the same held-out cases and fixed prompts/model IDs: colour-only versus colour+DINO candidate proposals; candidate crops with versus without Gemini confirmation; grading heads versus fitting-majority/current app; evidence-grounded answers on answerable versus unanswerable questions. Tune thresholds on calibration/development only. Freeze settings before the final cases are run. Human reviewers, not the model under test, establish reference labels.

## Remaining work

1. Full embeddings, original defect-label recovery and classifier comparisons are complete. Controlled CV/Gemini diagnostics are saved in `data/results/COMPONENT-EVALUATION-2026-10-18.md`; they do not substitute for real captures. Improve weak detectors based on valid development evidence.
2. Capture/annotate real garment cases and lock splits.
3. Validate `truth.json` files with `eval/capture_schema.py`, then use `eval/workflow_eval.py` for the seller/search/questions/acceptance/issue/report/review-request API path. Use `--with-agents` to include live agents. The new runner has offline checks but awaits real captures; it does not replace independent semantic review, manual UI tests or a real reviewer's decision. Existing `workflow_smoke.py` covers additional-evidence and simulated refund transitions. The old `run_eval.py` alone does not evaluate the complete updated workflow.
4. Run component evaluations and paired ablations; fix development failures without revisiting final-test answers.
5. Freeze configuration, run final held-out cases, publish counts/intervals/limitations and measured runtime costs.
6. Complete manual local app checks before cloud deployment, then rerun persistence/restart and workflow checks in the cloud.
