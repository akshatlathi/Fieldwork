"""Demo marketplace from real second-hand garment photos (no Gemini calls).

Photos + sorter labels come from the local HF test split. Everything the photo cannot
show is honest: stain/hole labels came from handling, so they go in the *declared* lane
("reported by sorter; not located in the photo"). Grades come from our own model.
Listings are marked fixture + demo; IDs d_01..d_24 are stable."""

from __future__ import annotations

import hashlib
import io
import re

import numpy as np
import pandas as pd
from PIL import Image

from . import config
from .spec import Box, Capture, Claim, ConditionRecord, Item, Lane, Severity
from .store import store

PARQUET = config.DATA_DIR / "hf" / "data" / "test-00000-of-00001.parquet"

# (row index in parquet, our type, colour override). Order = d_01..d_24.
PICKS = [
    (446, "coat", "navy"), (356, "coat", "navy"), (815, "coat", "black"),
    (84, "jacket", None), (1466, "jacket", None), (140, "jacket", None),
    (2456, "jeans", None), (1281, "jeans", None), (2915, "jeans", None), (2387, "jeans", None),
    (2964, "shirt", None), (2987, "shirt", None), (1394, "shirt", None), (2135, "shirt", None),
    (121, "dress", None), (432, "dress", None), (1357, "dress", None), (2898, "dress", None),
    (2169, "hoodie", None), (1294, "hoodie", None), (572, "hoodie", None), (2918, "hoodie", None),
    (2110, "sweater", None), (2695, "sweater", None),
]
_MAT = {"bomull": "cotton", "viskos": "viscose", "polyamid": "polyamide", "elastan": "elastane", "ull": "wool"}
_SEV = {"Minor": Severity.minor, "Major": Severity.major}


def _material(m) -> str | None:
    if not isinstance(m, str) or m.strip() in ("", "?", "unknown", "Missing"):
        return None
    s = m.strip().lower()
    for sv, en in _MAT.items():
        s = re.sub(rf"\b{sv}\b", en, s)
    return s if re.search(r"\d", s) and "?" not in s else None


def _bbox(img: Image.Image) -> tuple[int, int, int, int]:
    a = np.asarray(img.convert("RGB")).min(axis=2) < 235
    ys, xs = np.where(a)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _save(item_id: str, img: Image.Image, name: str) -> None:
    img.save(store.item_dir(item_id) / f"{name}.jpg", quality=88)


def seed_demo(n: int = 24) -> list[str]:
    from .take import grade as G

    df = pd.read_parquet(PARQUET)
    ids = []
    for k, (idx, typ, colour_override) in enumerate(PICKS[:n], 1):
        row = df.iloc[idx]
        iid = f"d_{k:02d}"
        raw = row.image["bytes"]
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        x0, y0, x1, y1 = _bbox(img)
        pad = 24
        x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)
        mid = (y0 + y1) // 2
        _save(iid, img, "f1")
        _save(iid, img.crop((x0, y0, x1, mid + 40)), "f2")  # upper half, zoomed view
        _save(iid, img.crop((x0, mid - 40, x1, y1)), "f3")  # lower half
        W, H = img.size
        whole = [Box(frame_id="f1", box_2d=[round(y0 / H * 1000), round(x0 / W * 1000), round(y1 / H * 1000), round(x1 / W * 1000)])]

        g = G.grade([store.item_dir(iid) / "f1.jpg"])
        grade_set = [int(x) for x in g["condition"]["set"]]
        colour = colour_override or str(row.colors).strip("[]'\" ").split("'")[0].lower() or None
        brand = None if str(row.brand) in ("Missing", "nan") else str(row.brand).replace("�hlens", "Åhlens")
        item = Item(type=typ, brand=brand, colour=colour, material=_material(row.material))

        claims: list[Claim] = []
        declared = []
        for attr, code in (("stains", "stain"), ("holes", "hole")):
            sev = _SEV.get(row[attr])
            if sev:
                declared.append(f"{sev.value} {code}")
                claims.append(Claim(id=f"d_{code}", lane=Lane.declared, code=code, region="whole", severity=sev,
                                    note="Reported by sorter; not located in the photo"))
        if int(row.pilling) <= 2:
            declared.append("pilling")
            claims.append(Claim(id="d_pilling", lane=Lane.declared, code="pilling", region="whole",
                                severity=Severity.major if int(row.pilling) == 1 else Severity.minor,
                                note="Reported by sorter; not located in the photo"))
        if not any(c.code in ("stain", "hole") for c in claims):
            claims.append(Claim(id="s_clean", lane=Lane.shown, code="no_stain_visible", region="front",
                                note="No stains or holes visible on the front in this photo", evidence=whole))
        if isinstance(row.smell, str):
            declared.append("odour")
            claims.append(Claim(id="d_smell", lane=Lane.declared, code="other", region="whole",
                                severity=_SEV.get(row.smell, Severity.minor), note="Sorter reported an odour"))
        claims += [
            Claim(id="cj_smell", lane=Lane.cant_judge, code="smell", region="whole", note="Smell cannot be judged from a photo"),
            Claim(id="cj_fit", lane=Lane.cant_judge, code="fit_on_body", region="whole", note="Fit on the body cannot be judged from a photo"),
            Claim(id="cj_back", lane=Lane.cant_judge, code="back_not_photographed", region="back", note="Only the front was photographed"),
        ]

        g_txt = f"{min(grade_set)}-{max(grade_set)}" if len(grade_set) > 1 else str(grade_set[0])
        text = " ".join(filter(None, [
            f"{(brand + ' ') if brand else ''}{colour or ''} {typ}".replace("  ", " ").strip().capitalize() + ".",
            f"{item.material.capitalize()}." if item.material else "",
            f"Condition grade {g_txt} of 5 (Fieldwork model).",
            f"Sorter notes: {', '.join(declared)} (not located in the photo)." if declared else "No flaws shown in the front photo.",
            "Front photo only.",
        ]))
        rec = ConditionRecord(
            id=iid, item=item, claims=claims, grade_set=grade_set, price_band=None, currency="INR",
            capture=Capture(code_expected="DEMO", code_seen=False, take_sha256=hashlib.sha256(raw).hexdigest(),
                            frames=["f1", "f2", "f3"]),
            listing_text_en=text)
        store.put_json("records", iid, rec.model_dump(mode="json"))
        store.put_json("listings", iid, {
            "id": iid, "en": text, "translations": "pending", "evidence_badge": "basic", "fixture": True, "demo": True,
            "price_source": "unset", "currency": "INR", "source_row": int(idx)})
        ids.append(iid)
    return ids


if __name__ == "__main__":
    from collections import Counter

    from . import market

    ids = seed_demo()
    recs = [ConditionRecord(**store.get_json("records", i)) for i in ids]
    print(len(ids), dict(Counter(r.item.type for r in recs)),
          "with declared flaws:", sum(any(c.lane == Lane.declared for c in r.claims) for r in recs))
    for c in market.search({"type": "coat", "colour": "navy", "exclude_defects": ["stain"]}):
        print(c["id"], c["item"]["brand"], c["item"]["colour"], c["item"]["material"], c["grade_set"], c["price_band"], c["evidence_badge"])
    print(recs[0].summary_line())
