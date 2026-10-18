# Seller review and retake loop — 18 October 2026

New seller captures now become drafts. The seller reviews observations, explicitly answers the condition question, saves any known issues, adds supplemental evidence if needed, reviews limitations, then approves publication. Capture alone does not publish.

## Implemented behavior

- `/take` retains its ConditionRecord response shape but creates a draft. The frontend opens `/sell/review/<id>` rather than immediately presenting a published Pass.
- Drafts are excluded from marketplace search. Central escrow creation rejects them for HTTP and MCP purchases.
- Condition answers are `issues_reported`, `none_known`, or `unknown`. Typed issues contain code, region and description. They remain `declared` with no invented evidence or severity. Unknown severity uses the existing `none` enum value; it does not mean the reported defect is absent. Seller-reported issue IDs remain available to defect-exclusion search regardless of unestablished severity.
- Overview claims no longer become broad clean assertions in the reviewed public projection. Generated listing prose is rebuilt from qualified observations and disclosures; translations are regenerated. A failed translation drops stale translated prose while retaining English disclosures.
- Additional photos/video are saved with source hashes in unique attempt folders. Analysis frames also have unique attempt prefixes. Earlier original media and raw model outputs remain in history. All active source photos and the latest source video participate in reinspection; failed attempts preserve their source files and restore the earlier active source set.
- Previously observed positive defect findings are retained from earlier captures if a later inspection omits that code/region. They are labelled Earlier capture and cite retained original frames. A new fold cannot silently erase earlier evidence. No automatic claim that repair or disappearance is established is made.
- Seller disclosures survive reinspection independently of model findings. A reported hidden hole or stain remains disclosed even when no image establishes it. A matching model label alone does not automatically confirm the seller's particular issue.
- Publication requires an answered condition question, explicit acknowledgment of the displayed limitations and the current revision. Stale approvals/edits return 409. Published drafts cannot be edited through draft routes. Buyer-facing Passes show unresolved limitations and separate declared claims.

## API additions

- `GET /seller/drafts/{item_id}` returns the review record, state, revision, disclosures, guidance, limitations, original-media links and history.
- `POST /seller/drafts/{item_id}/declarations` accepts `{revision, answer, issues}`.
- `POST /seller/drafts/{item_id}/evidence` accepts multipart revision, optional video/photos and optional code.
- `POST /seller/drafts/{item_id}/publish` accepts `{revision, acknowledge_limitations}`.

Invalid disclosures return 422; unknown drafts 404; stale/missing approval or edits to published drafts 409. Existing ConditionRecord and Store interfaces remain unchanged. Listing metadata adds publication_status, seller_limitations and seller_disclosures. Existing legacy listings without draft metadata keep their previous visibility; newly generated take listings default to draft. Direct pipeline callers need to use the seller-review workflow to publish.

## Validation

120 focused/backend checks and 12 separate legacy harness checks pass. Frontend production build and TypeScript checks pass. New checks cover hidden drafts, purchase blocking, declared-versus-shown separation, saved disclosures after retakes, immutable media, failed attempts, stale/missing approvals, retained earlier findings, translation failure and defect filtering.

A live isolated API run used garment 05's three original photos. The hole and red stain were declared from the owner's clarification, with visibility explicitly not established. A repeated original back photo exercised the evidence-retake route; it is not a new physical capture or a defect-accuracy test. All six stages completed HTTP 200. Search exclusion before approval and inclusion after approval were checked; a hole-excluding query rejects the published seller-disclosed item. No real listing was published into the user's active app store, no payments were initiated, and no cloud deployment occurred.

| Stage | Seconds |
|---|---:|
| create_draft | 26.56 |
| review_draft | 0.00 |
| disclose_hidden_issues | 3.34 |
| additional_evidence_reinspection | 22.75 |
| simulated_seller_approval | 0.01 |
| buyer_listing | 0.00 |

## Use locally

Restart the backend to load the new draft/publication logic. Refresh/restart the Next app if necessary. Capture via Sell, review the draft, save the condition answer, upload any additional evidence, then approve publication with the displayed limitations. The draft review page and capture history remain accessible afterward.

## Limits

This remains a local prototype role/approval flow: seller ownership authentication is not implemented, and the locks serialize one API process only. Authenticated ownership and transactional persistence are required before multi-user/multi-worker deployment. A seller approval is not visual verification. Detail requests are suggestions and do not establish that any particular flaw exists or is absent. Original raw observations stay in attempt history; a seller correction/repair adjudication process remains future work. Independent received recordings are still needed for full delivery and human-review accuracy evaluation.

The workflow evaluator and live smoke runner now explicitly exercise seller review/disclosure/publication before buyer search/purchase. Their scripted approval checks transitions, not human decision quality. Historical performance reports remain historical.
