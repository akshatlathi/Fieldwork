"""Fieldwork HTTP API. Run: uv run uvicorn fieldwork.api:app --port 8000"""

from __future__ import annotations

import os
import tempfile
import secrets
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, Depends
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import ask as ask_mod
from . import escrow, market, human_review as reviews
from . import seller_review
from . import pricing
from .spec import ConditionRecord
from .store import store

app = FastAPI(title="Fieldwork")
app.add_middleware(CORSMiddleware, allow_origins=[*[o for o in os.getenv("FW_CORS_ORIGINS", "").split(",") if o], "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3100", "http://127.0.0.1:3100"],
                   allow_methods=["*"], allow_headers=["*"])


def _record(item_id: str) -> ConditionRecord:
    raw = store.get_json("records", item_id)
    if raw is None:
        raise HTTPException(404, f"unknown item {item_id}")
    return ConditionRecord(**raw)


async def _save_upload(f: UploadFile, d: Path, max_bytes: int | None = None) -> Path:
    p = d / (uuid.uuid4().hex[:8] + "_" + Path(f.filename or "upload.bin").name)
    size = 0
    with p.open("wb") as stream:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if max_bytes is not None and size > max_bytes:
                raise HTTPException(413, "Video is too large. Choose a clip under 50 MB.")
            stream.write(chunk)
    return p


@app.get("/health")
def health():
    return {"ok": True, "records": len(store.list_json("records"))}


@app.post("/take")
async def take(code: str = Form(""), video: UploadFile | None = File(None), photos: list[UploadFile] = File(default=[])):
    if video is None and not photos:
        raise HTTPException(400, "send a video or photos")
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        from .video import SOURCE_LIMIT
        v = await _save_upload(video, d, SOURCE_LIMIT) if video else None
        ps = [await _save_upload(p, d) for p in photos]
        from .video import VideoInputError
        try:
            rec = await run_in_threadpool(seller_review.create, store, v, ps or None, code or None)
        except VideoInputError as exc:
            raise HTTPException(422, str(exc)) from exc
    return rec.model_dump(mode="json")


def _seller_call(function, *args):
    try:
        return function(store, *args)
    except KeyError as exc:
        raise HTTPException(404, "Unknown seller draft") from exc
    except seller_review.Conflict as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/seller/drafts/{item_id}")
def seller_draft(item_id: str):
    return _seller_call(seller_review.review, item_id)


@app.post("/seller/drafts/{item_id}/declarations")
def seller_declarations(item_id: str, body: seller_review.DisclosureIn):
    return _seller_call(seller_review.disclose, item_id, body)


@app.post("/seller/drafts/{item_id}/publish")
def seller_publish(item_id: str, body: seller_review.PublishIn):
    return _seller_call(seller_review.publish, item_id, body)


@app.post("/seller/drafts/{item_id}/price")
def seller_price(item_id: str, body: pricing.PriceIn):
    return _seller_call(seller_review.set_price, item_id, body)


class OfferIn(BaseModel):
    item_id: str
    amount: int = Field(gt=0, strict=True)
    negotiation_id: str = ""


