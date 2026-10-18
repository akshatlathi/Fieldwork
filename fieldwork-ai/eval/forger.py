"""Forger vs Fieldwork.  STRESS TEST, not a guarantee.

Attack: a buyer takes a real unbox frame of the garment, has an image model paint in fake damage,
then launders the file so it looks like phone footage. Four rungs of the ladder:
  raw         the edit as returned (lossless)
  jpeg70      re-saved as JPEG q=70
  screenshot  downscaled + status/nav bar overlay (a screenshot of a screen), JPEG q=90
  rephoto     perspective warp + moire + blur + noise + JPEG q=85 (a photo of a screen, simulated)
Defences run on each rung: (1) the replay / too-perfect check from the gate, (2) the error-level and
JPEG-grid check in fieldwork/forensics.py, (3) the full unbox gate. The forger "wins" a rung when the
gate returns `differs` (damage accepted as real) and neither (1) nor (2) flagged it.

    uv run python eval/forger.py --items ev_garment_01,ev_garment_02 --per-item 2
Needs records + unbox frames already in the store (run eval/run_eval.py first).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fieldwork import config, forensics, imgedit  # noqa: E402
from fieldwork.stats import fmt, rate  # noqa: E402

RUNGS = ["raw", "jpeg70", "screenshot", "rephoto"]
DAMAGE = ["a coin-sized dark stain", "a small hole about 8 mm with frayed edges", "a visible pulled snag with a thread loop"]
LABEL = "STRESS TEST on a small sample: not a guarantee against forgery."


# ---------- laundering ladder (each returns a BGR image; save() chooses the container) ----------
def jpeg(img: np.ndarray, q: int) -> np.ndarray:
    return cv2.imdecode(cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])[1], cv2.IMREAD_COLOR)


def screenshot(img: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = img.shape[:2]
    s = cv2.resize(img, (round(w * 0.75), round(h * 0.75)), interpolation=cv2.INTER_AREA)
    sh, sw = s.shape[:2]
    bar = max(18, round(sh * 0.07))
    canvas = np.full((sh + 2 * bar, sw, 3), 245, np.uint8)
    canvas[bar:bar + sh] = s
    canvas[:bar] = (30, 30, 30)  # status bar
    cv2.putText(canvas, "9:41", (10, bar - 6), cv2.FONT_HERSHEY_SIMPLEX, bar / 40, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.rectangle(canvas, (sw - 50, 5), (sw - 12, bar - 5), (255, 255, 255), 1)
    canvas[-bar:] = (235, 235, 235)  # nav bar
    cv2.rectangle(canvas, (sw // 2 - 40, sh + bar + bar // 2 - 2), (sw // 2 + 40, sh + bar + bar // 2 + 2), (60, 60, 60), -1)
    return jpeg(canvas, 90)


def rephoto(img: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = img.shape[:2]
    j = 0.03
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = src + np.float32([[rng.uniform(-j, j) * w, rng.uniform(-j, j) * h] for _ in range(4)])
    out = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    th = rng.uniform(0.05, 0.25)
    g1 = np.sin(2 * np.pi * xx / 3.0)
    g2 = np.sin(2 * np.pi * (xx * np.cos(th) + yy * np.sin(th)) / 3.1)
    out *= (1 + 0.05 * g1 * g2)[..., None]  # moire from two near-equal gratings
    out = cv2.GaussianBlur(out, (0, 0), 1.2)
    nrng = np.random.default_rng(rng.randrange(2**31))
    out += nrng.normal(0, 4, out.shape).astype(np.float32)
    return jpeg(np.clip(out, 0, 255).astype(np.uint8), 85)


def ladder(forged: np.ndarray, rng: random.Random) -> dict[str, np.ndarray]:
    return {"raw": forged, "jpeg70": jpeg(forged, 70), "screenshot": screenshot(forged, rng), "rephoto": rephoto(forged, rng)}


def save(rung: str, img: np.ndarray, path_noext: Path) -> Path:
    p = path_noext.with_suffix(".png" if rung == "raw" else ".jpg")
    cv2.imwrite(str(p), img, [] if rung == "raw" else [cv2.IMWRITE_JPEG_QUALITY, 95])
    return p


# ---------- defences ----------
def run_defences(record, listing: dict[str, Path], forged_path: Path, work: Path, seed: int = 0) -> dict:
    from fieldwork.unbox import gate
    from fieldwork.unbox.pipeline import pair_frames

    f = forensics.check(forged_path)
    pairs = pair_frames(listing, [forged_path])
    replay = any(gate._near_identical(listing[fid], p) for fid, p in pairs)
    res = gate.check(record, listing, pairs, work, seed=seed)
    return {"replay_flag": replay, "forensics_flag": f.flagged, "ela": f.ela_score, "grid": f.grid_score,
            "gate_verdict": res.verdict, "gate_flags": res.flags,
            "forger_wins": res.verdict == "differs" and not f.flagged and not replay}


def forge(item_ids: list[str], per_item: int, out: Path, seed: int = 0, edit=None) -> dict:
    from fieldwork.spec import ConditionRecord
    from fieldwork.store import store

    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    trials: list[dict] = []
    clean_flags: list[bool] = []
    for iid in item_ids:
        raw = store.get_json("records", iid)
        frames = sorted((store.item_dir(iid) / "unbox" / "frames").glob("*.jpg"))
        if raw is None or not frames:
            continue
        rec = ConditionRecord(**raw)
        listing = {fid: store.item_dir(iid) / f"{fid}.jpg" for fid in rec.capture.frames}
        for k in range(per_item):
            base_path = rng.choice(frames)
            clean_flags.append(forensics.check(base_path).flagged)  # false-alarm baseline on a genuine frame
            base = cv2.imread(str(base_path))
            prompt = (f"Edit this photo of a garment: add {rng.choice(DAMAGE)} somewhere on the fabric so it looks real. "
                      "Keep framing, lighting, colour and everything else unchanged.")
            try:
                forged = (edit or imgedit.edit_image)(prompt, [base_path], task="forger_edit")
            except Exception as e:
                trials.append({"item": iid, "k": k, "error": f"{type(e).__name__}: {e}"[:200]})
                continue
            if forged.shape[:2] != base.shape[:2]:
                forged = cv2.resize(forged, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_AREA)
            for rung, img in ladder(forged, rng).items():
                p = save(rung, img, out / f"{iid}_{k}_{rung}")
                trials.append({"item": iid, "k": k, "rung": rung, "file": str(p),
                               **run_defences(rec, listing, p, out / "work" / f"{iid}_{k}_{rung}", seed)})
    return summarise(trials, clean_flags)


def summarise(trials: list[dict], clean_flags: list[bool]) -> dict:
    per = {}
    ok = [t for t in trials if "rung" in t]
    for r in RUNGS:
        xs = [t for t in ok if t["rung"] == r]
        per[r] = {"forger_wins": rate(sum(t["forger_wins"] for t in xs), len(xs)),
                  "caught_by_forensics": rate(sum(t["forensics_flag"] for t in xs), len(xs)),
                  "caught_by_replay_check": rate(sum(t["replay_flag"] for t in xs), len(xs)),
                  "gate_says_differs": rate(sum(t["gate_verdict"] == "differs" for t in xs), len(xs))}
    return {"label": LABEL, "per_rung": per, "forensics_false_alarm_on_genuine_frames": rate(sum(clean_flags), len(clean_flags)),
            "errors": [t for t in trials if "error" in t], "trials": ok}


def write_md(res: dict, path: Path) -> None:
    L = ["# Forger vs Fieldwork", "", f"**{res['label']}** Win = the unbox gate accepted the fake damage as a real change and no forgery check flagged it.", "",
         "| Laundering rung | Forger wins | Caught by forensics | Caught by replay check | Gate says 'differs' |", "|---|---|---|---|---|"]
    for r, v in res["per_rung"].items():
        L.append(f"| {r} | {fmt(v['forger_wins'])} | {fmt(v['caught_by_forensics'])} | {fmt(v['caught_by_replay_check'])} | {fmt(v['gate_says_differs'])} |")
    L += ["", f"Forensics false alarms on genuine unbox frames: {fmt(res['forensics_false_alarm_on_genuine_frames'])} (thresholds are uncalibrated).",
          "", "Reading: a forged take can only trigger a refund path when the gate says 'differs'; flagged takes become a close-up request, not a refund."]
    path.write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", help="comma-separated store item ids (default: every record with unbox frames)")
    ap.add_argument("--per-item", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=config.DATA_DIR / "results" / "forger")
    a = ap.parse_args(argv)
    from fieldwork.store import store

    ids = a.items.split(",") if a.items else [r["id"] for r in store.list_json("records")]
    res = forge(ids, a.per_item, a.out, a.seed)
    (a.out.parent / "forger.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    write_md(res, a.out.parent / "FORGER.md")
    for r, v in res["per_rung"].items():
        print(r, "forger wins", fmt(v["forger_wins"]))
    print(LABEL)


if __name__ == "__main__":
    main()
