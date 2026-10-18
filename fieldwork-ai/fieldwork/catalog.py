"""Buyer-facing media and prices; keep source paths relative to the item store."""
from pathlib import PurePosixPath


def listing_media(storage, record, listing):
    draft = storage.get_json("seller_drafts", record.id) or {}
    media = []
    counts = {"photo": 0, "video": 0}
    for attempt in draft.get("attempts", []):
        if attempt.get("status") != "completed":
            continue
        for source in attempt.get("sources", []):
            path = source["path"]
            kind = "video" if PurePosixPath(path).suffix.lower() in {".mp4", ".mov", ".webm", ".m4v"} else "photo"
            counts[kind] += 1
            media.append({"kind": kind, "label": f"Seller {kind} {counts[kind]}",
                          "url": storage.media_url(record.id, path)})
    # Legacy/demo listings have retained frames but no seller draft.
    if not media and (not listing.get("fixture") or listing.get("demo")):
        media = [{"kind": "photo", "label": f"Listing view {fid}",
                  "url": storage.media_url(record.id, f"{fid}.jpg")} for fid in record.capture.frames]
    if media and not any(m["kind"] == "photo" for m in media) and record.capture.frames:
        fid = record.capture.frames[0]
        media.insert(0, {"kind": "photo", "label": f"Seller video preview · {fid}",
                         "url": storage.media_url(record.id, f"{fid}.jpg")})
    return media


def public_record(storage, record):
    result = record.public()
    asking = purchase_price(storage, record)
    result.price_band = (asking, asking) if asking else None
    result.currency = "INR"
    return result


def purchase_price(storage, record):
    listing = storage.get_json("listings", record.id) or {}
    return listing.get("asking_price") if listing.get("price_source") == "seller" else None


def purchased_items(storage):
    # Sample fixtures (fx_*/d_*) stay listed so every judge can buy them repeatedly; each purchase has its own mandate.
    return {m["item_id"] for m in storage.list_json("mandates")
            if m["status"] in ("held", "released", "partial") and not (storage.get_json("listings", m["item_id"]) or {}).get("fixture")}
