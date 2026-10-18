"""One-command evaluation over data/garments/* (folder layout: ../CAPTURE-GUIDE.md).

    uv run python eval/run_eval.py                       # take + unbox + look-alike pairs
    uv run python eval/run_eval.py --arm both            # also the Agentic Vision ablation (flaw inspector)
    uv run python eval/run_eval.py --arm-only both       # ablation only, on records already in the store

Writes data/results/eval.json and data/results/RESULTS.md. Wording rule: a take is "consistent with
the listing", never "verified". N is always printed next to every rate, with Clopper-Pearson 95% CIs.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fieldwork import config  # noqa: E402
from fieldwork.stats import fmt, rate  # noqa: E402

# LIST PRICES, USD per 1M tokens (input, output). PLACEHOLDERS: update from the current Google price page
# before quoting any cost. Thinking tokens are billed as output. Unknown models fall back to "default".
PRICES_USD_PER_M = {
    "default": (0.30, 2.50),
    "gemini-3.8-flash": (0.30, 2.50),
    "gemini-3.7-flash": (0.30, 2.50),
    "gemini-3.5-flash": (0.30, 2.50),
    "gemini-3.5-flash-lite": (0.10, 0.40),
}

# Words in notes.txt -> defect codes (ground truth for the flaw-inspector ablation).
NOTE_WORDS = {"stain": "stain", "hole": "hole", "tear": "tear", "pill": "pilling", "fad": "fading", "snag": "snag",
              "seam": "loose_seam", "button": "missing_button", "zip": "broken_zip", "discolo": "discolour"}


# ---------- ground truth parsing ----------
def parse_changes(text: str | None) -> dict:
    """changes.txt: 'no change' (any case) or one planted change per line (what + where)."""
    lines = [ln.strip(" -*\t") for ln in (text or "").splitlines() if ln.strip()]
    if not lines or all(re.match(r"(?i)^(no[ -]?change|none|nothing|n/?a)\b", ln) for ln in lines):
        return {"planted": False, "n_changes": 0, "changes": []}
    return {"planted": True, "n_changes": len(lines), "changes": lines}


def parse_notes(text: str | None) -> dict:
    text = text or ""
    m = re.search(r"(?i)\bcode\W+([A-Z0-9]{4})\b", text)
    codes = sorted({c for w, c in NOTE_WORDS.items() if re.search(w, text, re.I) and not re.search(rf"\bno\s+{w}", text, re.I)})
    return {"code": m.group(1) if m else None, "flaw_codes": codes}


def read(p: Path) -> str | None:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None


def discover(root: Path) -> list[Path]:
    return sorted(d for d in root.iterdir() if d.is_dir()) if root.exists() else []


def lookalike_partner(d: Path) -> Path | None:
    """garment-20b -> garment-20a (its listing record is the one b is checked against)."""
    m = re.fullmatch(r"(.+?)(\d+)b", d.name)
    if not m:
        return None
    a = d.with_name(f"{m.group(1)}{m.group(2)}a")
    return a if a.is_dir() else None


def item_id_for(d: Path) -> str:
    return f"ev_{d.name.replace('-', '_')}"


# ---------- cost / latency ----------
def _cost_path() -> Path:
    return config.LOG_DIR / "cost.jsonl"


def _offset() -> int:
    p = _cost_path()
    return p.stat().st_size if p.exists() else 0


def usd(row: dict) -> float:
    pin, pout = PRICES_USD_PER_M.get(row.get("model"), PRICES_USD_PER_M["default"])
    return ((row.get("in_tokens") or 0) * pin + ((row.get("out_tokens") or 0) + (row.get("thinking_tokens") or 0)) * pout) / 1e6


def _rows_since(off: int) -> list[dict]:
    p = _cost_path()
    if not p.exists():
        return []
    with open(p, "rb") as fh:
        fh.seek(off)
        return [json.loads(ln) for ln in fh.read().decode("utf-8").splitlines() if ln.strip()]


class Stage:
    """Context manager: wall-clock seconds + Gemini calls/cost logged while it ran."""

    def __init__(self, store: list[dict], name: str, garment: str):
        self.store, self.name, self.garment = store, name, garment

    def __enter__(self):
        self.t0, self.off = time.time(), _offset()
        return self

    def __exit__(self, *exc):
        rows = _rows_since(self.off)
        self.store.append({"stage": self.name, "garment": self.garment, "seconds": round(time.time() - self.t0, 2),
                           "gemini_calls": len(rows), "usd": round(sum(usd(r) for r in rows), 5),
                           "in_tokens": sum(r.get("in_tokens") or 0 for r in rows),
                           "out_tokens": sum((r.get("out_tokens") or 0) + (r.get("thinking_tokens") or 0) for r in rows)})
        return False


# ---------- per-garment run ----------
def run_garment(d: Path, stages: list[dict], run_take=None, run_unbox=None) -> dict:
    if run_take is None:
        from fieldwork.take.pipeline import run_take
    if run_unbox is None:
        from fieldwork.unbox.pipeline import run_unbox
    from fieldwork.spec import ConditionRecord
    from fieldwork.store import store

    item_id = item_id_for(d)
    notes = parse_notes(read(d / "notes.txt"))
    truth = parse_changes(read(d / "unbox" / "changes.txt"))
    row = {"garment": d.name, "item_id": item_id, "notes": notes, "truth": truth, "partner": None}

    photos = sorted(d.glob("photo-*.jpg"))
    take_video = d / "take.mp4"
    with Stage(stages, "take", d.name):
        rec = run_take(take_video, notes["code"], item_id=item_id) if take_video.exists() else \
            run_take(None, None, photos=photos, item_id=item_id)
    row["record_summary"] = rec.summary_line()
    row["shown_flaws"] = sorted({c.code for c in rec.claims if c.lane.value == "shown" and c.severity.value != "none"})

    ub = d / "unbox" / "take.mp4"
    if ub.exists():
        with Stage(stages, "unbox", d.name):
            res = run_unbox(rec, video=ub, seed=0)
        row["unbox"] = {"verdict": res.verdict, "flags": res.flags, "closeup_request": res.closeup_request,
                        "pairs_aligned": res.pairs_aligned, "pairs_total": res.pairs_total,
                        "findings": [{"kind": f.kind, "what": f.what, "reason": f.reason} for f in res.findings]}

    a = lookalike_partner(d)
    if a is not None and take_video.exists():  # b's listing take, checked against a's record: must NOT be "consistent"
        a_raw = store.get_json("records", item_id_for(a))
        if a_raw is not None:
            with Stage(stages, "unbox_lookalike", d.name):
                res = run_unbox(ConditionRecord(**a_raw), video=take_video, seed=0)  # note: overwrites a's stored unbox result
            row["partner"] = a.name
            row["lookalike"] = {"verdict": res.verdict, "flags": res.flags,
                                "findings": [{"kind": f.kind, "what": f.what} for f in res.findings]}
    return row


def metrics(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    planted = [r for r in ok if r["truth"]["planted"] and "unbox" in r]
    clean = [r for r in ok if not r["truth"]["planted"] and "unbox" in r]
    look = [r for r in ok if "lookalike" in r]
    allruns = [r["unbox"]["verdict"] for r in ok if "unbox" in r] + [r["lookalike"]["verdict"] for r in look]
    return {
        "change_detection_recall": rate(sum(r["unbox"]["verdict"] == "differs" for r in planted), len(planted)),
        "false_differs_on_no_change": rate(sum(r["unbox"]["verdict"] == "differs" for r in clean), len(clean)),
        "false_consistent_on_lookalikes": rate(sum(r["lookalike"]["verdict"] == "consistent" for r in look), len(look)),
        "cant_tell_share": rate(sum(v == "cant_tell" for v in allruns), len(allruns)),
        "planted_changes_total": sum(r["truth"]["n_changes"] for r in planted),
        "garments_with_errors": [{"garment": r["garment"], "error": r["error"]} for r in rows if "error" in r],
    }


def summarise_stages(stages: list[dict]) -> dict:
    out = {}
    for name in sorted({s["stage"] for s in stages}):
        xs = [s for s in stages if s["stage"] == name]
        secs = sorted(s["seconds"] for s in xs)
        out[name] = {"n": len(xs), "seconds_mean": round(statistics.mean(secs), 1), "seconds_p50": round(statistics.median(secs), 1),
                     "seconds_max": secs[-1], "gemini_calls_mean": round(statistics.mean(s["gemini_calls"] for s in xs), 1),
                     "usd_mean": round(statistics.mean(s["usd"] for s in xs), 4), "usd_total": round(sum(s["usd"] for s in xs), 4)}
    return out


# ---------- flaw-inspector ablation ----------
def run_arms(dirs: list[Path], arm: str, max_frames: int, inspect_fns: dict | None = None) -> dict:
    from fieldwork.store import store
    from fieldwork.take import flaws

    fns = inspect_fns or {"agentic": flaws.inspect, "plain": flaws.inspect_plain}
    arms = ["agentic", "plain"] if arm == "both" else [arm]
    res: dict = {a: {"noted": 0, "found_noted": 0, "extra_codes": 0, "frames": 0, "errors": 0, "seconds": 0.0, "usd": 0.0} for a in arms}
    per: list[dict] = []
    for d in dirs:
        iid = item_id_for(d)
        truth = set(parse_notes(read(d / "notes.txt"))["flaw_codes"])
        idir = store.item_dir(iid)
        frames = sorted(idir.glob("f[0-9]*.jpg"))[:max_frames] or sorted(idir.glob("p[0-9]*.jpg"))[:max_frames]
        if not frames:
            continue
        for a in arms:
            found: set[str] = set()
            stg: list[dict] = []
            with Stage(stg, a, d.name):
                for f in frames:
                    try:
                        found |= {x.code for x in fns[a](f)}
                        res[a]["frames"] += 1
                    except Exception as e:  # keep going; errors are counted, not hidden
                        res[a]["errors"] += 1
                        per.append({"garment": d.name, "arm": a, "error": f"{type(e).__name__}: {e}"[:200]})
            res[a]["noted"] += len(truth)
            res[a]["found_noted"] += len(truth & found)
            res[a]["extra_codes"] += len(found - truth)
            res[a]["seconds"] += stg[0]["seconds"]
            res[a]["usd"] += stg[0]["usd"]
            per.append({"garment": d.name, "arm": a, "noted": sorted(truth), "found": sorted(found)})
    for a in arms:
        res[a]["recall_of_noted_flaws"] = rate(res[a]["found_noted"], res[a]["noted"])
        res[a]["seconds"], res[a]["usd"] = round(res[a]["seconds"], 1), round(res[a]["usd"], 4)
    return {"arms": res, "per_garment": per,
            "caveat": "Truth = flaws named in notes.txt. 'extra_codes' are flaws found that the notes do not mention: unreviewed, may be real or false."}


# ---------- report ----------
def write_markdown(res: dict, path: Path) -> None:
    m, L = res["metrics"], []
    L += ["# Fieldwork evaluation results", "",
          f"Run {res['meta']['date']}; {res['meta']['garments']} garment folders. Unit of detection is the whole take: a take is 'differs' if the check flags a change.",
          "Wording: a take that passes is **consistent with the listing**; Fieldwork makes no claim beyond consistency with the listing. Intervals are Clopper-Pearson 95%.", "",
          "| Measure | Result | What it means |", "|---|---|---|",
          f"| Change detection recall (planted changes) | {fmt(m['change_detection_recall'])} | Planted marker/lint/pin take flagged as differs |",
          f"| False 'differs' on no-change takes | {fmt(m['false_differs_on_no_change'])} | Honest take wrongly flagged |",
          f"| False 'consistent' on look-alike garments | {fmt(m['false_consistent_on_lookalikes'])} | Different but similar garment passed as consistent |",
          f"| Share 'cant_tell' (all unbox runs) | {fmt(m['cant_tell_share'])} | Sent to a close-up request; money does not move |", ""]
    if res.get("latency_cost"):
        L += ["## Latency and Gemini cost per stage", "", "Cost uses list prices in `eval/run_eval.py` (PRICES_USD_PER_M): placeholders until updated.", "",
              "| Stage | N | Mean s | Median s | Max s | Gemini calls | Mean USD | Total USD |", "|---|---|---|---|---|---|---|---|"]
        for k, v in res["latency_cost"].items():
            L.append(f"| {k} | {v['n']} | {v['seconds_mean']} | {v['seconds_p50']} | {v['seconds_max']} | {v['gemini_calls_mean']} | {v['usd_mean']} | {v['usd_total']} |")
        L.append("")
    if res.get("ablation"):
        L += ["## Flaw inspector: Agentic Vision ablation", "", res["ablation"]["caveat"], "",
              "| Arm | Recall of noted flaws | Extra codes (unreviewed) | Frame errors | Seconds | USD |", "|---|---|---|---|---|---|"]
        for a, v in res["ablation"]["arms"].items():
            L.append(f"| {a} | {fmt(v['recall_of_noted_flaws'])} | {v['extra_codes']} | {v['errors']} | {v['seconds']} | {v['usd']} |")
        L.append("")
    if m["garments_with_errors"]:
        L += ["## Garments that errored (excluded from rates)", ""] + [f"- {e['garment']}: {e['error']}" for e in m["garments_with_errors"]] + [""]
    L += ["## Limits", "", "- Few garments: wide intervals; treat as a pilot, not a benchmark.",
          "- Planted changes are small removable marks made by us, not adversarial edits (see eval/forger.py for those).",
          "- Look-alike pairs are run in one direction (b's listing take against a's record).", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--garments", type=Path, default=config.DATA_DIR / "garments")
    ap.add_argument("--out", type=Path, default=config.DATA_DIR / "results")
    ap.add_argument("--limit", type=int, default=0, help="only the first N garment folders")
    ap.add_argument("--arm", choices=["none", "agentic", "plain", "both"], default="none", help="also run the flaw-inspector ablation")
    ap.add_argument("--arm-only", choices=["agentic", "plain", "both"], help="ablation only, using records already in the store")
    ap.add_argument("--arm-frames", type=int, default=4)
    a = ap.parse_args(argv)

    dirs = discover(a.garments)[: a.limit or None]
    if not dirs:
        sys.exit(f"no garment folders in {a.garments}")
    a.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    stages: list[dict] = []
    if not a.arm_only:
        for d in dirs:
            try:
                rows.append(run_garment(d, stages))
            except Exception as e:  # one bad garment must not sink the run
                rows.append({"garment": d.name, "error": f"{type(e).__name__}: {e}"[:300]})
            print(f"{d.name}: {rows[-1].get('unbox', {}).get('verdict', rows[-1].get('error', 'take only'))}", flush=True)
    res = {"meta": {"date": time.strftime("%Y-%m-%d"), "garments": len(dirs), "prices": PRICES_USD_PER_M},
           "garments": rows, "metrics": metrics(rows), "latency_cost": summarise_stages(stages)}
    arm = a.arm_only or (a.arm if a.arm != "none" else None)
    abl = run_arms(dirs, arm, a.arm_frames) if arm else None
    if a.arm_only and (a.out / "eval.json").exists():  # keep the main results from the earlier run
        res = json.loads((a.out / "eval.json").read_text(encoding="utf-8"))
    if abl:
        res["ablation"] = abl
    (a.out / "eval.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(res, a.out / "RESULTS.md")
    print(f"wrote {a.out / 'eval.json'} and RESULTS.md")
    return res


if __name__ == "__main__":
    main()
