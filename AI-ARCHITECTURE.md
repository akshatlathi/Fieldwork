# Contract changes — 14 October 2026

### Purchase recovery and route-state persistence — 18 October 2026

`GET /purchases` returns shared prototype mandate summaries joined to garment details and the exact attached issue, sorted newest first, omitting signatures, private minima and missing-record test artifacts. `GET /seller/drafts` adds resumable listing summaries without private pricing limits. Existing purchase creation/settlement semantics and Store/ConditionRecord interfaces are unchanged. Production still requires authenticated ownership scopes for both history endpoints.

The frontend now uses a route-independent external draft store. Serializable conversation/form state is mirrored to browser-tab session storage; file objects, busy flags, private minimum entries and reviewer credentials are memory-only. Async request setters remain valid after a route unmounts, so navigation does not discard a completed response. Buyer session IDs survive navigation/reload, but backend ADK conversation memory still does not survive a backend restart. Restoring UI text is not durable server-side chat memory.

Buy shows saved purchases recovered from the backend even if the browser has lost its mandate IDs; Sell shows resumable listings. Bottom navigation remembers the last route in each flow. Seller review refreshes server state without overwriting retained unsaved inputs; changed revisions invalidate acknowledgement and show a review message. Upload completion saves a resume link and redirects only while its originating page is still mounted. Camera cleanup detaches the stop handler, cancels its timer and stops tracks so leaving cannot upload a partial recording. A pending camera-permission result is also cleaned up after unmount.

Validation: 49 focused backend checks, seven frontend state-store checks, frontend production build/typecheck, and actual browser navigation/reload exercises. The saved ₹400 xFisics sweatpants purchase (`md_6c55a5ccb5`) remains held. No duplicate purchase, buyer acceptance, issue submission or payment settlement was performed during browser verification.


### Local workflow audit and seller-defined INR pricing — 18 October 2026

Automatic condition/type-based prices and SEK/JPY demo conversions are removed. `POST /seller/drafts/{id}/price` saves an explicit INR asking price and optional negotiation minimum. The private minimum remains solely in backend `floors` storage. Publication now requires a price; published legacy seller-managed listings can set their first explicit price. ConditionRecord retains `price_band` for compatibility, populated only as `(asking, asking)` for current listings; its default currency is INR. Public legacy records have no price until the seller sets one. No automatic migration of old funded mandates is performed.

`POST /offers` returns deterministic accepted/counter/fixed responses, a negotiation ID, round count and a 30-minute quote ID. Negotiation allows at most five rounds per ID. A below-minimum offer counters at `min(asking, max(minimum, ceil((offer+asking)/20)*10))`; an offer within seller limits is accepted, and an above-asking offer returns the asking price. The central HTTP/MCP escrow path enforces currency, seller limits, valid quotes below asking, quote expiry and one active/completed purchase per garment. Automatic purchases are removed from the in-app buyer agent; a UI confirmation creates escrow. Unauthenticated identities, quote ownership and cross-process transactions remain prototype limitations.

Search/listing responses add `media`, `purchase_price`, `price_source`, and negotiation status; listings add `seller_managed` and `purchase_available`. Already-purchased garments are excluded from available search and cannot receive offers or price edits. Search adds brand/currency filters, normalizes garment-type punctuation, uses actual asking prices for budget filters, and requires every grade in an uncertain set to meet a minimum-grade filter. `GET /issues` accepts an omitted item ID for the **shared prototype** Help history; this is not an authenticated buyer scope. Reviewer decisions remain token-protected.

The in-app ADK buyer uses the same tool functions in-process; external MCP remains available. Search no longer automatically runs two vision Q&A calls. Model calls/response length are bounded and the request has a 60-second agent budget; explicit vision questions run off the event loop. Safe React text formatting, seller media galleries, INR price/offer/confirmation controls, Help history and labelled side-by-side comparisons are wired into the frontend. Old reports are marked as predating correspondence checks; original assessments are retained.

