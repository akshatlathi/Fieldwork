# Component evaluation — 18 October 2026

These are controlled synthetic/fixture diagnostics, not final real-capture accuracy results. No real seller/received captures are available.

## CV: 12 public garment photographs

| Check | Result |
|---|---:|
| Correct closed-set SigLIP matches | 12/12 |
| Alignment success | 23/24 pairs |
| Median alignment error on successful pairs | 0.41 pixels |
| colour: top-3 mark localisation (IoU ≥ .1) | 8/12 |
| colour: unchanged images with proposals above 3.5 | 0/12 |
| combined: top-3 mark localisation (IoU ≥ .1) | 10/12 |
| combined: unchanged images with proposals above 3.5 | 1/12 |

The fixed 3.5 production score threshold was not retuned. Colour-only removes DINO while retaining the original colour weight; it is not a separately calibrated competitor. Sample sizes are small. Alignment pairs share source images; their binomial intervals are descriptive rather than independent-garment estimates. Closed-set transformed-copy retrieval does not establish identity of real garments.

One combined localisation miss is a broad crop containing the mark with IoU below .1; the other is an alignment failure. Both remain misses in the predeclared localisation metric.

## Live Gemini diagnostics

- Eight known-location crop checks: four unchanged crops correctly reported unchanged, two painted marks reported as new defects, and two painted marks returned unsure. Oracle boxes isolate the judge and bypass proposal selection; these are not end-to-end case results.
- Ten buyer-question fixture checks matched expected shown/not-in-take/cant-judge states, before and after code guards. Answer semantics still require independent review.
- Two posthoc production-selected crop checks: the broad crop exposed the mark to Gemini, while the unchanged false proposal was rejected as a crease/reflection. These were selected after seeing failures and are diagnostic only.

All live calls used gemini-3.8-flash. The first 18 checks logged 36492 input tokens and 4173 output/thinking tokens. Two additional selected-crop checks are logged separately in the component log. No placeholder dollar-cost estimates are presented.

## Integration fixes and checks

- Escrow creation now enforces positive amount, listing currency, price band and seller minimum in both the HTTP and MCP agent paths. API business conflicts return 409; nonpositive amount validation returns 422. Payments remain simulated.
- Buyer/seller ADK response token usage now reaches the shared usage log. Partial/tool events are excluded. Agent response timing includes intervening tool work, not just network/model latency. Wiring is covered by offline runner tests.
- 63 focused tests passed. The legacy harness is run separately because it owns a process-global test store. Its evaluator orchestration test now uses explicitly scripted inspection outputs, rather than pretending a pixel heuristic is a reliable Gemini oracle. Actual CV/Gemini behaviour is covered by the diagnostics above.

## Data still required

The active real-capture dataset has no labelled recordings. Use data/capture-kit/README.md and the root CAPTURE-GUIDE.md. Templates are not ground truth and are outside data/garments/. Fill annotations independently, record the media and validate them before model runs. The next evaluation is the real seller → buyer → inspection → human-review path, with development/calibration/test garments kept separate. Manual local app checks still precede deployment.
