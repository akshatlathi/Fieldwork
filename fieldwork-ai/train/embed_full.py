"""Resumable, fingerprinted SigLIP2 features, one output per source shard.

Legacy features may be reused only after raw label alignment and sampled encoder checks.
python train/embed_full.py --reuse-legacy --out data/emb-v2
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import time
import numpy as np
import pyarrow.parquet as pq
import torch
from PIL import Image
import truststore
truststore.inject_into_ssl()
from transformers import AutoModel, AutoProcessor

ROOT = Path(__file__).resolve().parent.parent
MODEL = "google/siglip2-base-patch16-224"
LABELS = ["condition", "pilling", "stains", "holes", "type", "category", "price", "brand"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "data/emb-v2")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--reuse-legacy", action="store_true")
    ap.add_argument("--limit-shards", type=int, default=0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    processor = AutoProcessor.from_pretrained(MODEL, local_files_only=True)
    model = AutoModel.from_pretrained(MODEL, local_files_only=True).eval()
    revision = getattr(model.config, "_commit_hash", None)

    def encode(rows):
        images = [Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB") for r in rows]
        with torch.inference_mode():
            features = model.get_image_features(**processor(images=images, return_tensors="pt"))
            features = getattr(features, "pooler_output", features)
            return torch.nn.functional.normalize(features, dim=-1).numpy()

    paths = sorted((ROOT / "data/hf/data").glob("*.parquet"))
    if args.limit_shards:
        paths = paths[:args.limit_shards]
    legacy = {}
    for path in paths:
        output = args.out / (path.stem + ".npz")
        meta_path = output.with_suffix(".json")
        source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if output.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if (meta["source_sha256"] == source_sha and meta["model_revision"] == revision
                    and meta["features_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()):
                print(f"{path.name}: complete; skipping", flush=True)
                continue
            raise ValueError(f"Fingerprint mismatch for {path.name}; choose a new output directory")
        start = time.monotonic()
        rows = pq.read_table(path, columns=["image"] + LABELS).to_pylist()
        split = "test" if path.name.startswith("test") else "train"
        index = int(path.name.split("-")[1])
        reused = args.reuse_legacy and (split == "test" or index < 3)
        checks = None
        if reused:
            if split not in legacy:
                legacy[split] = np.load(ROOT / f"data/emb/{split}.npz", allow_pickle=True)
            cache = legacy[split]
            offset = index * 2173 if split == "train" else 0
            X = cache["X"][offset:offset + len(rows)]
            assert len(X) == len(rows)
            for key in LABELS:
                assert all(str(a) == str(r[key] if r[key] is not None else "")
                           for a, r in zip(cache[key][offset:offset + len(rows)], rows)), f"Label mismatch: {key}"
            sample = sorted(set([0, len(rows) // 2, len(rows) - 1]))
            fresh = encode([rows[i] for i in sample])
            checks = {"n": len(sample), "max_absolute_error": float(np.max(np.abs(fresh - X[sample]))),
                      "min_cosine_similarity": float(np.min(np.sum(fresh * X[sample], axis=1)))}
            assert checks["min_cosine_similarity"] > .9999 and checks["max_absolute_error"] < .002, checks
            print(f"{path.name}: legacy sample check {checks}", flush=True)
        else:
            features = []
            for i in range(0, len(rows), args.batch_size):
                features.append(encode(rows[i:i + args.batch_size]))
                if i % (args.batch_size * 10) == 0:
                    done = min(i + args.batch_size, len(rows))
                    print(f"{path.name}: {done}/{len(rows)} ({done / (time.monotonic()-start):.1f} images/s)", flush=True)
            X = np.concatenate(features)
        assert np.isfinite(X).all()
        labels = {k: np.array([r[k] for r in rows], dtype=object) for k in LABELS}
        image_sha = np.array([hashlib.sha256(r["image"]["bytes"]).hexdigest() for r in rows])
        temporary = output.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, X=X, row_id=np.array([f"{path.name}:{i}" for i in range(len(rows))]),
                            image_sha256=image_sha, **labels)
        temporary.replace(output)
        meta_path.write_text(json.dumps({"source": path.name, "source_sha256": source_sha,
            "model": MODEL, "model_revision": revision, "rows": len(rows), "dimension": X.shape[1],
            "reused_legacy": reused, "sample_validation": checks,
            "features_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "seconds": round(time.monotonic()-start, 2)}, indent=2))
        print(f"Saved {output.name} ({time.monotonic()-start:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