Comparison changes: one-to-one feature matches, inlier-supported garment masks, full-view Gemini correspondence checks before crop judging, explicit crop `comparable` fields, padded-area support checks, and rejection of silently resized crop pairs. Source photo/frame labels and new-frame video timestamps are persisted. Video plus supplementary received photos are both retained and inspected. Failed/uncertain correspondence cannot generate a positive defect conclusion. This is a conservative abstention change, not demonstrated alignment or damage accuracy.


### Full contextual defect-sequence experiment — 18 October 2026

No production contract/model change. `eval/defect_sequence.py` reuses the frozen overview/regional outputs, unions evidence with provenance, and checks all 31 unique proposals using full-photo/crop context. All 30 photos are processed; 15 confirmation tasks succeed, four hit server deadlines and 11 photos have no proposals. Raw context outcomes are 17 supported / two rejected / 12 uncertain; a separate posthoc conservative agreement policy gives 12 / two / 17. Failed/missing checks cannot create support. The 01 lettering-related hole is rejected and 02's visible hole retained, but 05's identical dark crop flips from earlier hole-specific uncertainty to general-context support. The spot remains unresolved, not confirmed as the owner's hidden hole. No accuracy gain or production promotion is claimed. Original hashes are unchanged and 35 focused checks pass. See `fieldwork-ai/data/results/defect-sequence-2026-10-18/REPORT.md`, `REVIEW-NOTES.md`, `prompt-comparison.json` and `review.html` for all evidence, failures and measured overhead.

### Seller regional-defect experiment — 18 October 2026

No production contract, pipeline, weight or threshold change. A frozen 30-photo/15-garment comparison exercises the current overview inspector versus an experimental dedicated per-photo overview-plus-four-tile pass. All 45 attempts complete; original hashes are unchanged. The regional pass adds visibly localized garment-03 hem spots but also a questionable garment-01 hole. A separate posthoc check of all three hole proposals rejects 01, retains 02 and marks 05 uncertain; it is not independent ground truth. Owner-negative garment disagreements increase 1/10 → 4/10, so the raw pass is not promoted. Per-image independent labels remain pending; no defect accuracy claim. One regional call uses the configured fallback model, recorded in the report. Thirty focused checks pass. See `fieldwork-ai/data/results/defect-pass-2026-10-18/REPORT.md`, `REVIEW-NOTES.md` and `review.html`. Experimental helpers live under `eval/`; main seller inspection remains unchanged.

### All-15-garment live workflow regression — 18 October 2026

No production contract or model change. `eval/organized_workflow.py` runs original seller videos through drafts, owner-note disclosures and explicit publication, then original same-session photos through buyer issues and human-review evidence requests in an isolated store. All 15 cases and 285 expected API statuses pass; persisted issue escrows remain held. All 15 assessments are cant_tell, and 15/33 reference views align. Saved comparisons include 24 Gemini candidate-change judgments and two existing-flaw judgments. This does not establish delivery/defect/grade accuracy. All 63 source hashes remain unchanged; 25 focused checks pass. See `fieldwork-ai/data/results/organized-workflow-2026-10-18/REPORT.md` and `REVIEW-NOTES.md`. Browser UI, ADK chats and deployment are not exercised in this run. Priorities are garment-focused correspondence and uncertainty-driven close-ups.

### Seller draft review, disclosures and explicit publication — 18 October 2026

`POST /take` retains its ConditionRecord response but now creates an unpublished seller draft. New pipeline listings default to draft. Marketplace search excludes draft/processing listings, and central HTTP/MCP escrow creation rejects purchase until publication. Existing legacy listings without draft state remain visible. ConditionRecord and Store interfaces are unchanged.

New routes: `GET /seller/drafts/{item_id}`, `POST /seller/drafts/{item_id}/declarations` (`revision`, `answer`, `issues`), `POST /seller/drafts/{item_id}/evidence` (multipart revision and photos/video), and `POST /seller/drafts/{item_id}/publish` (`revision`, `acknowledge_limitations`). Condition answers are issues_reported, none_known or unknown; issue descriptions remain declared, never automatically shown. Severity is unestablished (the existing none value), while positive seller issue IDs still participate in defect-exclusion search. Publication requires a saved answer, acknowledgment and current revision; conflicts return 409. Published drafts are immutable through these routes.

