"""Export a small, readable dataset sample and audit label counts without training."""
from collections import Counter
import html
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/hf/data"
OUT = ROOT / "data/inspection"
OUT.mkdir(parents=True, exist_ok=True)
labels = ["condition", "pilling", "stains", "holes"]
report = {"files": [], "splits": {}, "cached_embeddings": {}}
for split in ("train", "test"):
    counts = {k: Counter() for k in labels}
    total = 0
    for path in sorted(DATA.glob(f"{split}-*.parquet")):
        parquet = pq.ParquetFile(path)
        total += parquet.metadata.num_rows
        report["files"].append({"file": path.name, "rows": parquet.metadata.num_rows, "bytes": path.stat().st_size})
        table = parquet.read(columns=labels)
        for key in labels:
            counts[key].update("<NULL>" if v is None else str(v) for v in table[key].to_pylist())
    report["splits"][split] = {"rows": total, "labels": {k: dict(v) for k, v in counts.items()}}
    cached = np.load(ROOT / f"data/emb/{split}.npz", allow_pickle=True)
    report["cached_embeddings"][split] = {"shape": list(cached["X"].shape),
        "labels": {k: dict(Counter(str(v) for v in cached[k])) for k in labels}}

sample_path = sorted(DATA.glob("test-*.parquet"))[0]
batch = next(pq.ParquetFile(sample_path).iter_batches(batch_size=36))
rows = batch.to_pylist()
cards = []
for i, row in enumerate(rows):
    blob = row["image"]["bytes"]
    image = OUT / f"test-{i:03d}.jpg"
    image.write_bytes(blob)
    caption = {k: v for k, v in row.items() if k != "image"}
    (OUT / f"test-{i:03d}.json").write_text(json.dumps(caption, indent=2, ensure_ascii=False))
    cards.append(f'<article><h2>Test row {i}</h2><img src="{image.name}" alt="Garment test row {i}">'
                 f'<pre>{html.escape(json.dumps(caption, indent=2, ensure_ascii=False))}</pre></article>')
(OUT / "index.html").write_text('''<!doctype html><meta charset="utf-8"><title>Fieldwork dataset sample</title>
<style>body{font-family:system-ui;margin:24px;background:#f5f3ee}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{background:white;padding:16px;border-radius:8px}img{width:100%;height:300px;object-fit:contain}pre{white-space:pre-wrap;font-size:12px}</style>
<h1>Public garment dataset: first 36 test rows</h1><p>Original dataset annotations, not Fieldwork predictions. Only front images are available in this mirror. No training was performed by this inspection.</p><main>'''
    + "".join(cards) + "</main>")
(OUT / "audit.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print(f"Gallery: {OUT / 'index.html'}")
