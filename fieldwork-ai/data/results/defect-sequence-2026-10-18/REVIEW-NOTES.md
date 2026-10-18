# Sequence review and decision

Tested sequence: cached current overview → cached dedicated regional inspection → new full-photo/crop confirmation → supported/rejected/uncertain model decisions. The same 30 primary front/back photos from 15 garments are used. No new detector training, production integration, deployment, settlement or grading change is involved.

## What improved in the examples

Final primary results: 30/30 photos processed, 31 unique proposals, 17 context-supported, two not_supported and 12 uncertain. The posthoc conservative agreement policy gives 12 supported, two not_supported and 17 uncertain. Five detector-uncertain proposals received context support; the conservative policy does not promote those. Thirty-five focused software checks pass. All original source hashes remain unchanged. A completed-run resume adds no model calls.

Nineteen photos have proposals and require confirmation; 11 skip it because neither detector proposed a finding. Fifteen confirmation tasks succeed; four hit server deadlines (07 back, 08 back, 12 front/back). Seven proposals remain uncertain because of these failed tasks. There are no missing/duplicated/invented response-ID errors in successful results. These failures remain in the main denominator and are not silently rerun or removed.

New context wall time totals 1,034.65 seconds across the dataset, including retries/failures; failed tasks each take approximately 176–181 seconds. Successful-call logs record 58,620 input/output/thinking tokens, all on gemini-3.8-flash. Including cached overview/regional stages yields 377,942 logged tokens versus 89,431 for overview alone (about 4.23 times as many); successful-call logs cannot account for unavailable token usage on failed tasks. This is not a dollar-cost estimate. Summing historic stage wall times gives 2,155.62 seconds for sequential dataset processing, not an app latency benchmark.

Owner-described defect-free garments with at least one supported proposal are 5/10 for raw context decisions and 3/10 with the conservative policy (raw regional definite proposals flagged 4/10; overview flagged 1/10). These are unresolved disagreement counts, not false-positive rates. In particular, a failed context task or conservative abstention must not be counted as a correctly rejected defect. No net accuracy improvement is established.

- Garment 01's proposed hole is rejected. Both the earlier hole-specific context prompt and this general context prompt describe fabric lettering/indentations or creases rather than an opening. This agrees with the earlier pixel inspection; independent human reference review remains pending.
- Garment 02's visible hole survives the sequence. Both initial arms and both context prompts localize/support the small opening below the pocket. This is a useful development regression case, not a general hole-recall estimate.
- Garment 03's back-hem brown specks survive confirmation, while the faint yellow hem proposal stays uncertain. The brown specks were visible in the earlier source-crop review, and the original overview had reported no defect. Do not infer the chemical cause as mud from pixels alone.
- The proposed snag on garment 09's back is rejected. These are saved model decisions, not independently scored false positives.

## Important weakness: context support is not verification

Garment 05's same dark spot receives **uncertain** from the earlier hole-specific checker and **supported** from this general checker. The crop files are byte-identical; the full photograph and requested model are also the same. The prompts differ, so this illustrates response/prompt sensitivity rather than an isolated causal measurement of prompt effects. Sampling/service variation is not controlled by a single run.

The new model's reason (broken knit fibers) does not independently establish those fibers or a through-opening. The spot is still **unresolved**. It is not confirmed as the owner's real back hole, which the owner says is hidden by folds. The red hip stain on 05 and hip hole on 06 likewise receive no invented visibility labels. Seller disclosures remain unchanged.

This sequence can repeat an initial mistake, add certainty to an ambiguous crop, or reject a real issue. Neither agreement between model calls nor a valid evidence box establishes correctness. It cannot recover a visible defect that neither detector proposed.

## Conservative agreement policy

After observing context support for detector-uncertain proposals, a separate **posthoc analysis** was added: require at least one definite detector origin and a supported context decision to retain a supported proposal. A proposal that was only uncertain at detection stays uncertain even if the context checker supports it. Context-uncertain, missing/duplicate response IDs and failed calls stay uncertain; explicit context rejection is retained as not_supported.

This is a policy sensitivity analysis, not a preregistered third arm or an independently validated improvement. It prevents automatic upgrades of detector uncertainty, but it cannot resolve the ambiguous 05 spot because the regional detector had already called that definite. The original raw responses are preserved alongside the policy counts.

## Runtime and failures

Confirmation requests are skipped only for photos with no proposals. Skipping does not establish absence of defects. New model calls use the configured primary model with fallbacks disabled for this confirmation run. Cached detection includes one earlier fallback on garment-10 photo-2, which had no findings.

Service timeouts are recorded in the primary results and leave proposals uncertain. Successful-call token logs do not measure unavailable usage for failed requests. Added confirmation wall time includes retries/failures. Overview and regional costs are historical cached measurements: summing stages estimates sequential processing, not a newly measured end-to-end app latency or production p95.

## Decision and next work

Keep the sequence experimental as a candidate-generation/review aid. It preserves useful localized evidence and rejects selected unsupported proposals, but does not establish overall precision/recall gains or reliable automatic hole verification. Do not turn context-supported into a public shown claim solely on model agreement.

The next prerequisite is a visibly labelled defect set: per-image hole/stain locations, clear negative regions, explicit ambiguous/folded areas, and a consistent defect/severity rubric. The existing reviewer template remains pending; no reference labels are fabricated. Use these inspected garments for development, then evaluate a frozen context-confirmed method on independently annotated additional visible holes/stains and an unseen test set. Classifier training and grade calibration require those relevant labels rather than treating model predictions as truth.

Inspect `REPORT.md` for the final per-garment counts and usage, `review.html` for crops/reasons/provenance, `prompt-comparison.json` for the three hole-prompt comparisons, and `report.json` for full upstream snapshots and new context responses. The software checks validate evidence/state handling, not model accuracy.
