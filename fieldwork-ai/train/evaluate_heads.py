"""Validation-selected classifier benchmark with independent calibration groups.

python train/evaluate_heads.py --emb data/emb-v2 --out data/results/full-v2
Unknown defect labels are excluded unless --null-policy negative explicitly requests a sensitivity run.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, cohen_kappa_score, confusion_matrix,
                             log_loss, precision_recall_curve, precision_recall_fscore_support)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork.ml import OrdinalHead, SoftmaxHead
from train.labels import defect_label, grade_label
from fieldwork.stats import rate

LEVELS = [1, 2, 3, 4, 5]
SEED = 7


def threshold(probabilities, y, alpha=.1):
    scores = 1 - probabilities[np.arange(len(y)), y - 1]
    rank = min(len(scores), int(np.ceil((len(scores) + 1) * (1 - alpha))))
    return float(np.sort(scores)[rank - 1])


def load(directory, split):
    paths = sorted(directory.glob(f"{split}-*.npz"))
    if not paths:
        raise ValueError(f"No {split} shards in {directory}")
    arrays = {}
    for path in paths:
        meta = json.loads(path.with_suffix(".json").read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["features_sha256"]
        with np.load(path, allow_pickle=True) as data:
            for key in data.files:
                arrays.setdefault(key, []).append(data[key])
    return {k: np.concatenate(v) for k, v in arrays.items()}, paths


def ordinal_metrics(y, p):
    p = np.asarray(p, dtype=np.float64)
    p /= p.sum(axis=1, keepdims=True)
    predicted = p.argmax(axis=1) + 1
    correct = int((y == predicted).sum())
    return {"n": len(y), "exact": round(float(np.mean(y == predicted)), 4),
            "exact_interval": rate(correct, len(y)),
            "within_1": round(float(np.mean(np.abs(y - predicted) <= 1)), 4),
            "qwk": round(float(cohen_kappa_score(y, predicted, weights="quadratic", labels=LEVELS)), 4),
            "log_loss": round(float(log_loss(y, p, labels=LEVELS)), 4),
            "confusion_matrix": confusion_matrix(y, predicted, labels=LEVELS).tolist()}


def paired_qwk_interval(y, p, baseline, repeats=500):
    """Paired bootstrap over deduplicated images; original garment IDs unavailable."""
    rng = np.random.default_rng(SEED)
    predicted, old = p.argmax(axis=1) + 1, baseline.argmax(axis=1) + 1
    differences = []
    for _ in range(repeats):
        i = rng.integers(0, len(y), len(y))
        differences.append(cohen_kappa_score(y[i], predicted[i], weights="quadratic", labels=LEVELS)
                           - cohen_kappa_score(y[i], old[i], weights="quadratic", labels=LEVELS))
    return {"repeats": repeats, "delta_qwk_ci95": np.quantile(differences, [.025, .975]).tolist(),
            "unit": "unique encoded image; original garment grouping unknown"}


def apply_source_labels(data, recovered):
    counts = Counter()
    for i, rid in enumerate(data["row_id"]):
        row = recovered.get(rid)
        if row is None:
            continue
        if row["status"] != "matched":
            for key in ("stains", "holes"):
                data[key][i] = None
            counts["identity_mismatch_excluded"] += 1
            continue
        for key in ("stains", "holes"):
            before = defect_label(data[key][i])
            after = defect_label(row["labels"][key])
            data[key][i] = row["labels"][key]
            if before < 0 and after >= 0:
                counts[f"{key}_unknown_recovered"] += 1
            if key in row.get("conflicts", []):
                counts[f"{key}_conflict_excluded"] += 1
        counts["source_rows_matched"] += 1
    return dict(counts)


def binary_metrics(y, scores, threshold_value):
    predicted = scores >= threshold_value
    tp = int(np.sum(predicted & (y == 1)))
    fp = int(np.sum(predicted & (y == 0)))
    fn = int(np.sum(~predicted & (y == 1)))
    return {"threshold": threshold_value, "precision": rate(tp, tp+fp), "recall": rate(tp, tp+fn),
            "f1": float(2*tp / (2*tp+fp+fn)) if 2*tp+fp+fn else 0.,
            "confusion_matrix": confusion_matrix(y, predicted, labels=[0, 1]).tolist()}


def choose_binary_threshold(y, scores):
    precision, recall, thresholds = precision_recall_curve(y, scores)
    f1 = 2*precision[:-1]*recall[:-1] / np.maximum(precision[:-1]+recall[:-1], 1e-12)
    return float(thresholds[int(np.argmax(f1))])


def paired_ap_interval(y, scores, old, repeats=500):
    rng = np.random.default_rng(SEED)
    values, differences = [], []
    for _ in range(repeats):
        i = rng.integers(0, len(y), len(y))
        if len(np.unique(y[i])) < 2:
            continue
        value = average_precision_score(y[i], scores[i])
        values.append(value)
        differences.append(value - average_precision_score(y[i], old[i]))
    return {"repeats": len(values), "ap_ci95": np.quantile(values, [.025, .975]).tolist(),
            "delta_ap_ci95": np.quantile(differences, [.025, .975]).tolist()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emb", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--null-policy", choices=["exclude", "negative"], default="exclude")
    ap.add_argument("--allow-partial", action="store_true", help="Diagnostic run on incomplete training shards")
    ap.add_argument("--source-labels", type=Path, help="Source-backed per-record defect label overlay")
    args = ap.parse_args()
    train, tr_paths = load(args.emb, "train")
    test, te_paths = load(args.emb, "test")
    manifest_path = Path(__file__).resolve().parent.parent / "data/audit/manifest.jsonl"
    manifest = {r["row_id"]: r for r in map(json.loads, manifest_path.read_text().splitlines())}
    for data in (train, test):
        for rid, image_hash in zip(data["row_id"], data["image_sha256"]):
            assert manifest[rid]["image_sha256"] == image_hash, f"Audit identity mismatch: {rid}"
        data["group_id"] = np.array([manifest[rid]["group_id"] for rid in data["row_id"]])
    source_meta = None
    if args.source_labels:
        if args.null_policy != "exclude":
            raise ValueError("Source labels must retain truly missing values as unknown")
        source_meta = json.loads((args.source_labels.parent / "recovery-summary.json").read_text())
        assert not source_meta["errors"] and not source_meta["unmatched"], "Incomplete source recovery"
        assert source_meta["manifest_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        assert source_meta["overlay_sha256"] == hashlib.sha256(args.source_labels.read_bytes()).hexdigest()
        recovered = {r["row_id"]: r for r in map(json.loads, args.source_labels.read_text().splitlines())}
        source_meta = {"overlay_sha256": source_meta["overlay_sha256"], "source_url": source_meta["source_url"],
                       "train": apply_source_labels(train, recovered), "test": apply_source_labels(test, recovered)}
    if not args.allow_partial:
        assert len(tr_paths) == 13 and len(train["X"]) == 28248, "Full training set not ready"
        assert len(test["X"]) == 3390, "Unexpected test size"
    args.out.mkdir(parents=True, exist_ok=False)
    test_hashes = set(test["group_id"])
    groups = sorted(set(train["group_id"]) - test_hashes,
                    key=lambda h: hashlib.sha256(f"{SEED}:{h}".encode()).hexdigest())
    # Splits use source/image identity; duplicate rows stay together.
    a, b = int(.60 * len(groups)), int(.75 * len(groups))
    assignment = {h: ("fit" if i < a else "validation" if i < b else "calibration") for i, h in enumerate(groups)}
    ix = {name: np.array([i for i, h in enumerate(train["group_id"]) if assignment.get(h) == name], dtype=int)
          for name in ("fit", "validation", "calibration")}
    np.savez_compressed(args.out / "split-indices.npz", **ix, row_id=train["row_id"])
    report = {"meta": {"date": time.strftime("%Y-%m-%d"), "seed": SEED,
        "null_policy": args.null_policy, "sensitivity_only": args.null_policy == "negative",
        "partial_diagnostic": args.allow_partial,
        "source_label_recovery": source_meta,
        "n_train": len(train["X"]), "n_test": len(test["X"]),
        "split_rows": {k: len(v) for k, v in ix.items()},
        "excluded_train_test_duplicates": sum(h in test_hashes for h in train["group_id"]),
        "audit_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "features": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tr_paths + te_paths},
        "protocol": "60% fit, 15% model selection, 25% calibration by union of source filename and encoded-image SHA. Select on validation QWK (grades) or AP (defects). Refit on fit+validation before calibration and test.",
        "limits": ["Provided test set was examined in earlier runs; this is a comparative benchmark, not a pristine final test.",
                   "Source filename/image grouping does not establish near-duplicate or independently verified garment-level independence.",
                   "Front images may not show the annotated defects; runtime frame averaging needs separate calibration."]},
        "tasks": {}}
    heads = {}
    baseline_path = Path(__file__).resolve().parent.parent / "models/heads.joblib"
    baseline = joblib.load(baseline_path)
    report["meta"]["current_app_model_sha256"] = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    X, Xt = train["X"], test["X"]
    for name in ("condition", "pilling", "stains", "holes"):
        ordinal = name in ("condition", "pilling")
        convert = grade_label if ordinal else lambda v: defect_label(v, null_policy=args.null_policy)
        y, yt = np.array([convert(v) for v in train[name]]), np.array([convert(v) for v in test[name]])
        task = {"label_counts_train": dict(Counter(str(v) for v in y)),
                "label_counts_test": dict(Counter(str(v) for v in yt))}
        report["tasks"][name] = task
        # Each exact image contributes once. Ambiguous duplicate labels are excluded, not arbitrarily resolved.
        for data, target, suffix in ((train, y, "train"), (test, yt, "test")):
            grouped = {}
            for i, image_hash in enumerate(data["group_id"]):
                grouped.setdefault(image_hash, []).append(i)
            conflicts, repeats = 0, 0
            for indices in grouped.values():
                known = [i for i in indices if target[i] >= 0]
                if len({target[i] for i in known}) > 1:
                    target[indices] = -1
                    conflicts += 1
                elif len(known) > 1:
                    target[known[1:]] = -1
                    repeats += len(known) - 1
            task[f"conflicting_image_groups_excluded_{suffix}"] = conflicts
            task[f"duplicate_rows_excluded_{suffix}"] = repeats
        f, v, c = (ix[k][y[ix[k]] >= 0] for k in ("fit", "validation", "calibration"))
        t = np.where(yt >= 0)[0]
        task["usable_split_rows"] = {"fit": len(f), "validation": len(v), "calibration": len(c), "test": len(t)}
        required = 5 if ordinal else 2
        if (len(np.unique(y[f])) < required or len(np.unique(y[v])) < required
                or (not ordinal and min(Counter(y[f]).values()) < 10)):
            task.update(status="blocked_labels", reason="Insufficient explicit labels in one or more classes; missing labels were not made negative.")
            print(name, task["status"], flush=True)
            continue
        trials = []
        for kind in (("ordinal", "multiclass") if ordinal else ("binary",)):
            for C in (.01, .1, 1., 10.):
                if ordinal:
                    model = (OrdinalHead if kind == "ordinal" else SoftmaxHead)(LEVELS, C=C).fit(X[f], y[f])
                    metrics = ordinal_metrics(y[v], model.proba(X[v]))
                    score = metrics["qwk"]
                else:
                    model = LogisticRegression(C=C, max_iter=2000, class_weight="balanced").fit(X[f], y[f])
                    score = float(average_precision_score(y[v], model.predict_proba(X[v])[:, 1]))
                    metrics = {"average_precision": score}
                trials.append({"kind": kind, "C": C, "score": score, "validation": metrics})
        selected = max(trials, key=lambda row: row["score"])
        task.update(selection=selected, trials=trials)
        fit = np.concatenate([f, v])
        if ordinal:
            model = (OrdinalHead if selected["kind"] == "ordinal" else SoftmaxHead)(LEVELS, C=selected["C"]).fit(X[fit], y[fit])
            qhat = threshold(model.proba(X[c]), y[c])
            p = model.proba(Xt[t])
            sets = 1 - p <= qhat
            task["test"] = ordinal_metrics(yt[t], p)
            task["current_app_on_same_test"] = ordinal_metrics(yt[t], baseline[name]["head"].proba(Xt[t]))
            task["paired_comparison"] = paired_qwk_interval(yt[t], p, baseline[name]["head"].proba(Xt[t]))
            np.savez_compressed(args.out / f"{name}-predictions.npz", row_id=test["row_id"][t],
                                y=yt[t], p=p, current_app_p=baseline[name]["head"].proba(Xt[t]))
            majority = Counter(y[fit]).most_common(1)[0][0]
            task["test"].update(majority_grade=int(majority), majority_exact=float(np.mean(yt[t] == majority)),
                conformal_coverage=float(np.mean(sets[np.arange(len(t)), yt[t] - 1])),
                average_set_size=float(sets.sum(axis=1).mean()), empty_set_rate=float(np.mean(sets.sum(axis=1) == 0)), qhat=qhat)
            heads[name] = {"head": model, "levels": LEVELS, "qhat": qhat}
            task["status"] = "evaluated"
        else:
            model = LogisticRegression(C=selected["C"], max_iter=2000, class_weight="balanced").fit(X[fit], y[fit])
            heads[name] = {"head": model}
            if len(np.unique(yt[t])) < 2:
                task.update(status="trained_test_not_evaluable", reason="Known test labels have one class only; AP/precision benchmark withheld.")
            else:
                p = model.predict_proba(Xt[t])[:, 1]
                old = baseline[name]["head"].predict_proba(Xt[t])[:, 1]
                precision, recall, f1, _ = precision_recall_fscore_support(yt[t], p >= .5, average="binary", zero_division=0)
                decision_threshold = choose_binary_threshold(y[c], model.predict_proba(X[c])[:, 1])
                task.update(status="evaluated", test={"n": len(t), "average_precision": float(average_precision_score(yt[t], p)),
                    "prevalence_baseline_ap": float(yt[t].mean()), "precision_at_0_5": float(precision),
                    "recall_at_0_5": float(recall), "f1_at_0_5": float(f1), "threshold": .5,
                    "at_calibration_selected_threshold": binary_metrics(yt[t], p, decision_threshold)})
                task["threshold_selection"] = {"method": "Maximum F1 on independent calibration labels; no test threshold tuning",
                                                "threshold": decision_threshold, "n": len(c)}
                task["current_app_on_same_test"] = {"average_precision": float(average_precision_score(yt[t], old)),
                                                     "at_0_5": binary_metrics(yt[t], old, .5)}
                task["paired_comparison"] = paired_ap_interval(yt[t], p, old)
                np.savez_compressed(args.out / f"{name}-predictions.npz", row_id=test["row_id"][t], y=yt[t], p=p, current_app_p=old)
        print(name, task["status"], task.get("test", {}), flush=True)
    report["meta"]["runtime_complete"] = len(heads) == 4
    report["meta"]["automatic_promotion"] = False
    joblib.dump(heads, args.out / "heads.joblib")
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    lines = ["# Classifier comparison" + (" — partial diagnostic" if args.allow_partial else " — full dataset"), "", f"Run: {report['meta']['date']}. Null policy: **{args.null_policy}**.",
             "", "The app model was not replaced. Missing defect labels remain a data limitation.", "",
             "| Task | Clean test N | Selected model | Exact accuracy | Current app exact | QWK | Current app QWK | Grade-set coverage | Average set size |",
             "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for name, task in report["tasks"].items():
        if name in ("condition", "pilling") and task.get("test"):
            new, old = task["test"], task["current_app_on_same_test"]
            lines.append(f"| {name} | {new['n']} | {task['selection']['kind']}, C={task['selection']['C']} | {new['exact']:.1%} | {old['exact']:.1%} | {new['qwk']:.3f} | {old['qwk']:.3f} | {new['conformal_coverage']:.1%} | {new['average_set_size']:.2f} |")
    lines += ["", "## Baseline context", ""]
    for name in ("condition", "pilling"):
        task = report["tasks"][name]
        if task.get("test"):
            new, old = task["test"], task["current_app_on_same_test"]
            lines.append(f"- {name}: fitting-majority exact accuracy {new['majority_exact']:.1%}; within-one accuracy {new['within_1']:.1%} versus current app {old['within_1']:.1%}. Paired QWK difference 95% interval: {task['paired_comparison']['delta_qwk_ci95']}.")
    lines += ["", "## Defect labels", ""]
    for name in ("stains", "holes"):
        task = report["tasks"][name]
        lines.append(f"- {name}: **{task['status']}**. {task.get('reason', '')}")
        if task.get("test"):
            lines.append(f"  AP={task['test']['average_precision']:.3f}; prevalence reference={task['test']['prevalence_baseline_ap']:.3f}. Null-as-negative results are sensitivity analysis only.")
    lines += ["", "## Protocol and limits", "", report["meta"]["protocol"], ""]
    lines += ["- " + limit for limit in report["meta"]["limits"]]
    lines += ["", "Confidence intervals, confusion matrices, validation trials, excluded label counts and file fingerprints are in report.json. Predictions and split indices are saved beside it.",
              "This dataset comparison does not establish real-world phone-video accuracy or final workflow quality."]
    (args.out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"Saved {args.out}; app model unchanged", flush=True)


if __name__ == "__main__":
    main()
