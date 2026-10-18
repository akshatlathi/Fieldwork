"""Day-1 test: does Gemini with code execution (Agentic Vision: crop/zoom itself) find
stains and holes better than plain Gemini?

Sample: N garments labelled with a Major stain or hole, N with neither (HF test split).
Writes data/day1/agentic.jsonl and prints accuracy for both arms.

    uv run python eval/day1_agentic.py 20
"""

import glob
import io
import json
import random
import sys
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fieldwork import gemini  # noqa: E402
from google.genai import types  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "day1"

MODEL = "gemini-3.5-flash"  # same model for both arms; supports code execution on images

PROMPT = (
    "You inspect a used garment photo for a resale marketplace. "
    "Is there a visible stain, hole or tear on the garment? Only report what is visible; "
    "if unsure, say so. Give the location in plain words."
)


class Finding(BaseModel):
    defect_visible: bool
    kinds: list[str]
    where: str
    unsure: bool


def sample(n: int):
    f = glob.glob(str(ROOT / "data" / "hf" / "data" / "test-*.parquet"))[0]
    rows = pq.read_table(f, columns=["image", "stains", "holes"]).to_pylist()
    pos = [r for r in rows if r["stains"] == "Major" or r["holes"] == "Major"]
    neg = [r for r in rows if not r["stains"] and not r["holes"]]
    random.seed(7)
    return [(r, True) for r in random.sample(pos, n)] + [(r, False) for r in random.sample(neg, n)]


def run(img: bytes, agentic: bool) -> Finding:
    part = types.Part.from_bytes(data=img, mime_type="image/jpeg")
    if not agentic:
        return gemini.generate("day1_plain", [part, PROMPT], schema=Finding, model=MODEL, temperature=0)
    # Code execution can't be combined with a response schema, so ask for JSON at the end.
    resp = gemini.generate(
        "day1_agentic",
        [part, PROMPT + " Use code to crop and zoom into suspicious regions before deciding. "
         'End your answer with one line of JSON: {"defect_visible": bool, "kinds": [..], "where": str, "unsure": bool}'],
        code_execution=True,
        model=MODEL,
        temperature=0,
    )
    text = "".join(p.text or "" for p in resp.candidates[0].content.parts if getattr(p, "text", None))
    line = text[text.rfind("{") : text.rfind("}") + 1]
    return Finding.model_validate_json(line)


def main(n: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    score = {"plain": [0, 0], "agentic": [0, 0]}
    with open(OUT / "agentic.jsonl", "w", encoding="utf-8", buffering=1) as fh:
        for i, (row, truth) in enumerate(sample(n)):
            img = row["image"]["bytes"]
            rec = {"i": i, "truth": truth, "stains": row["stains"], "holes": row["holes"]}
            for arm in ("plain", "agentic"):
                try:
                    f = run(img, arm == "agentic")
                    rec[arm] = f.model_dump()
                    score[arm][0] += int(f.defect_visible == truth)
                    score[arm][1] += 1
                except Exception as e:  # keep going; log the failure
                    rec[arm] = {"error": str(e)[:200]}
            fh.write(json.dumps(rec) + "\n")
            print(i, truth, {a: rec[a].get("defect_visible") for a in ("plain", "agentic")}, flush=True)
    for arm, (ok, tot) in score.items():
        print(f"{arm}: {ok}/{tot} correct")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
