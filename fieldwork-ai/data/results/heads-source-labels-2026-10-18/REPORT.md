# Classifier comparison — full dataset

Run: 2026-10-18. Null policy: **exclude**.

The app model was not replaced. This run uses original source-backed defect labels; truly missing labels are excluded.

| Task | Clean test N | Selected model | Exact accuracy | Current app exact | QWK | Current app QWK | Grade-set coverage | Average set size |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| condition | 3356 | ordinal, C=10.0 | 37.6% | 32.2% | 0.226 | 0.222 | 88.9% | 3.38 |
| pilling | 3356 | ordinal, C=10.0 | 54.7% | 54.6% | 0.114 | 0.030 | 90.2% | 2.94 |

## Baseline context

- condition: fitting-majority exact accuracy 37.4%; within-one accuracy 73.8% versus current app 78.0%. Paired QWK difference 95% interval: [-0.026056672068621792, 0.03452503252871914].
- pilling: fitting-majority exact accuracy 55.2%; within-one accuracy 76.6% versus current app 75.5%. Paired QWK difference 95% interval: [0.05777338738844633, 0.1109496152006224].

## Defect labels

- stains: **evaluated**. 
  AP=0.467; prevalence reference=0.273. These results use recovered source annotations, not a null-as-negative assumption.
- holes: **evaluated**. 
  AP=0.170; prevalence reference=0.073. These results use recovered source annotations, not a null-as-negative assumption.

## Protocol and limits

60% fit, 15% model selection, 25% calibration by union of source filename and encoded-image SHA. Select on validation QWK (grades) or AP (defects). Refit on fit+validation before calibration and test.

- Provided test set was examined in earlier runs; this is a comparative benchmark, not a pristine final test.
- Source filename/image grouping does not establish near-duplicate or independently verified garment-level independence.
- Front images may not show the annotated defects; runtime frame averaging needs separate calibration.

Confidence intervals, confusion matrices, validation trials, excluded label counts and file fingerprints are in report.json. Predictions and split indices are saved beside it.
This dataset comparison does not establish real-world phone-video accuracy or final workflow quality.

## Source-backed defect comparison

| Task | Test N | Current app AP | Candidate AP | Precision at calibration threshold | Recall at calibration threshold |
|---|---:|---:|---:|---:|---:|
| stains | 3357 | 0.427 | 0.467 | 40.0% | 67.9% |
| holes | 3363 | 0.157 | 0.170 | 16.5% | 29.8% |