Source uploads and analysis frames are namespaced by attempt; historical raw observations and media are retained, and failed retakes restore the earlier active source set. Earlier positive findings omitted by a new inspection remain explicitly labelled as earlier observations. Reviewed public prose/overview claims are qualified to avoid whole-garment absence claims; translations are rebuilt or omitted on failure. Listing metadata exposes publication_status, seller_limitations and seller_disclosures. The seller UI now opens review/disclosure/retake/approval; the buyer Pass shows unresolved limitations.

120 focused checks, 12 separate legacy checks, frontend build/typecheck and an isolated live six-stage garment-05 API run pass. The live approval was a test actor, not owner validation of a defect. See `fieldwork-ai/data/results/seller-review-2026-10-18/REPORT.md`. Seller ownership/authentication and cross-process transactions remain prototype limitations; no deployment or real payment occurred. Workflow evaluators now include explicit seller publication before purchase.

### Defect close-ups and garment-focused comparison — 18 October 2026

Existing `/take` multipart requests can now combine video and supplementary photos; previously the video branch ignored photos. No route, ConditionRecord or Store schema changes. Optional listing `capture_coverage.views[].garment_outline` contains normalized [y,x] silhouette vertices for the first cited frame only; invalid polygons/unknown original frames are not reused. `detail_requests` adds garment-specific capture suggestions without claiming they are absent or mandatory. The seller UI supports combined submission and the Pass displays guidance.

Reference features/valid comparison masks can be restricted to these outlines. Production received inspection requires garment-focused evidence before suggesting consistent; older listings without outlines remain readable but their unlocalized comparisons are inconclusive. SIFT remains provisional. Missing region correspondence never settles funds. Bounded transport retries now cover HTTP disconnections on read-only Gemini generation only.

Selected six-view diagnostics: same-garment geometric acceptance changed 5/6 → 3/6; different-garment background-control acceptance changed 3/6 → 0/6. These are posthoc development tradeoffs, not final identity accuracy. A live original-video-plus-three-photo submission succeeded; all photos were retained and two masks generated. The reported hip hole on 06 remains unresolved. A zoomed 05 back crop proposed a possible hole requiring owner confirmation. See `fieldwork-ai/data/results/defect-regions-2026-10-18/REPORT.md` and `fieldwork-ai/data/capture-kit/defect-followup/README.md`. 113 focused checks, 12 separately run legacy checks and frontend build/typecheck pass. No deployment or model promotion occurred.

### Video, coverage and comparison improvements — 18 October 2026

Seller `/take` now streams video uploads with a 50 MB bound (413 on excess), validates readable clips up to 60 seconds (422 for invalid input), and preserves the original while Vertex uses a compressed H.264/AAC analysis copy when needed. Full-resolution evidence frames still come from the original. Bundled FFmpeg is installed/locked through imageio-ffmpeg. This is local upload support; cloud ingress limits remain untested.

`GET /listings/{id}` adds optional `capture_coverage`: front/back/label statuses, valid retained evidence boxes, guidance and a limitation. ConditionRecord and Store interfaces are unchanged. The record draft schema audits these regions explicitly; only valid retained evidence supports shown coverage. Candidate selection preserves sharpness choices plus time coverage, then keeps all cited frames as listing references. The Garment Pass displays missing/unclear views; the seller page also accepts existing phone videos. Legacy listing compatibility is retained.

Internal pairing now supplies at most three candidates per reference. AKAZE can fall back to classical SIFT; explicit overlap masks protect flaw/diff comparisons from warp borders. Insufficient overlap is inconclusive. Shared-background controls exposed geometric matches on different garments, so SIFT-assisted results remain provisional and cannot alone support consistent. Human review/payment boundaries are unchanged. Checks: 15/15 video preparation, 4/4 representative live seller submissions, 30/30 development retrieval, 26/30 geometric comparisons (17 AKAZE, 9 provisional SIFT); 101 focused tests, 12 separate legacy tests, frontend build/typecheck and lock consistency pass. See `fieldwork-ai/data/results/workflow-priorities-2026-10-18/REPORT.md` for limits. No final delivery benchmark or deployment occurred.

