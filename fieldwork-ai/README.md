# Fieldwork backend

Python 3.12 API, Gemini agents, garment condition models, and evaluation tools.
The Next.js frontend is in `../fieldwork-app` and has its own npm dependencies.

## Conda setup

From this directory:

```bash
conda env create -f environment.yml
conda activate fieldwork
python -m pip check
```

The environment includes Python 3.12, pip, Node.js 24, and the packages in
`requirements.txt`, including pytest. macOS installs PyTorch from PyPI; the
Linux CPU index configured for uv is not used by this Conda setup.

To reinstall Python dependencies in an existing environment:

```bash
python -m pip install -r requirements.txt
```

## Gemini through Vertex AI

Use the Google account granted access to your Cloud project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
export FW_USE_VERTEX=1
export FW_GCP_PROJECT=YOUR_PROJECT_ID
export FW_GCP_LOCATION=global
```

Credentials remain in Google's local credential store, outside this repository.

## Run locally

From this directory, with the environment active:

```bash
python -m uvicorn fieldwork.api:app --port 8000
```

In another terminal:

```bash
conda activate fieldwork
cd ../fieldwork-app
npm ci
npm run dev
```

The API listens on port 8000 and the frontend on port 3000.

## Quick checks

```bash
python -m pip check
python -m pytest tests/test_store.py
```

Other existing tests can require the downloaded garment dataset, model weights,
or live Gemini calls; they are not all offline installation checks.

## Received garment and human review

The buyer chooses **All good** or **Raise an issue** at `/unbox/<item-id>`.
Issues capture a statement and video/photos, inspect evidence with SigLIP 2,
DINOv2-small, OpenCV and Gemini, then save a report for a person. Every issue
keeps escrow held, even if the inspection suggests consistency or fails.

Set a reviewer-only key before starting the API:

```bash
export FW_REVIEW_TOKEN='YOUR_REVIEWER_ACCESS_KEY'
python -m uvicorn fieldwork.api:app --port 8000
```

Open `/review` in the frontend and enter that key. The human can release funds,
choose a refund percentage, or request more evidence. Buyers see the response
and can add requested footage at `/case/<item-id>`. Refresh the reviewer queue
to see new or updated reports. The key stays in browser memory, not local storage.

DINOv2-small and SigLIP 2 are public checkpoints; no Meta approval is required.
Pre-download them for offline runs using Transformers, or allow the first run
to download them into the Hugging Face cache. DINOv3 is not used.

```bash
python -m pytest tests/test_human_review.py tests/test_store.py -q
```

These checks cover queue persistence, all inspection suggestions, processing
failures, protected human decisions, acceptance restrictions, and additional
evidence. See `../AI-ARCHITECTURE.md` for endpoint changes and prototype limits.
