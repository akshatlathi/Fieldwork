"""Live API orchestration check using demo media. Not an accuracy benchmark.

Run with Vertex env settings, HF_HOME, and an isolated FW_STORE_DIR.
python eval/workflow_smoke.py --photo store/items/d_02/f1.jpg --out data/results/workflow-smoke.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cv2
from fastapi.testclient import TestClient
from fieldwork.api import app
from fieldwork.store import store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not os.getenv("FW_REVIEW_TOKEN"):
        raise SystemExit("Set FW_REVIEW_TOKEN for this isolated test")
    stages = []
    result = {"kind": "functional_smoke", "accuracy_benchmark": False, "stages": stages}
    scratch = args.out.parent / "smoke-media"
    scratch.mkdir(parents=True, exist_ok=True)
    image = cv2.imread(str(args.photo))
    if image is None:
        raise SystemExit("Photo cannot be read")
    h, w = image.shape[:2]
    video = scratch / "seller.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 5, (w, h))
    assert writer.isOpened(), "MP4 writer unavailable"
    for _ in range(30):
        writer.write(image)
    writer.release()
    changed = image.copy()
    cv2.circle(changed, (w // 2, h // 2), max(12, w // 25), (15, 25, 70), -1)
    received = scratch / "received.jpg"
    cv2.imwrite(str(received), changed)

    with TestClient(app) as client:
        def call(name, method, path, **kwargs):
            start = time.monotonic()
            response = getattr(client, method)(path, **kwargs)
            stages.append({"stage": name, "http": response.status_code,
                           "seconds": round(time.monotonic() - start, 2)})
            print(f"{name}: HTTP {response.status_code} ({stages[-1]['seconds']}s)", flush=True)
            assert response.status_code == 200, f"{name}: HTTP {response.status_code}: {response.text[:300]}"
            return response.json()

        try:
            rec = call("seller_video_capture", "post", "/take", data={"code": ""},
                       files={"video": (video.name, video.read_bytes(), "video/mp4")})
            item = rec["id"]
            result["item_id"] = item
            assert rec["capture"]["frames"]
            draft = call("seller_review", "get", f"/seller/drafts/{item}")
            draft = call("seller_disclosure", "post", f"/seller/drafts/{item}/declarations", json={
                "revision": draft["revision"], "answer": "unknown", "issues": []})
            draft = call("seller_price", "post", f"/seller/drafts/{item}/price", json={
                "revision": draft["revision"], "asking_price": 1500, "currency": "INR"})  # explicit test-actor price
            call("seller_publication_state_check", "post", f"/seller/drafts/{item}/publish", json={
                "revision": draft["revision"], "acknowledge_limitations": True})
            listing = call("translated_listing", "get", f"/listings/{item}")
            assert all(listing.get(k) for k in ("en", "ja", "ko", "zh-TW", "th", "id-ID", "vi", "hi"))
            rec = call("public_record", "get", f"/records/{item}")
            found = call("buyer_search", "get", "/search")
            assert item in json.dumps(found)
            call("buyer_evidence_question", "post", "/ask", json={"item_id": item, "question": "Can you establish how this garment smells?"})
            # Agent faults are recorded while the direct transaction path is still checked.
            for stage, path, message in (
                ("buyer_agent", "/agent/chat", "Search for available garments and show me an option. Do not purchase anything."),
                ("seller_agent", "/seller/chat", f"Use propose_price to quote the opening price for {item}."),
            ):
                try:
                    reply = call(stage, "post", path, json={"session_id": "smoke-" + item + stage, "message": message})
                    assert reply.get("text") and reply.get("tool_calls"), "Agent did not exercise tools"
                except Exception as exc:
                    result.setdefault("agent_errors", []).append({"stage": stage, "error": str(exc)[:300]})
            mandate_body = {"item_id": item, "payer": "smoke-buyer", "payee": "smoke-seller", "amount": rec["price_band"][1], "currency": rec["currency"]}
            from fieldwork.store import store
            accept_item = item + "_accept_control"
            control_record = store.get_json("records", item); control_record["id"] = accept_item
            control_listing = store.get_json("listings", item); control_listing["id"] = accept_item
            store.put_json("records", accept_item, control_record)
            store.put_json("listings", accept_item, control_listing)
            accepted = call("purchase_accept_branch", "post", "/escrow", json={**mandate_body, "item_id": accept_item})
            release = call("explicit_buyer_acceptance", "post", f"/escrow/{accepted['id']}/accept")
            assert release["status"] == "released"
            held = call("purchase_issue_branch", "post", "/escrow", json=mandate_body)
            issue = call("received_inspection_and_report", "post", "/issues",
                         data={"item_id": item, "mandate_id": held["id"], "buyer_text": "Functional test: digitally planted mark on demo media."},
                         files={"photos": (received.name, received.read_bytes(), "image/jpeg")})
            assert issue["status"] == "awaiting_review" and issue["inspection"], "Inspection failed or report not queued"
            result["suggested_assessment"] = issue["suggested_assessment"]
            result["comparisons"] = len(issue["inspection"]["comparisons"])
            assert call("escrow_stays_held", "get", f"/escrow/{held['id']}")["status"] == "held"
            assert client.post(f"/escrow/{held['id']}/accept").status_code == 409
            auth = {"Authorization": "Bearer " + os.environ["FW_REVIEW_TOKEN"]}
            queue = call("human_review_queue", "get", "/review", headers=auth)
            assert issue["id"] in json.dumps(queue)
            call("human_requests_evidence", "post", f"/issues/{issue['id']}/decision", headers=auth,
                 json={"action": "request_evidence", "reviewer": "smoke-reviewer", "note": "Please show the area more clearly."})
            updated = call("buyer_adds_evidence", "post", f"/issues/{issue['id']}/evidence",
                           files={"photos": (received.name, received.read_bytes(), "image/jpeg")})
            assert updated["status"] == "awaiting_review" and updated["inspection"]
            decision = call("human_refund", "post", f"/issues/{issue['id']}/decision", headers=auth,
                            json={"action": "refund", "refund_pct": 100, "reviewer": "smoke-reviewer", "note": "Functional test decision; simulated payment."})
            assert decision["status"] == "resolved"
            assert call("settlement_audit", "get", f"/escrow/{held['id']}")["status"] == "refunded"
            result["passed"] = not result.get("agent_errors")
        except Exception as exc:
            result["passed"] = False
            result["error"] = f"{type(exc).__name__}: {exc}"[:500]
        finally:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2), flush=True)
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