### Real phone-photo orientation correction — 18 October 2026

Gemini image inputs and SigLIP embeddings now apply EXIF rotation/reflection consistently with OpenCV/display pixels. Original media remains unchanged; upright Gemini inputs retain their bytes. A real garment-08 collar box demonstrated the prior raw-versus-display coordinate mismatch. No route, ConditionRecord, Store or trained artifact changes. Pre-fix photo records need regenerated claims before their crop coordinates can be relied upon; restart the backend for the fix. Nine orientation tests pass within 86 focused checks; 3 new evaluator checks and 12 separate legacy checks also pass.

Real seller captures are now available under `fieldwork-ai/data/organized-garments/`. See `fieldwork-ai/data/results/real-captures-2026-10-18/REPORT.md`: 15/15 photo API captures completed (09 has only two photos), 14/15 original videos were blocked by the existing 20 MiB guard, matching was 29/30 and alignment acceptance 14/30. Owner-note disagreements and missing known defects remain; no real received/change benchmark or deployment occurred. Posthoc EXIF and temporal-selection checks are separate from the saved pre-fix baseline.

### Evidence-integrity fixes — 18 October 2026

No ConditionRecord/Store migration or route changes. Buyer Answer states now validate only `shown`, `not_in_take`, `cant_judge`. An unsupported shown answer loses its original assertion as well as its shown status; its deterministic fallback labels its English language. Shown citations must have valid normalized boxes on captured frames (measured claims remain admissible). Draft ingestion drops malformed boxes; crop generation rejects them. Uncheckable listed flaws now prevent a consistent suggestion in the absence of positive difference findings. Alignment files include a reference-path digest so many-to-one pairing cannot overwrite another reference's warp. 77 focused and 12 separately run legacy checks pass.; no new real-capture accuracy claim is made.

### Purchase constraint fix — 18 October 2026

`POST /escrow` now rejects nonpositive amounts with 422 and rejects wrong currency, missing price band or prices outside the seller's band/floor with 409. The central `escrow.create` enforces the same checks for MCP agent purchases, so a buyer cannot bypass the seller's floor via a different entry point. Successful response shape, ConditionRecord and Store interfaces are unchanged. Payments remain simulated. Existing review fixtures now provide an explicit valid price band.

The agreed issue workflow replaces AI dispute adjudication with a persistent human-review queue. SigLIP 2 remains; DINOv2-small is used because DINOv3 requires gated access. No v3 fallback or download is required.

- `POST /issues` accepts item ID, optional buyer statement and escrow ID, and received-garment video/photos. It stores the report before inspection and returns an `IssueReport`.
- The existing `POST /unbox` capture route now also returns an `IssueReport` and always enqueues human review; it cannot release payment.
- `GET /issues?item_id=...` and `GET /issues/{id}` retrieve saved reports. `POST /issues/{id}/evidence` appends an immutable evidence attempt and re-runs inspection.
- `GET /review` provides the real reviewer queue. `POST /issues/{id}/decision` records a human release, refund, or more-evidence request. Both require `Authorization: Bearer <FW_REVIEW_TOKEN>`.
- The old `/case` adjudication and `/escrow/{id}/settle` API return HTTP 410. The three Gemini rulings and fair-wear refund recommendations have been removed.
- `POST /escrow/{id}/accept` is explicit buyer acceptance and refuses to release while any issue is open for the item.
- `ConditionRecord` and the existing Store interface remain unchanged. `UnboxResult` gains limitations and a crop-comparison trace for the evidence report. Its internal verdict is an inspection suggestion, not a settlement decision.

## Pipeline

All good → buyer acceptance → simulated release.

Raise issue → save complaint and original media → extract frames → SigLIP pairing → replay checks → AKAZE alignment → Gemini existing-flaw checks → DINOv2 + Lab candidate regions → Gemini crop comparisons → Python suggested assessment → saved report → human reviewer.

Every submitted issue, including apparently consistent or failed inspections, stays queued and keeps funds held. Reports include a listing snapshot, raw buyer statement labelled as such, immutable received media, aligned views, crop judgments, coverage limitations, and a human decision/history. Uploaded files and crops are referenced through media URLs, not server filesystem paths.

