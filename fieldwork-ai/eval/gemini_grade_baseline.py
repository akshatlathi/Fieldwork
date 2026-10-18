"""Results-table row: plain Gemini vs our trained heads on the same test garments.

Grades the condition (1-5) and pilling (1-5) of N stratified test images with Gemini
(zero-shot, rubric in the prompt) and with models/heads.joblib, and reports QWK,
exact and within-1 for both, plus Gemini's cost/latency from logs/cost.jsonl.

    uv run python eval/gemini_grade_baseline.py 100 gemini-2.5-flash
"""

import glob
import io
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from pydantic import BaseModel, Field
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork import gemini  # noqa: E402
from fieldwork.take.grade import _heads  # noqa: E402
from google.genai import types  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "results"

RUBRIC = """Grade this second-hand garment from its photo, as a professional charity-shop sorter would.
Condition: 5 = new or like new; 4 = very good, minimal wear; 3 = good, visible wear but fully usable;
2 = fair, clear wear or minor damage; 1 = poor, damaged or heavily worn.
Pilling: 5 = no pilling; 4 = slight; 3 = moderate; 2 = heavy; 1 = very heavy.
Judge only what the photo shows."""


class Grade(BaseModel):
    condition: int = Field(ge=1, le=5)
    pilling: int = Field(ge=1, le=5)


def sample(n: int):
    f = glob.glob(str(ROOT / "data" / "hf" / "data" / "test-*.parquet"))[0]
    rows = pq.read_table(f, columns=["image", "condition", "pilling"]).to_pylist()
    rng = np.random.default_rng(11)
    by = {g: [r for r in rows if r["condition"] == g] for g in range(1, 6)}
    per = n // 5
    return [r for g in range(1, 6) for r in rng.choice(by[g], size=min(per, len(by[g])), replace=False)]


def our_model(img_bytes: list[bytes]) -> np.ndarray:
    import tempfile

    from fieldwork.take.grade import embed

    paths = []
    with tempfile.TemporaryDirectory() as d:
        for i, b in enumerate(img_bytes):
            p = Path(d) / f"{i}.jpg"
            p.write_bytes(b)
            paths.append(p)
        X = embed(paths)
    h = _heads()
    return np.column_stack([np.array(h[k]["levels"])[h[k]["head"].proba(X).argmax(1)] for k in ("condition", "pilling")])


def scores(y, p) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    return {"qwk": round(cohen_kappa_score(y, p, weights="quadratic"), 3), "exact": round(float(np.mean(y == p)), 3),
            "within_1": round(float(np.mean(np.abs(y - p) <= 1)), 3)}


def main(n: int, model: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = sample(n)
    truth = np.array([[r["condition"], r["pilling"]] for r in rows])
    gem, ok = [], []
    for i, r in enumerate(rows):
        try:
            g = gemini.generate("grade_baseline", [types.Part.from_bytes(data=r["image"]["bytes"], mime_type="image/jpeg"), RUBRIC],
                                schema=Grade, model=model, temperature=0)
            gem.append([g.condition, g.pilling])
            ok.append(i)
        except Exception as e:
            print(i, "error", str(e)[:120], flush=True)
            if "429" in str(e):
                break
        if i % 10 == 0:
            print(i, flush=True)
    ours = our_model([r["image"]["bytes"] for r in rows])
    t, o, g = truth[ok], ours[ok], np.array(gem)
    res = {"n": len(ok), "gemini_model": model,
           "condition": {"ours": scores(t[:, 0], o[:, 0]), "gemini": scores(t[:, 0], g[:, 0])},
           "pilling": {"ours": scores(t[:, 1], o[:, 1]), "gemini": scores(t[:, 1], g[:, 1])}}
    (OUT / f"grade_baseline_{model}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100, sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash")
