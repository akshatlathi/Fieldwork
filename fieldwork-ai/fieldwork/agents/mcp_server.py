"""Fieldwork MCP server (stdio). Run: python -m fieldwork.agents.mcp_server
Tools are plain functions so tests can call them in-process."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .. import ask as ask_mod
from .. import escrow, market
from ..spec import ConditionRecord
from ..store import store

mcp = MCPServer("fieldwork")


def _record(item_id: str) -> ConditionRecord:
    raw = store.get_json("records", item_id)
    if raw is None:
        raise ValueError(f"unknown item_id {item_id}")
    return ConditionRecord(**raw)


@mcp.tool()
def search_garments(type: str = "", colour: str = "", max_price: int = 0, min_grade: int = 0,
                    exclude_defects: list[str] | None = None, size: str = "", brand: str = "", currency: str = "INR") -> list[dict]:
    """Search second-hand garments by EVIDENCE (what the seller's video showed), not by seller text.
    All arguments are optional filters; leave empty/0 to skip. type: garment type e.g. "coat", "jacket", "jeans".
    colour: e.g. "navy". max_price: budget in INR against the seller's asking price.
    min_grade: minimum condition grade 1-5; all grades in the uncertainty set must meet it.
    exclude_defects: defect codes to rule out, any of stain, hole, tear, pilling, fading, snag, loose_seam, missing_button, broken_zip, discolour.
    size: size label substring e.g. "M". Returns cards with id, grade_set, price_band, shown_flaws, cant_judge regions, evidence_badge."""
    return market.search({"type": type, "colour": colour, "max_price": max_price or None, "min_grade": min_grade or None,
                          "exclude_defects": exclude_defects or [], "size_label": size, "brand": brand, "currency": currency})


@mcp.tool()
def get_condition_record(item_id: str) -> dict:
    """Get the full public condition record for one garment: claims in four lanes (shown / measured / declared / cant_judge),
    each with region and severity, plus the grade set and price band. Only 'shown' and 'measured' claims are evidence."""
    from ..catalog import public_record
    return public_record(store, _record(item_id)).model_dump(mode="json")


@mcp.tool()
def ask_garment(item_id: str, question: str) -> dict:
    """Ask the garment one question in any language (e.g. "Is there a stain on the left cuff?"). The answer comes only from the
    evidence record and frames. state is 'shown' (answered from evidence), 'not_in_take' (not shown; ask the seller for a close-up)
    or 'cant_judge' (photos cannot establish it). Treat not_in_take and cant_judge as unknown, never as a yes or no."""
    return ask_mod.ask(_record(item_id), question).model_dump()


@mcp.tool()
def create_escrow(item_id: str, payer: str, amount: int, currency: str = "INR", quote_id: str = "") -> dict:
    """Create a simulated escrow held until the buyer accepts delivery or a human reviews an issue.
    Inspection suggestions never release payment. ONLY call after explicit purchase confirmation."""
    _record(item_id)
    return escrow.create(item_id, payer, "seller", amount, currency, quote_id or None).model_dump()


@mcp.tool()
def get_escrow(mandate_id: str) -> dict:
    """Get the current state of an escrow mandate: status (held, released, refunded, partial) and event history."""
    return escrow.get(mandate_id).model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
