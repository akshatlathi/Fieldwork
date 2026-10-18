# Classifier comparison — full dataset

Run: 2026-10-17. Null policy: **exclude**.

The app model was not replaced. Missing defect labels remain a data limitation.

| Task | Clean test N | Selected model | Exact accuracy | Current app exact | QWK | Current app QWK | Grade-set coverage | Average set size |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| condition | 3356 | ordinal, C=10.0 | 37.6% | 32.2% | 0.226 | 0.222 | 88.9% | 3.38 |
| pilling | 3356 | ordinal, C=10.0 | 54.7% | 54.6% | 0.114 | 0.030 | 90.2% | 2.94 |

## Defect labels

- stains: **trained_test_not_evaluable**. Known test labels have one class only; AP/precision benchmark withheld.
- holes: **blocked_labels**. Insufficient explicit labels in one or more classes; missing labels were not made negative.

## Protocol and limits

60% fit, 15% model selection, 25% calibration by union of source filename and encoded-image SHA. Select on validation QWK (grades) or AP (defects). Refit on fit+validation before calibration and test.

- Provided test set was examined in earlier runs; this is a comparative benchmark, not a pristine final test.
- Source filename/image grouping does not establish near-duplicate or independently verified garment-level independence.
- Front images may not show the annotated defects; runtime frame averaging needs separate calibration.

Confidence intervals, confusion matrices, validation trials, excluded label counts and file fingerprints are in report.json. Predictions and split indices are saved beside it.
This dataset comparison does not establish real-world phone-video accuracy or final workflow quality.

## Baseline context

- condition: majority exact 37.4%; within-one 73.8% versus current app 78.0%; paired QWK delta CI95 [-0.026056672068621792, 0.03452503252871914].
- pilling: majority exact 55.2%; within-one 76.6% versus current app 75.5%; paired QWK delta CI95 [0.05777338738844633, 0.1109496152006224].
