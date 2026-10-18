"""Audit raw labels, exact image duplicates, cache label alignment and source fingerprints."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from labels import defect_label, grade_label

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/hf/data"
OUT = ROOT / "data/audit"
LABELS = ["condition", "pilling", "stains", "holes", "type", "category", "price", "brand"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"dataset": "fnauman/fashion-second-hand-front-only-rgb", "files": [], "splits": {},
               "null_policy": "exclude; null-as-negative only permitted as explicitly labelled sensitivity analysis",
               "limits": ["Exact encoded-image duplicates only; near duplicates and original garment IDs remain unaudited.",
                          "Front-only images may not show sorter-labelled defects."]}
    seen = defaultdict(list)
    cached_labels = {}
    with (OUT / "manifest.jsonl").open("w") as manifest:
        for split in ("train", "test"):
            counts = {k: Counter() for k in LABELS[:4]}
            usable = {k: Counter() for k in LABELS[:4]}
            raw_for_cache = []
            total = 0
            for path in sorted(DATA.glob(f"{split}-*.parquet")):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                summary["files"].append({"file": path.name, "sha256": digest, "rows": pq.ParquetFile(path).metadata.num_rows})
                offset = 0
                for batch in pq.ParquetFile(path).iter_batches(batch_size=64, columns=["image"] + LABELS):
                    for row in batch.to_pylist():
                        sha = hashlib.sha256(row["image"]["bytes"]).hexdigest()
                        rid = f"{path.name}:{offset}"
                        seen[sha].append((split, rid))
                        entry = {"row_id": rid, "split": split, "image_sha256": sha,
                                 "source_image_path": row["image"].get("path"),
                                 "labels": {k: row[k] for k in LABELS}}
                        manifest.write(json.dumps(entry) + "\n")
                        for k in counts:
                            counts[k]["<NULL>" if row[k] is None else str(row[k])] += 1
                            label = grade_label(row[k]) if k in ("condition", "pilling") else defect_label(row[k])
                            usable[k][str(label)] += 1
                        if split == "test" or path.name in {f"train-{i:05d}-of-00013.parquet" for i in range(3)}:
                            raw_for_cache.append({k: row[k] if row[k] is not None else "" for k in LABELS})
                        offset += 1
                        total += 1
                print(f"Audited {path.name}: {offset} rows", flush=True)
            summary["splits"][split] = {"n": total, "raw_labels": {k: dict(v) for k, v in counts.items()},
                                        "normalised_labels": {k: dict(v) for k, v in usable.items()}}
            path = ROOT / f"data/emb/{split}.npz"
            with np.load(path, allow_pickle=True) as cached:
                cached_labels[split] = {"rows": len(cached["X"]), "dimension": cached["X"].shape[1],
                    "finite_features": bool(np.isfinite(cached["X"]).all()),
                    "label_mismatches": {k: sum(str(a) != str(b[k]) for a, b in zip(cached[k], raw_for_cache)) for k in LABELS},
                    "raw_rows": len(raw_for_cache), "feature_provenance": "Legacy cache; matching labels do not prove image/encoder identity."}
    duplicates = [{"image_sha256": sha, "rows": rows} for sha, rows in seen.items() if len(rows) > 1]
    cross = [d for d in duplicates if len({r[0] for r in d["rows"]}) > 1]
    summary.update(cache_audit=cached_labels, exact_duplicate_groups=len(duplicates), cross_split_duplicate_groups=len(cross))
    row_labels = {r["row_id"]: r["labels"] for r in map(json.loads, (OUT / "manifest.jsonl").read_text().splitlines())}
    summary["conflicting_duplicate_groups_raw"] = {k: sum(len({str(row_labels[rid][k]) for _, rid in g["rows"]}) > 1
                                                        for g in duplicates) for k in LABELS[:4]}
    entries = list(map(json.loads, (OUT / "manifest.jsonl").read_text().splitlines()))
    parent = {r["row_id"]: r["row_id"] for r in entries}
    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)
    identities = defaultdict(list)
    for r in entries:
        if r["source_image_path"]:
            identities[r["source_image_path"]].append(r["row_id"])
    for group in identities.values():
        for rid in group[1:]:
            union(group[0], rid)
    for group in seen.values():
        for _, rid in group[1:]:
            union(group[0][1], rid)
    grouped_splits = defaultdict(set)
    with (OUT / "manifest.jsonl").open("w") as manifest:
        for r in entries:
            r["group_id"] = find(r["row_id"])
            grouped_splits[r["group_id"]].add(r["split"])
            manifest.write(json.dumps(r) + "\n")
    summary["source_identity"] = {"rows_with_source_path": sum(bool(r["source_image_path"]) for r in entries),
        "unique_paths": len(identities), "combined_groups": len(grouped_splits),
        "cross_split_groups": sum(len(splits) > 1 for splits in grouped_splits.values()),
        "grouping": "Union of exact encoded-image SHA and preserved source image filename; timestamp filenames are a garment-identity proxy, not independently verified IDs."}
    (OUT / "duplicates.json").write_text(json.dumps(duplicates, indent=2))
    (OUT / "audit.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"splits": {k: v["n"] for k, v in summary["splits"].items()},
                      "cache": cached_labels, "cross_split_duplicate_groups": len(cross)}, indent=2))


if __name__ == "__main__":
    main()
