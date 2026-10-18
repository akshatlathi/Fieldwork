"""Train Fieldwork's condition heads on frozen SigLIP 2 embeddings (train/embed.py).

Heads
- condition (1-5) and pilling (1-5): ordinal logistic (Frank & Hall: one binary model per
  threshold P(y > k)), which respects that grade 4 is closer to 5 than to 1.
- stain and hole: binary (Minor/Major vs none).

Honesty
- Split-conformal prediction sets on a held-out calibration slice of train (alpha=0.1):
  the head returns a *set* of grades ("3 or 4") with ~90% coverage on in-domain photos.
- Baselines in the report: majority class. Gemini and human rows are added by eval/.

Writes heads.joblib and heads.json under --out; never replaces the app model.

    uv run python train/heads.py
"""

import json
import argparse
import hashlib
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, cohen_kappa_score

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork.ml import OrdinalHead  # noqa: E402
from train.labels import defect_label  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EMB = ROOT / "data" / "emb"
ALPHA = 0.1
SEED = 7


def conformal_threshold(p_cal: np.ndarray, y_idx: np.ndarray, alpha: float) -> float:
    """LAC score: 1 - p(true class). Returns the finite-sample-corrected quantile."""
    scores = 1 - p_cal[np.arange(len(y_idx)), y_idx]
    n = len(scores)
    rank = min(n, int(np.ceil((n + 1) * (1 - alpha))))
    return float(np.sort(scores)[rank - 1])


def grade_sets(p: np.ndarray, qhat: float) -> list[list[int]]:
    return [list(np.where(1 - row <= qhat)[0]) for row in p]


def load(split: str):
    d = np.load(EMB / f"{split}.npz", allow_pickle=True)
    X, L = d["X"], {k: d[k] for k in d.files if k != "X"}
    for rest in sorted(EMB.glob(f"{split}_rest_*.npz")):  # extra shards from train/embed.py --full
        r = np.load(rest, allow_pickle=True)
        X = np.concatenate([X, r["X"]])
        L = {k: np.concatenate([L[k], r[k]]) for k in L}
    return X, L


def ordinal_report(name, head, Xc, yc, Xt, yt, levels, majority):
    idx = {lv: i for i, lv in enumerate(levels)}
    qhat = conformal_threshold(head.proba(Xc), np.array([idx[v] for v in yc]), ALPHA)
    pt = head.proba(Xt)
    pred = np.array(levels)[pt.argmax(1)]
    sets = grade_sets(pt, qhat)
    yt_idx = np.array([idx[v] for v in yt])
    return {
        "n_test": int(len(yt)),
        "qwk": round(cohen_kappa_score(yt, pred, weights="quadratic"), 3),
        "within_1": round(float(np.mean(np.abs(pred - yt) <= 1)), 3),
        "exact": round(float(np.mean(pred == yt)), 3),
        "majority_exact": round(float(np.mean(yt == majority)), 3),
        "majority_qwk": 0.0,
        "conformal_alpha": ALPHA,
        "conformal_coverage": round(float(np.mean([t in s for t, s in zip(yt_idx, sets)])), 3),
        "avg_set_size": round(float(np.mean([len(s) for s in sets])), 2),
        "qhat": qhat,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "results" / "heads-run",
                        help="Versioned run directory; does not replace deployed heads")
    args = parser.parse_args()
    Xtr, Ltr = load("train")
    Xte, Lte = load("test")
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(len(Xtr))
    n_cal = int(0.25 * len(Xtr))
    cal, fit = perm[:n_cal], perm[n_cal:]

    heads, results = {}, {}
    for name in ("condition", "pilling"):
        y = Ltr[name].astype(int)
        ok_tr = y > 0
        levels = [1, 2, 3, 4, 5]
        f_idx = fit[ok_tr[fit]]
        c_idx = cal[ok_tr[cal]]
        head = OrdinalHead(levels).fit(Xtr[f_idx], y[f_idx])
        yt = Lte[name].astype(int)
        mask = yt > 0
        majority = int(np.bincount(y[f_idx]).argmax())
        results[name] = ordinal_report(name, head, Xtr[c_idx], y[c_idx], Xte[mask], yt[mask], levels, majority)
        heads[name] = {"head": head, "levels": levels, "qhat": results[name]["qhat"]}

    for name in ("stains", "holes"):
        y = np.array([defect_label(v) for v in Ltr[name]])
        yt = np.array([defect_label(v) for v in Lte[name]])
        known_fit, known_test = fit[y[fit] >= 0], yt >= 0
        if len(np.unique(y[known_fit])) < 2 or len(np.unique(yt[known_test])) < 2:
            results[name] = {"status": "not_evaluable", "reason": "Explicit labels do not contain both classes; null is unknown.",
                             "unknown_train": int((y < 0).sum()), "unknown_test": int((yt < 0).sum())}
            continue
        clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced").fit(Xtr[known_fit], y[known_fit])
        yt = yt[known_test]
        pt = clf.predict_proba(Xte[known_test])[:, 1]
        results[name] = {
            "n_test": int(len(yt)),
            "positives": int(yt.sum()),
            "average_precision": round(float(average_precision_score(yt, pt)), 3),
            "prevalence_baseline_ap": round(float(yt.mean()), 3),
        }
        heads[name] = {"head": clf}

    results["meta"] = {
        "date": time.strftime("%Y-%m-%d"), "seed": SEED,
        "n_train": len(Xtr), "n_fit": len(fit), "n_calibration": len(cal), "n_test": len(Xte),
        "encoder": "google/siglip2-base-patch16-224", "encoder_frozen": True,
        "dataset": "fnauman/fashion-second-hand-front-only-rgb",
        "protocol": "Fixed provided test split; 25% of train reserved for calibration; no test tuning.",
        "embedding_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted(EMB.glob("*.npz"))},
        "limits": "Existing cached embeddings lack garment group IDs; split independence and embedding provenance need auditing before headline claims.",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    joblib.dump(heads, args.out / "heads.joblib")
    (args.out / "heads.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