@app.post("/offers")
def buyer_offer(body: OfferIn):
    _record(body.item_id)
    try:
        with seller_review.lock(body.item_id):
            return pricing.offer(store, body.item_id, body.amount, body.negotiation_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/seller/drafts/{item_id}/evidence")
async def seller_evidence(item_id: str, revision: int = Form(..., ge=1), code: str = Form(""),
                          video: UploadFile | None = File(None), photos: list[UploadFile] = File(default=[])):
    if video is None and not photos:
        raise HTTPException(400, "Add a video or close-up photos")
    from .video import SOURCE_LIMIT, VideoInputError
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        v = await _save_upload(video, folder, SOURCE_LIMIT) if video else None
        ps = [await _save_upload(p, folder) for p in photos]
        try:
            return await run_in_threadpool(_seller_call, seller_review.add_evidence, item_id, revision, v, ps, code or None)
        except VideoInputError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.get("/records/{item_id}")
def get_record(item_id: str):
    from .catalog import public_record
    return public_record(store, _record(item_id)).model_dump(mode="json")


@app.get("/listings/{item_id}")
def get_listing(item_id: str):
    l = store.get_json("listings", item_id)
    if l is None:
        raise HTTPException(404, f"unknown listing {item_id}")
    from .catalog import listing_media, purchase_price, purchased_items
    record = _record(item_id)
    l = {k: v for k, v in l.items() if k != "price_note"}
    return {**l, "media": listing_media(store, record, l), "purchase_price": purchase_price(store, record),
            "currency": "INR", "price_source": l.get("price_source", "unset"),
            "purchase_available": item_id not in purchased_items(store),
            "seller_managed": store.get_json("seller_drafts", item_id) is not None}


@app.get("/search")
def search(type: str | None = None, colour: str | None = None, max_price: int | None = None, min_grade: int | None = None,
           exclude_defects: str | None = None, size_label: str | None = None,
           brand: str | None = None, currency: str | None = None):
    """exclude_defects is comma-separated, e.g. stain,hole."""
    return market.search({"type": type, "colour": colour, "max_price": max_price, "min_grade": min_grade,
                          "exclude_defects": [x for x in (exclude_defects or "").split(",") if x], "size_label": size_label,
                          "brand": brand, "currency": currency})


@app.get("/purchases")
def purchases():
    """Shared prototype history. Production must scope this to the signed-in buyer."""
    reports = reviews.list_reports()
    result = []
    for mandate in store.list_json("mandates"):
        raw = store.get_json("records", mandate["item_id"])
        if raw is None:
            continue  # old test mandates may have no remaining garment record
        record = ConditionRecord(**raw)
        report = next((r for r in reports if r.mandate_id == mandate["id"]), None)
        result.append({k: mandate[k] for k in ("id", "item_id", "amount", "currency", "status")})
        result[-1].update(item=record.item.model_dump(),
                         created_at=next((e.get("t", 0) for e in mandate.get("events", []) if e.get("event") == "held"), 0),
                         issue_id=report.id if report else None, issue_status=report.status if report else None)
    return sorted(result, key=lambda m: m["created_at"], reverse=True)


@app.get("/seller/drafts")
def seller_drafts():
    """Resumable listings in the shared prototype, without private price limits."""
    result = []
    for meta in store.list_json("seller_drafts"):
        raw = store.get_json("records", meta["id"])
        if raw is None:
            continue
        result.append({"id": meta["id"], "status": meta["status"], "item": raw["item"],
                       "asking_price": meta.get("asking_price"), "currency": "INR",
                       "updated_at": (meta.get("history") or [{}])[-1].get("at", "")})
    return sorted(result, key=lambda row: row["updated_at"], reverse=True)


class AskIn(BaseModel):
    item_id: str
    question: str


@app.post("/ask")
def ask(body: AskIn):
    return ask_mod.ask(_record(body.item_id), body.question).model_dump()


class ChatIn(BaseModel):
    session_id: str
    message: str


@app.post("/agent/chat")
async def agent_chat(body: ChatIn):
    from .agents.buyer import chat
    try:
        return await chat(body.session_id, body.message)
    except Exception as exc:
        raise HTTPException(503, "The shopping agent is temporarily unavailable. Try again in a moment.") from exc


@app.post("/seller/chat")
async def seller_chat(body: ChatIn):
    from .agents.seller import chat
    return await chat(body.session_id, body.message)


class FloorIn(BaseModel):
    item_id: str
    floor: int


@app.post("/seller/floor")
def seller_floor(body: FloorIn):
    raise HTTPException(410, "Set the asking price and optional private minimum through the seller pricing step.")


@app.post("/tryon")
async def tryon(item_id: str = Form(...), person: UploadFile = File(...)):
    """Try-on preview of THIS listed garment (its first evidence frame) on the buyer's photo."""
    from .tryon import preview
    rec = _record(item_id)
    garment = store.get_file(item_id, f"{rec.capture.frames[0]}.jpg")
    if garment is None:
        raise HTTPException(404, "garment frame not found")
    with tempfile.TemporaryDirectory() as t:
        p = await _save_upload(person, Path(t))
        out = preview(garment, p, out_dir=store.item_dir(item_id))
    store.sync_item(item_id)
    return {"preview": store.media_url(item_id, out.name), "label": "preview"}


def _reviewer(authorization: str | None = Header(None)):
    expected = os.getenv("FW_REVIEW_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Human-review access is not configured. Set FW_REVIEW_TOKEN on the API.")
    if not authorization or not secrets.compare_digest(authorization, "Bearer " + expected):
        raise HTTPException(401, "Reviewer access key required.")


async def _inspect_issue(report, video, photos):
    from .unbox.pipeline import run_unbox
    # Save raw evidence under an immutable attempt folder before model work.
    rel = f"issues/{report.id}/{uuid.uuid4().hex[:8]}"
    d = store.item_dir(report.item_id) / rel / "source"
    d.mkdir(parents=True, exist_ok=True)
    try:
        v = await _save_upload(video, d) if video else None
        ps = [await _save_upload(p, d) for p in photos]
        report = reviews.get(report.id)
        attempt_number = 1 + sum(e.get("event") == "additional_evidence" for e in report.history)
        report.media += [{"label": f"Received video · capture {attempt_number}", "url": store.media_url(report.item_id, v.relative_to(store.item_dir(report.item_id)).as_posix())}] if v else []
        report.media += [{"label": f"Received photo {i+1} · capture {attempt_number}", "url": store.media_url(report.item_id, p.relative_to(store.item_dir(report.item_id)).as_posix())}
                         for i, p in enumerate(ps)]
        reviews.save(report)
        await run_in_threadpool(store.sync_item, report.item_id)
        rec = ConditionRecord(**report.listing)
        res = await run_in_threadpool(run_unbox, rec, video=v, photos=ps or None, work_name=rel + "/inspection")
        return reviews.complete(report.id, res).model_dump(mode="json")
    except Exception as exc:
        # Never discard an issue or settle money when evidence processing fails.
        import logging
        logging.getLogger(__name__).warning("Issue inspection failed: %s (%s)", report.id, type(exc).__name__)
        return reviews.complete(report.id, None, f"Inspection unavailable ({type(exc).__name__}). A reviewer can inspect the uploaded media.").model_dump(mode="json")


@app.post("/issues")
@app.post("/unbox")  # legacy capture route now queues a human review too
async def issue(item_id: str = Form(...), buyer_text: str = Form(""), mandate_id: str = Form(""),
                video: UploadFile | None = File(None), photos: list[UploadFile] = File(default=[])):
    if video is None and not photos:
        raise HTTPException(400, "Send a received-garment video or photos.")
    if len(buyer_text) > 5000:
        raise HTTPException(400, "Keep the buyer statement under 5000 characters.")
    try:
        report = reviews.begin(_record(item_id), buyer_text, mandate_id or None)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await _inspect_issue(report, video, photos)


@app.get("/issues")
def issues_for_item(item_id: str | None = None):
    # Shared prototype history; production requires an authenticated buyer scope.
    if item_id is not None:
        _record(item_id)
    return [r.model_dump(mode="json") for r in reviews.list_reports(item_id)]


@app.get("/issues/{issue_id}")
def issue_report(issue_id: str):
    try:
        return reviews.get(issue_id).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(404, "Unknown issue") from exc


@app.post("/issues/{issue_id}/evidence")
async def more_evidence(issue_id: str, video: UploadFile | None = File(None), photos: list[UploadFile] = File(default=[])):
    if video is None and not photos:
        raise HTTPException(400, "Send a video or photos.")
    with reviews.transaction():
        try:
            report = reviews.get(issue_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown issue") from exc
        if report.status not in ("awaiting_review", "needs_evidence"):
            raise HTTPException(409, "This issue cannot accept evidence right now.")
        report.history.append({"at": reviews.now(), "event": "additional_evidence", "previous_inspection": report.inspection})
        report.status = "processing"
        reviews.save(report)
    return await _inspect_issue(report, video, photos)


@app.get("/review", dependencies=[Depends(_reviewer)])
def review_queue():
    return [r.model_dump(mode="json") for r in reviews.list_reports()]


@app.post("/issues/{issue_id}/decision", dependencies=[Depends(_reviewer)])
def review_decision(issue_id: str, body: reviews.Decision):
    try:
        return reviews.review(issue_id, body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(404, "Unknown issue") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


class CaseIn(BaseModel):
    item_id: str
    buyer_text: str | None = None
    amount: int


@app.post("/case")
def case(body: CaseIn):
    raise HTTPException(410, "AI dispute rulings have been retired. Submit captured evidence to /issues for human review.")


class EscrowIn(BaseModel):
    item_id: str
    payer: str = "buyer"
    payee: str | None = None
    amount: int = Field(gt=0, strict=True)
    currency: str = "INR"
    quote_id: str | None = None


@app.post("/escrow")
def escrow_create(body: EscrowIn):
    _record(body.item_id)
    try:
        return escrow.create(body.item_id, body.payer, body.payee or "seller", body.amount, body.currency, body.quote_id).model_dump()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/escrow/{mandate_id}")
def escrow_get(mandate_id: str):
    if store.get_json("mandates", mandate_id) is None:
        raise HTTPException(404, "unknown mandate")
    return escrow.get(mandate_id).model_dump()


class SettleIn(BaseModel):
    verdict: str
    refund_pct: int = 0


@app.post("/escrow/{mandate_id}/settle")
def escrow_settle(mandate_id: str, body: SettleIn):
    raise HTTPException(410, "Inspection cannot settle escrow. Use buyer acceptance or the protected human-review endpoint.")


@app.post("/escrow/{mandate_id}/accept")
def accept_delivery(mandate_id: str):
    if store.get_json("mandates", mandate_id) is None:
        raise HTTPException(404, "Unknown mandate")
    with reviews.transaction():
        try:
            return escrow.settle(mandate_id, "buyer_accepted").model_dump()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc


@app.get("/media/{item_id}/{name:path}")
def media(item_id: str, name: str):
    p = store.get_file(item_id, name)  # local file, or downloaded from GCS with FW_STORE=cloud
    if p is None:
        raise HTTPException(404, "not found")
    return FileResponse(p)
