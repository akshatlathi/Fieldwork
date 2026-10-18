"""Embed the HF second-hand clothing subset with SigLIP 2 (frozen) on CPU.

Writes data/emb/<split>.npz with image embeddings and labels, so training heads
takes seconds instead of re-running the vision model.

    uv run python train/embed.py
"""

import glob
import io
import sys
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import numpy as np
import pyarrow.parquet as pq
import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

MODEL_ID = "google/siglip2-base-patch16-224"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "emb"
LABELS = ["condition", "pilling", "stains", "holes", "type", "category", "price", "brand"]
BATCH = 32


def load_split(pattern: str):
    pattern, _, exclude = pattern.partition("|exclude:")
    files = sorted(glob.glob(str(ROOT / "data" / "hf" / "data" / pattern)))
    if exclude:
        files = [f for f in files if not glob.fnmatch.fnmatch(Path(f).name, exclude + "*")]
    for f in files:
        table = pq.read_table(f, columns=["image"] + LABELS)
        yield from table.to_pylist()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(12)
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).eval()

    splits = [("test", "test-*.parquet"), ("train", "train-0000[0-2]-*.parquet")]
    if "--full" in sys.argv:
        # One output per shard so an interrupted run resumes where it stopped.
        splits += [(f"train_rest_{i:02d}", f"train-{i:05d}-*.parquet") for i in range(3, 13)]
    for split, pattern in splits:
        target = OUT / f"{split}.npz"
        if target.exists():
            print(f"{split}: exists, skipping")
            continue
        rows = list(load_split(pattern))
        feats, start = [], time.time()
        for i in range(0, len(rows), BATCH):
            imgs = [Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB") for r in rows[i : i + BATCH]]
            with torch.inference_mode():
                inputs = processor(images=imgs, return_tensors="pt")
                f = model.get_image_features(**inputs)
                f = getattr(f, "pooler_output", f)
                feats.append(torch.nn.functional.normalize(f, dim=-1).numpy())
            if i % (BATCH * 20) == 0:
                done = i + len(imgs)
                print(f"{split}: {done}/{len(rows)} ({done / (time.time() - start):.1f} img/s)", flush=True)
        labels = {k: np.array([r[k] if r[k] is not None else "" for r in rows], dtype=object) for k in LABELS}
        np.savez_compressed(target, X=np.concatenate(feats), **labels)
        print(f"{split}: saved {target} in {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
