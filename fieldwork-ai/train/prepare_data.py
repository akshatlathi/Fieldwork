"""Download the public training mirror; safe to resume interrupted downloads."""
from pathlib import Path
import truststore
truststore.inject_into_ssl()
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parent.parent
snapshot_download(
    "fnauman/fashion-second-hand-front-only-rgb", repo_type="dataset",
    allow_patterns=["README.md", "data/*.parquet"],
    local_dir=root / "data" / "hf", max_workers=2,
)
print("Dataset ready. Run python train/embed.py --full, then train/heads.py --out <run-folder>.")
