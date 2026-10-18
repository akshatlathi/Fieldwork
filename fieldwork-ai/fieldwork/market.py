"""Evidence-first search over condition records. Filters on shown claims and grade sets,
never on seller prose. `seed_fixtures()` writes hand-made records for tests and demo fallback."""

from __future__ import annotations

from .spec import Capture, Claim, ConditionRecord, Item, Lane, Severity
from .store import store
from .catalog import listing_media, purchase_price, purchased_items
import re


def _normal(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _listing_map() -> dict[str, dict]:
    return {l["id"]: l for l in store.list_json("listings") if "id" in l}


def _flaws(r: ConditionRecord) -> list[dict]:
    return [{"code": c.code, "region": c.region, "severity": c.severity.value, "claim_id": c.id}
            for c in r.claims if c.lane == Lane.shown and c.severity != Severity.none]


def _declared_flaws(r: ConditionRecord) -> list[dict]:
    return [{"code": c.code, "region": c.region, "severity": c.severity.value, "claim_id": c.id}
            for c in r.claims if c.lane == Lane.declared and (c.severity != Severity.none or c.id.startswith("seller_issue_"))]


def _card(r: ConditionRecord, listing: dict) -> dict:
    badge = listing.get("evidence_badge") or ("strong" if r.capture.code_seen else "basic")
    return {
        "id": r.id,
        "item": r.item.model_dump(),
        "grade_set": r.grade_set,
        "price_band": [listing["asking_price"]]*2 if listing.get("price_source") == "seller" else None,
        "currency": listing.get("currency", "INR"),
        "negotiation_enabled": listing.get("negotiation_enabled", False),
        "shown_flaws": _flaws(r),
        "declared_flaws": _declared_flaws(r),
        "cant_judge": sorted({c.region for c in r.claims if c.lane == Lane.cant_judge}),
        "evidence_badge": badge,
        "summary_line": r.summary_line(),
        "media": listing_media(store, r, listing),
        "purchase_price": purchase_price(store, r),
        "price_source": listing.get("price_source", "unset"),
    }


def search(query: dict) -> list[dict]:
    """query keys: type, colour, max_price, min_grade, exclude_defects (list of codes), size_label (or size)."""
    q = {k: v for k, v in (query or {}).items() if v not in (None, "", [])}
    lmap = _listing_map()
    unavailable = purchased_items(store)
    out = []
    for raw in store.list_json("records"):
        r = ConditionRecord(**raw)
        if r.id in unavailable:
            continue
        lifecycle = store.get_json("seller_drafts", r.id)
        if lifecycle is not None and lifecycle.get("status") != "published":
            continue
        if lmap.get(r.id, {}).get("publication_status", "published") != "published":
            continue
        if "type" in q and _normal(q["type"]) not in _normal(r.item.type):
            continue
        if "brand" in q and _normal(q["brand"]) not in _normal(r.item.brand or ""):
            continue
        if "colour" in q and q["colour"].lower() not in (r.item.colour or "").lower():
            continue
        price = purchase_price(store, r)
        if "currency" in q and q["currency"].upper() != lmap.get(r.id, {}).get("currency", "INR").upper():
            continue
        if "max_price" in q and (price is None or price > q["max_price"]):
            continue
        if "min_grade" in q and (not r.grade_set or min(r.grade_set) < q["min_grade"]):
            continue
        size = q.get("size_label") or q.get("size")
        if size and size.lower() not in (r.item.size_label or "").lower():
            continue
        bad = {f["code"] for f in _flaws(r) + _declared_flaws(r)}  # sorter-reported flaws also exclude
        if any(c in bad for c in q.get("exclude_defects", [])):
            continue
        out.append(_card(r, lmap.get(r.id, {})))
    return out


def _rec(id, typ, brand, size, colour, material, grades, band, claims, text, code_seen=True, price=None) -> tuple[dict, dict]:
    r = ConditionRecord(
        id=id, item=Item(type=typ, brand=brand, size_label=size, colour=colour, material=material),
        claims=claims, grade_set=grades, price_band=band,
        capture=Capture(code_expected="K7Q2", code_seen=code_seen, take_sha256="fixture", frames=["f1", "f2"]),
        listing_text_en=text)
    l = {"id": id, "en": text, "evidence_badge": "strong" if code_seen else "basic", "fixture": True}
    if price:
        l.update(price_source="seller", asking_price=price, currency="INR")
    return r.model_dump(mode="json"), l


def _s(i, code, region, sev, note) -> Claim:
    return Claim(id=i, lane=Lane.shown, code=code, region=region, severity=sev, note=note)


def _cj(i, region, note) -> Claim:
    return Claim(id=i, lane=Lane.cant_judge, code="feel_or_smell", region=region, note=note)


def seed_fixtures() -> list[str]:
    N, M, m = Severity.none, Severity.major, Severity.minor
    fx = [
        _rec("fx_coat_navy_clean", "shirt", "celio", "L", "navy", None, [4, 5], (1000, 1400),
             [_s("c1", "no_stain_visible", "whole", N, "No stains visible on the front, collar or cuffs"),
              _s("c2", "no_hole_visible", "whole", N, "No holes or tears visible"),
              _cj("c3", "whole", "Smell and fabric feel cannot be judged from the take")],
             "Navy long-sleeve button-front shirt, clean, no flaws shown.", price=1200),
        _rec("fx_coat_navy_stain", "trousers", "MNG", "36", "cream", None, [3], (700, 1100),
             [_s("c1", "stain", "ankle", m, "Mud stains near the ankle area"),
              _s("c2", "no_hole_visible", "whole", N, "No holes visible"),
              _cj("c3", "whole", "Smell cannot be judged from the take")],
             "Cream trousers, mud stains near the ankle.", code_seen=False, price=900),
        _rec("fx_jacket_denim", "jeans", "Levi's", "W36 L32", "blue", "denim", [4, 5], (2200, 2800),
             [_s("c1", "no_stain_visible", "whole", N, "No stains visible"),
              _s("c2", "no_hole_visible", "whole", N, "No holes visible")],
             "Blue Levi's 513 jeans, no flaws shown.", price=2400),
        _rec("fx_jacket_black_bomber", "t-shirt", "SF Jeans", "L", "black", None, [4, 5], (700, 1000),
             [_s("c1", "no_stain_visible", "whole", N, "No stains visible"),
              _s("c2", "no_hole_visible", "whole", N, "No holes visible")],
             "Black short-sleeve graphic T-shirt, no flaws shown.", price=800),
        _rec("fx_jeans_indigo", "jeans", "GANT", "36", "charcoal", "denim", [3], (900, 1400),
             [_s("c1", "hole", "hip", M, "Hole near the hip area")],
             "Washed charcoal GANT jeans, hole near the hip.", price=1100),
        _rec("fx_coat_grey_wool", "polo shirt", "U.S. Polo Assn.", None, "white", None, [4, 5], (1300, 1800),
             [_s("c1", "no_stain_visible", "whole", N, "No stains visible"),
              _s("c2", "no_hole_visible", "whole", N, "No holes visible")],
             "White polo with dark collar trim and chest logo, no flaws shown.", price=1500),
    ]
    import shutil
    from pathlib import Path
    for rec, lst in fx:
        media = Path(__file__).parent / "fixture_media" / rec["id"]
        if media.is_dir():  # tracked fixture photos -> item store (store/ is gitignored)
            for f in media.glob("*.jpg"):
                shutil.copyfile(f, store.item_dir(rec["id"]) / f.name)
        store.put_json("records", rec["id"], rec)
        store.put_json("listings", rec["id"], lst)
    return [r["id"] for r, _ in fx]
