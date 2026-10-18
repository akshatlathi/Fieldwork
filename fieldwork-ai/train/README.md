# Reproduce the classifier benchmark

Activate the existing `fieldwork` Conda environment and run these commands from `fieldwork-ai/`.

```bash
python train/audit.py
HF_HOME=/private/tmp/fieldwork-hf-cache HF_HUB_OFFLINE=1 python train/embed_full.py --reuse-legacy --out data/emb-v2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python train/evaluate_heads.py --emb data/emb-v2 --out data/results/a-new-run-directory
```

The full run requires all 13 training feature shards and the test shard. Embedding resumes only when output/source/model fingerprints match. It never replaces the legacy embedding files. This workflow uses CPU inference with a frozen encoder and does not call Gemini.

The output directory must be new, preserving earlier experiments. It contains the candidate artifact, validation trials, test metrics, paired comparison intervals, split indices, predictions, and a Markdown report. It never replaces `models/heads.joblib`, which the app loads.

## Label policy

- Condition and pilling: integer 1–5 only.
- Defect present: Yes, Minor, Major, ignoring case and surrounding whitespace.
- Defect absent: explicit No or literal None strings.
- Null, empty and unrecognised values: unknown, excluded by default.

The downloaded mirror represents most apparent absence labels as null; their meaning has not been established from the original annotations. As a result, a strict benchmark can train a stain model on explicit train labels but cannot evaluate it against a two-class test set. Hole labels lack enough explicit negative training examples. Those limitations are reported, not filled in as clean garments.

`--null-policy negative` runs an **assumption-dependent sensitivity analysis**. It must be named and reported separately and cannot support headline defect-accuracy claims or automatic promotion. `--allow-partial` is for diagnostics, not the full dataset benchmark.

## Independence and calibration

Identity groups join preserved source filenames and exact encoded-image hashes. Keep identity groups together in 60% fitting, 15% model selection and 25% calibration partitions. Exclude train/test identity overlaps. Within each task, count each group once and exclude conflicting known labels. The source filenames are identity proxies; near duplicates and physical garment identity are not independently verified.

Select ordinal versus multiclass logistic models and regularisation strength on validation data. Refit on fit+validation, calibrate the grade-set threshold on the independent calibration partition, then evaluate once on the provided test set. This test set was examined in earlier experiments; a final unseen real-capture set remains necessary.

The model classes and encoders are not fine-tuned jointly. A grade set's dataset coverage does not establish the same coverage after runtime frame averaging or on phone videos.

## Next evaluation track

Follow `../eval/EVALUATION-PLAN.md` and the root `CAPTURE-GUIDE.md`. Real-capture API evaluation uses `eval/workflow_eval.py`; semantic claim/translation quality and actual human review require independent reference review. Keep local manual app testing ahead of cloud deployment.