## Reviewer setup

Set `FW_REVIEW_TOKEN` on the API to a reviewer-only access key. Enter the same key in the `/review` console; the frontend does not persist it. A missing key disables reviewer access rather than enabling public settlement. The queue is shared through this console; there are no external email/Slack notifications.

## Validation limits

Escrow is simulated. Buyer ownership/authentication remains a production integration requirement of the existing demo. The reviewer key is a minimal prototype access control, not a complete identity system. The mutation lock is process-local: before running multiple API workers/Cloud Run instances, issue creation and escrow decisions need Firestore transactions to avoid races. Use one API process for this prototype.

DINOv2 candidate thresholds remain preliminary. Partial alignment and uncertain crop checks are reported; they do not certify garment identity or complete coverage. Gemini model names in report metadata are requested models; fallback calls are tracked in the existing cost log.

Vertex video ingestion now uses inline bytes for short clips instead of the Developer API-only Files API. Real phone filming, real-garment performance, and deployed cloud behavior still require validation.

## Checks completed

### Component diagnostics and agent accounting — 18 October 2026

Controlled synthetic CV results, live crop/question results and limitations are recorded in `fieldwork-ai/data/results/COMPONENT-EVALUATION-2026-10-18.md`. DINO remains in production with unchanged combined weights/threshold; `change_regions(method="colour")` is an evaluation ablation that avoids DINO loading. Buyer/seller ADK responses now log usage through `gemini.log_agent_event`; partial/tool events are excluded, and response intervals include intervening tool work. 63 focused checks and 12 separately run legacy harness checks pass. Real-capture workflow accuracy remains unmeasured. Starter annotation folders are outside the active dataset at `fieldwork-ai/data/capture-kit/`.

### Original label recovery completed — 18 October 2026

Recovered all 28,987 targeted original annotation records and reran the benchmark with `--source-labels`. Explicit source `None` values become negative labels; missing fields stay unknown. 2,116 training hole labels remain excluded. Stain AP is 0.467 (current app 0.427), hole AP 0.170 (current app 0.157), on identical cleaned test rows per task. Only the stain AP improvement has a positive paired difference interval. These remain weak garment-level detectors. No app model promotion occurred. 49 focused offline checks pass. See `data/results/heads-source-labels-2026-10-18/` in `fieldwork-ai/` and the latest training status for details.

### Training audit and full-data comparison — 17 October 2026

See `fieldwork-ai/train/` and the reports under `fieldwork-ai/data/results/` for source/label audit, completed full SigLIP2 embeddings, validation-selected classifier comparisons and limitations. Grade results use deduplicated/consistent test labels; null defect labels are unknown by default. The stain test lacks explicit negatives and hole training lacks sufficient explicit negatives, so strict defect AP is withheld. Null-as-negative results are separate sensitivity analysis only. The app artifact was not replaced. 44 focused offline checks pass. Real-capture evaluation awaits independently labelled recordings; deployment remains on hold for manual local testing.

Partial reads of the original archive recovered its annotation index/schema and ten matching record probes. They confirm mixed mirror-null semantics (genuinely missing older hole fields versus explicit `None` in later source records). Per-record annotation recovery is required before defect benchmarks can be treated as source-backed.

- 18 offline issue/storage tests passed: all assessment paths remain held, failed inspections retain media, reviewer access is enforced, human decisions settle correctly, extra evidence preserves earlier attempts, and uploaded video produces retained evidence frames.
- Frontend production build and TypeScript checks passed.
- Browser smoke checks passed with controlled API responses: capture submission, an apparently consistent issue remaining queued, reviewer evidence requests, additional photos, and explicit All good. No legacy settlement requests or browser errors.
- Real public DINOv2 and SigLIP checkpoints loaded without a Hugging Face login; spatial features and image embeddings were finite and had the expected shapes.
- A real API inspection with SigLIP, DINOv2 and Gemini ran on an edited demo image. It produced a possible stain finding, persisted a report awaiting human review, and retained held escrow. This is a functional synthetic smoke test, not a real-garment accuracy benchmark.
