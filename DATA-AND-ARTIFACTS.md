# Data and artifact policy

Git contains source code, tests, dependency locks, deployment scripts, documentation, capture annotation templates, the small current runtime classifier (`fieldwork-ai/models/heads.joblib`) and Markdown evaluation reports. The runtime classifier is included because the API needs it; larger public pretrained checkpoints are downloaded separately.

The following stay local and are ignored:

- Raw public training Parquet files, source-annotation recovery caches and embeddings under `fieldwork-ai/data/`.
- Original garment videos/photos, crops, alignment images and generated evidence.
- Runtime stores, simulated transactions, uploaded user media and model-call logs.
- Full experimental response JSON, per-example predictions and candidate model artifacts.
- Downloaded research review records, local environments and generated app builds.
- Credentials, private keys and local environment files.

## Evaluation reports

Markdown reports under `fieldwork-ai/data/results/` are included. Images, JSON, stores, call logs and HTML crop galleries referenced by those reports stay local. Those local-only links will not resolve in a fresh GitHub checkout. Reports preserve the limitations and numerical summaries; they are not a self-contained evidence archive.

Current result entry points:

- [Training/source-label benchmark](fieldwork-ai/data/results/heads-source-labels-2026-10-18/REPORT.md)
- [All-15-garment workflow regression](fieldwork-ai/data/results/organized-workflow-2026-10-18/REPORT.md)
- [Regional defect comparison](fieldwork-ai/data/results/defect-pass-2026-10-18/REPORT.md)
- [Full contextual defect sequence](fieldwork-ai/data/results/defect-sequence-2026-10-18/REPORT.md)

No visible-defect or delivery accuracy is inferred from owner-level condition notes or repeated model agreement. Independent per-image references and received sessions remain pending.

## Reconstruct local inputs

- Public training source: Hugging Face `fnauman/fashion-second-hand-front-only-rgb`; acquisition and source-label audit are documented in `fieldwork-ai/train/`.
- Pretrained checkpoints: `google/siglip2-base-patch16-224` and `facebook/dinov2-small`; Transformers downloads them to its normal cache.
- Private development captures: supplied separately by the owner into `fieldwork-ai/data/organized-garments/`; they are not published here.
- New real received-capture annotations: follow `CAPTURE-GUIDE.md` and the included `fieldwork-ai/data/capture-kit/` templates.

Large evidence archives should be managed separately with their source manifests and access controls rather than committed to the code repository. No original local media is deleted by these exclusions.
