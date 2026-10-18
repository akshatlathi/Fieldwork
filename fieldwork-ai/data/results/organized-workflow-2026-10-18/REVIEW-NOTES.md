# Interpretation of the 15-garment run

The seller-video → draft → publication → purchase → buyer-photo issue → human-review request flow completed on all 15 items. All 285 API status checks met expectations, including rejected draft purchases, blocked acceptance during an open issue, and denied unauthenticated reviewer access. A final read of persisted files confirmed all 15 issue escrows were still held and all 15 reports were needs_evidence. Every saved comparison-media link resolves to an existing local evidence file. All 63 original hashes match before and after the run. No active app listings, real payments or deployments were involved.

The 25 focused seller-review, human-review and real-capture evaluator tests also pass. The current run uses 15 primary videos and 44 primary photos; four extra files are hash-checked only. Retakes and final human settlement are covered by earlier live/unit tests, not newly exercised for each garment here. Browser UI, buyer/seller ADK chats, try-on and cloud deployment are outside this run.

## What is working

- All 15 original phone videos now reach live Gemini inspection successfully. This is stronger ingestion evidence than preparation-only checks.
- Front/back are reported shown on 15/15 seller videos. These are model-reported coverage statuses, not independent segmentation labels or proof of visibility of every defect.
- The owner-reported defects stay declared: one each for 01, 02, 03 and 06; three for 05. Hidden or unclear issues are not upgraded into visible findings just because a code matches.
- The smell question returned cant_judge on 15/15. This tests one known nonvisual question, not general question-answer accuracy.
- DINOv2/Lab candidate changes and Gemini judgments are exercised. Saved entries include 15 aligned views, 24 candidate-change judgments and two existing-flaw judgments. These counts do not indicate detection accuracy.
- No new-defect, missing-flaw or replay finding was recorded. All issue reports still reached human review, and no inspection settled funds.

## Where it is weak

**Comparison usefulness is the largest gap.** All 15 suggestions are cant_tell. Only 15/33 listing reference views align; six garments have zero aligned views and ten have incomplete alignment. Three cases cannot check at least one recorded flaw. One uses provisional SIFT; one aligned view lacks a usable garment outline. Five cases contain uncertain Gemini crop judgments. Categories overlap. The current safeguards correctly preserve uncertainty, but an always-inconclusive result provides limited assistance to a reviewer.

**Capture and localization matter before changing models.** Plain fabric, changed folds, phone blur and partial views limit point correspondences. Shared beds and cards can produce misleading correspondences, so removing garment-focus guards merely to raise alignment counts would be unjustified. In a visually inspected garment-06 crop, the received code card actually covers the reference fabric; Gemini marks it unsure. Garment outlines do not exclude objects lying inside the garment, such as cards.

**Seller recognition remains incomplete.** The capture code is recognized on 11/15 videos (not recognized on 07, 11, 14, 15). Labels are not clearly shown on any seller video in this run. Existing close-up photos were used as buyer inputs, so this does not test label recognition when those photos supplement seller video. Video-only ingestion should be distinguished from the supported mixed-media capture flow.

**Observations need adjudication.** The model reports a front hole on 02 and front dark spots/stains on 05. It reports upper-front discoloration on 01, whose owner note has an unresolved defect type and a potentially different shoulder description. It does not report the owner-noted ankle mud on 03. Video visibility/localization still needs independent checking before scoring these as exact matches or visible misses. On owner-described defect-free garment 09, it flags whitish marks on both sides. The inspected back frame does show light patches, but residue, lighting, fabric appearance and whether those count as defects remain unresolved. This is an owner/model disagreement, not automatically a proven false positive.

Garment 05's real back hole/red hip stain are hidden by folds; 06's hip hole is unclear. Their absence from shown findings is not an established visible-defect miss. Broad grade sets remain weakly discriminating; no grade accuracy can be computed without reference grades.

**The follow-up can be irrelevant.** The generic random close-up picker asked for a collar for garment-06 jeans. Follow-up requests should identify the uncertain view/region and garment type. The human request in this test is scripted, so this does not measure real reviewer decisions or report usefulness.

**Latency varies.** Median complete case time is 53.8 seconds, maximum 137.35. Seller video capture ranges up to 82.40 seconds; received comparison reaches 102.38 seconds. Cases with multiple sequential crop calls take longer. These 15 development observations are not a production latency benchmark.

## Next work, in order

1. Diagnose failed view pairs and improve garment-focused correspondence. Separate comparable front/back evidence from label-only or other noncomparable references; expose reasons for rejection. Test changes against both same-garment pairs and different-garment shared-background controls. Preserve abstention on inadequate evidence.
2. Make close-up requests follow the actual uncertainty and garment type, including hidden seller-disclosed issues, rather than randomly asking for an irrelevant body region.
3. Use the existing label photos as seller supplements in a separate mixed-media experiment. Keep them out of buyer comparisons when measuring correspondence; repeated identical files would primarily test replay detection.
4. Adjudicate the recorded seller findings and visibility before reporting defect accuracy or selecting new training labels. Independent received recordings remain necessary for delivery change recall, false alarms, reviewer agreement and final workflow evaluation.

Successful model calls used gemini-3.8-flash (56 calls) and gemini-3.5-flash-lite (30). DINOv2 and SigLIP checkpoints and trained heads were unchanged. These 15 already-inspected garments remain development data.
