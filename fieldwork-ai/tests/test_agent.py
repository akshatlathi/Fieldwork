"""End-to-end: fixtures -> market -> MCP tools -> ADK buyer agent -> API. Run: uv run python tests/test_agent.py"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fieldwork import market  # noqa: E402
from fieldwork.agents import mcp_server  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import logging; logging.disable(logging.INFO)
    ids = market.seed_fixtures()
    from fieldwork.store import store
    for item in ids:
        listing=store.get_json("listings",item)
        listing.update(price_source="seller",asking_price=1500,currency="INR",negotiation_enabled=False)
        store.put_json("listings",item,listing)  # explicitly chosen test-actor prices, no estimate
    assert len(ids) == 6

    cards = market.search({"type": "shirt", "colour": "navy", "max_price": 6000, "exclude_defects": ["stain"]})
    print("search navy coat no stains ->", [c["id"] for c in cards])
    assert [c["id"] for c in cards] == ["fx_coat_navy_clean"]

    rec = mcp_server.get_condition_record("fx_coat_navy_clean")
    assert rec["capture"]["code_expected"] == "hidden"
    md = mcp_server.create_escrow("fx_coat_navy_clean", "buyer-agent", 5000, "JPY")
    assert md["status"] == "held" and mcp_server.get_escrow(md["id"])["id"] == md["id"]
    print("mcp tools ok, mandate", md["id"])

    from fastapi.testclient import TestClient
    from fieldwork.api import app
    c = TestClient(app)
    assert c.get("/health").json()["ok"]
    assert len(c.get("/search", params={"type": "trousers", "exclude_defects": "stain"}).json()) == 0
    a = c.post("/ask", json={"item_id": "fx_coat_navy_stain", "question": "左の袖口にシミはありますか？"}).json()
    print("API /ask ->", json.dumps(a, ensure_ascii=False))
    assert a["state"] in ("shown", "not_in_take", "cant_judge")

    from fieldwork.agents.buyer import chat
    out = asyncio.run(chat("t1", "Find me a navy shirt with no stains under 6000 rupees"))
    print("AGENT model:", out.get("model"))
    for t in out["tool_calls"]:
        print("  tool:", t["tool"], json.dumps(t["args"], ensure_ascii=False))
    print("AGENT reply:", out["text"])
    assert out["tool_calls"] and out["text"]
    print("OK")


if __name__ == "__main__":
    main()
