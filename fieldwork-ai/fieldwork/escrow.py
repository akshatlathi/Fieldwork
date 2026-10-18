"""Simulated escrow released by explicit buyer acceptance or a human reviewer.
Inspection suggestions cannot settle payment. AP2 itself has no escrow; this is
a demo extension using HMAC signatures as a stand-in for real keys."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

from pydantic import BaseModel

from .store import store

_SECRET = b"fieldwork-demo-signing-key"  # demo only; real deployments use the payer's key


class Mandate(BaseModel):
    id: str
    item_id: str
    payer: str
    payee: str
    amount: int
    currency: str
    condition: str = "buyer accepts delivery or a human reviewer decides"
    status: str = "held"  # held | released | refunded | partial
    events: list[dict] = []
    signature: str = ""


def _sign(m: Mandate) -> str:
    body = json.dumps({k: getattr(m, k) for k in ("id", "item_id", "payer", "payee", "amount", "currency", "condition")},
                      sort_keys=True).encode()
    return hmac.new(_SECRET, body, hashlib.sha256).hexdigest()


def _save(m: Mandate) -> Mandate:
    store.put_json("mandates", m.id, m.model_dump())
    return m


def create(item_id: str, payer: str, payee: str, amount: int, currency: str, quote_id: str | None = None) -> Mandate:
    from .seller_review import lock
    with lock(item_id):
        return _create(item_id, payer, payee, amount, currency, quote_id)


def _create(item_id, payer, payee, amount, currency, quote_id):
    from .spec import ConditionRecord
    raw = store.get_json("records", item_id)
    if raw is None:
        raise ValueError("Unknown garment.")
    lifecycle = store.get_json("seller_drafts", item_id)
    listing = store.get_json("listings", item_id) or {}
    if (lifecycle is not None and lifecycle.get("status") != "published") or listing.get("publication_status", "published") != "published":
        raise ValueError("The seller must review and publish this draft before purchase.")
    record = ConditionRecord(**raw)
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("Purchase amount must be a positive integer.")
    currency = currency.strip().upper()
    if currency != record.currency.upper():
        raise ValueError("Purchase currency must match the listing.")
    from .pricing import validate_purchase
    validate_purchase(store, item_id, amount, currency, quote_id)
    if not listing.get("fixture") and any(m["item_id"] == item_id and m["status"] in ("held", "released", "partial") for m in store.list_json("mandates")):
        raise ValueError("This garment already has a purchase. Open its delivery or issue report.")
    m = Mandate(id=f"md_{uuid.uuid4().hex[:10]}", item_id=item_id, payer=payer, payee=payee, amount=amount, currency=currency)
    m.signature = _sign(m)
    m.events.append({"t": time.time(), "event": "held", "by": payer})
    _save(m)
    if quote_id:
        quote = store.get_json("quotes", quote_id)
        if quote:
            quote["mandate_id"] = m.id
            store.put_json("quotes", quote_id, quote)
    return m


def get(mandate_id: str) -> Mandate:
    return Mandate(**store.get_json("mandates", mandate_id))


def settle(mandate_id: str, verdict: str, refund_pct: int = 0, by: str = "buyer") -> Mandate:
    m = get(mandate_id)
    if m.signature != _sign(m):
        raise ValueError("mandate signature mismatch")
    if m.status != "held":
        return m
    if verdict not in ("buyer_accepted", "human_review"):
        raise ValueError("Inspection assessments cannot settle escrow.")
    if not 0 <= refund_pct <= 100 or (verdict == "buyer_accepted" and refund_pct):
        raise ValueError("Invalid refund percentage.")
    if verdict == "buyer_accepted":
        from .human_review import has_open_issue
        if has_open_issue(m.item_id):
            raise ValueError("A human must review the open issue before escrow can move.")
    if refund_pct >= 100:
        m.status = "refunded"
    elif refund_pct > 0:
        m.status = "partial"
    else:
        m.status = "released"
    m.events.append({"t": time.time(), "event": m.status, "source": verdict, "by": by, "refund_pct": refund_pct})
    return _save(m)
