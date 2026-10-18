"""Seller-defined INR prices. The private floor never leaves backend storage."""
from datetime import datetime, timedelta, timezone
import math
import uuid

from pydantic import BaseModel, Field, StrictInt, model_validator

MAX_ROUNDS = 5


class PriceIn(BaseModel):
    revision: int = Field(ge=1)
    asking_price: StrictInt = Field(gt=0, le=10000000)
    currency: str = "INR"
    negotiation_enabled: bool = False
    minimum_price: StrictInt | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid(self):
        if self.currency != "INR":
            raise ValueError("Only INR is supported.")
        if self.negotiation_enabled and (self.minimum_price is None or self.minimum_price > self.asking_price):
            raise ValueError("Set a private minimum no higher than the asking price.")
        if not self.negotiation_enabled and self.minimum_price is not None:
            raise ValueError("Enable negotiation before setting a private minimum.")
        return self


def terms(storage, item_id):
    listing = storage.get_json("listings", item_id) or {}
    if listing.get("price_source") != "seller" or not listing.get("asking_price"):
        raise ValueError("The seller must set an asking price in INR before purchase.")
    asking = listing["asking_price"]
    enabled = bool(listing.get("negotiation_enabled"))
    private = storage.get_json("floors", item_id) or {}
    floor = private.get("floor") if enabled else asking
    if floor is None or not 0 < floor <= asking:
        raise ValueError("Seller pricing needs to be configured again.")
    return listing, asking, floor


def offer(storage, item_id, buyer_offer, negotiation_id=""):
    from .catalog import purchased_items
    if item_id in purchased_items(storage):
        raise ValueError("This garment already has a purchase.")
    listing, asking, floor = terms(storage, item_id)
    if listing.get("publication_status", "published") != "published":
        raise ValueError("This garment has not been published.")
    if isinstance(buyer_offer, bool) or not isinstance(buyer_offer, int) or buyer_offer <= 0:
        raise ValueError("Enter a positive whole-rupee offer.")
    if not listing.get("negotiation_enabled"):
        return {"status": "fixed", "price": asking, "currency": "INR", "item_id": item_id,
                "note": "The seller has set a fixed asking price."}
    negotiation = storage.get_json("negotiations", negotiation_id) if negotiation_id else None
    if negotiation_id and (negotiation is None or negotiation["item_id"] != item_id):
        raise ValueError("Unknown negotiation for this garment.")
    if negotiation is None:
        negotiation = {"id": "offer_" + uuid.uuid4().hex[:16], "item_id": item_id, "rounds": 0}
    if negotiation["rounds"] >= MAX_ROUNDS:
        raise ValueError("Negotiation has reached its five-round limit. You can purchase at the asking price.")
    negotiation["rounds"] += 1
    accepted = buyer_offer >= floor
    # Counter halfway from the offer to the asking price, rounded up to ₹10.
    price = min(buyer_offer, asking) if accepted else min(asking, max(floor, math.ceil((buyer_offer + asking) / 20) * 10))
    expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    quote_id = "quote_" + uuid.uuid4().hex[:20]
    quote = {"id": quote_id, "negotiation_id": negotiation["id"], "item_id": item_id,
             "price": price, "currency": "INR", "expires_at": expires, "asking_price": asking}
    storage.put_json("quotes", quote_id, quote)
    storage.put_json("negotiations", negotiation["id"], negotiation)
    return {"status": "accepted" if accepted else "counter", "price": price, "currency": "INR",
            "item_id": item_id, "negotiation_id": negotiation["id"], "quote_id": quote_id,
            "round": negotiation["rounds"], "max_rounds": MAX_ROUNDS, "expires_at": expires}


def validate_purchase(storage, item_id, amount, currency, quote_id=None):
    listing, asking, floor = terms(storage, item_id)
    if currency != "INR":
        raise ValueError("Purchase currency must be INR.")
    if not floor <= amount <= asking:
        raise ValueError("Purchase price is outside the seller's accepted range. Request a new quote.")
    if amount != asking:
        quote = storage.get_json("quotes", quote_id) if quote_id else None
        if (not listing.get("negotiation_enabled") or quote is None or quote.get("item_id") != item_id
                or quote.get("price") != amount or quote.get("asking_price") != asking
                or quote.get("currency") != currency or quote.get("mandate_id")
                or datetime.fromisoformat(quote["expires_at"]) <= datetime.now(timezone.utc)):
            raise ValueError("A valid negotiated quote is required for this price.")
