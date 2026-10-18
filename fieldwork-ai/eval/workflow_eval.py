"""Run independently labelled capture cases through the actual local API stack.

Requires an isolated FW_STORE_DIR, FW_REVIEW_TOKEN and Vertex settings.
python eval/workflow_eval.py --root data/garments --split development --out data/results/captures-dev
--with-agents also exercises live buyer/seller agents; it increases latency and token usage.
No real payments are performed. Reviewer actions test transitions, not human decision quality.
"""
import argparse
import json
import mimetypes
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.capture_schema import validate_capture
from fieldwork import config
from fieldwork.stats import rate


def metrics(rows):
    changed = [r for r in rows if r["actual_change"] is True]
    unchanged = [r for r in rows if r["actual_change"] is False and r["same_garment"] is True]
    lookalikes = [r for r in rows if r["same_garment"] is False]
    questions = [q for r in rows for q in r.get("questions", [])]
    return {"cases": len(rows), "distinct_comparison_groups": len({r["group"] for r in rows}),
        "workflow_completed": rate(sum(r.get("workflow_passed", False) for r in rows), len(rows)),
        "expected_assessment_agreement": rate(sum(r.get("assessment") == r["expected_assessment"] for r in rows), len(rows)),
        "change_recall": rate(sum(r.get("assessment") == "differs" for r in changed), len(changed)),
        "false_differs_unchanged": rate(sum(r.get("assessment") == "differs" for r in unchanged), len(unchanged)),
        "false_consistent_lookalikes": rate(sum(r.get("assessment") == "consistent" for r in lookalikes), len(lookalikes)),
        "cant_tell": rate(sum(r.get("assessment") == "cant_tell" for r in rows), len(rows)),
        "errors": sum("error" in r for r in rows),
        "answer_state_agreement": rate(sum(q.get("state") == q["expected_state"] for q in questions), len(questions)),
        "interval_limit": "Binomial intervals are descriptive; repeated cases per garment/group are correlated. Use group bootstrap for larger multi-case datasets."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split", choices=["development", "calibration", "test"], default="development")
    ap.add_argument("--with-agents", action="store_true")
    args = ap.parse_args()
    if config.STORE_KIND != "local" or not os.getenv("FW_STORE_DIR") or not os.getenv("FW_REVIEW_TOKEN"):
        raise SystemExit("Use an isolated local FW_STORE_DIR and set FW_REVIEW_TOKEN")
    captures = []
    groups = {}
    for path in sorted(args.root.glob("*/truth.json")):
        truth = validate_capture(path.parent)
        previous = groups.setdefault(truth.comparison_group, truth.split)
        if previous != truth.split:
            raise SystemExit(f"Split leakage: {truth.comparison_group}")
        if truth.split == args.split:
            captures.append((path.parent, truth))
    if not captures:
        raise SystemExit(f"No validated captures in split {args.split}; no evaluation was run")
    from fastapi.testclient import TestClient
    from fieldwork.api import app
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []

    def media(folder, video, photos):
        files = []
        if video:
            path = folder / video
            files.append(("video", (path.name, path.read_bytes(), "video/webm" if path.suffix == ".webm" else "video/mp4")))
        for name in photos:
            path = folder / name
            files.append(("photos", (path.name, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/jpeg")))
        return files

    def save():
        report = {"meta": {"split": args.split, "models": {"flash": config.MODEL_FLASH, "lite": config.MODEL_LITE, "dino": config.DINO_MODEL},
                  "agents_exercised": args.with_agents, "real_payments": False,
                  "scope": "API orchestration and evidence assessment; manual UI and semantic reference review are separate"},
                  "cases": rows, "metrics": metrics(rows)}
        (args.out / "report.json").write_text(json.dumps(report, indent=2))

    with TestClient(app) as client:
        for folder, truth in captures:
            row = {"garment_id": truth.garment_id, "group": truth.comparison_group,
                   "actual_change": truth.actual_change, "same_garment": truth.same_garment,
                   "expected_assessment": truth.expected_assessment, "stages": [],
                   "questions": [q.model_dump() for q in truth.buyer_questions]}
            rows.append(row)

            def call(stage, method, path, **kwargs):
                start = time.monotonic()
                response = getattr(client, method)(path, **kwargs)
                row["stages"].append({"name": stage, "http": response.status_code, "seconds": round(time.monotonic()-start, 2)})
                print(truth.garment_id, stage, response.status_code, flush=True)
                assert response.status_code == 200, f"{stage}: HTTP {response.status_code}"
                return response.json()

            try:
                record = call("seller_capture", "post", "/take", data={"code": truth.code or ""},
                              files=media(folder, truth.seller_video, truth.seller_photos))
                item = record["id"]
                draft = call("seller_review", "get", f"/seller/drafts/{item}")
                from fieldwork.spec import DEFECT_CODES, REGIONS
                disclosed = [{"code": f.code if f.code in DEFECT_CODES else "other",
                              "region": f.region if f.region in REGIONS else "whole", "description": f.description}
                             for f in truth.known_flaws]
                draft = call("seller_disclosure", "post", f"/seller/drafts/{item}/declarations", json={
                    "revision": draft["revision"], "answer": "issues_reported" if disclosed else "unknown", "issues": disclosed})
                draft = call("seller_price", "post", f"/seller/drafts/{item}/price", json={
                    "revision": draft["revision"], "asking_price": 1500, "currency": "INR"})  # explicit test-actor price
                call("seller_publication_state_check", "post", f"/seller/drafts/{item}/publish", json={
                    "revision": draft["revision"], "acknowledge_limitations": True})
                record = call("published_record", "get", f"/records/{item}")
                row["item_id"] = item
                row["record"] = record
                row["listing"] = call("listing", "get", f"/listings/{item}")
                assert item in json.dumps(call("search", "get", "/search"))
                for question, reference in zip(truth.buyer_questions, row["questions"]):
                    answer = call("buyer_question", "post", "/ask", json={"item_id": item, "question": question.question})
                    reference.update(answer)
                    reference["semantic_review"] = "pending independent human comparison with reference_answer"
                if args.with_agents:
                    for path, message in (("/agent/chat", f"Find garment {item}, ask what is known about it, and show the option. Do not purchase."),
                                          ("/seller/chat", f"Use propose_price to quote item {item}.")):
                        reply = call("agent_" + path.split("/")[1], "post", path,
                                     json={"session_id": item + path.replace("/", "_"), "message": message})
                        assert reply.get("text") and reply.get("tool_calls")
                purchase = {"item_id": item, "payer": "eval-buyer", "payee": "eval-seller", "amount": record["price_band"][1], "currency": record["currency"]}
                from fieldwork.store import store
                accept_item = item + "_accept_control"
                control_record = store.get_json("records", item); control_record["id"] = accept_item
                control_listing = store.get_json("listings", item); control_listing["id"] = accept_item
                store.put_json("records", accept_item, control_record)
                store.put_json("listings", accept_item, control_listing)
                accepted = call("purchase_accept", "post", "/escrow", json={**purchase, "item_id": accept_item})
                assert call("all_good", "post", f"/escrow/{accepted['id']}/accept")["status"] == "released"
                mandate = call("purchase_issue", "post", "/escrow", json=purchase)
                issue = call("issue_inspection", "post", "/issues", data={"item_id": item, "mandate_id": mandate["id"],
                             "buyer_text": "Evaluation: compare the submitted received garment against the listing evidence."},
                             files=media(folder, truth.received_video, truth.received_photos))
                row["assessment"] = issue["suggested_assessment"]
                row["issue_report"] = issue
                assert issue["status"] == "awaiting_review" and issue["inspection"] is not None
                assert call("held_before_review", "get", f"/escrow/{mandate['id']}")["status"] == "held"
                assert client.post(f"/escrow/{mandate['id']}/accept").status_code == 409
                auth = {"Authorization": "Bearer " + os.environ["FW_REVIEW_TOKEN"]}
                assert issue["id"] in json.dumps(call("review_queue", "get", "/review", headers=auth))
                requested = call("request_evidence", "post", f"/issues/{issue['id']}/decision", headers=auth,
                                 json={"action": "request_evidence", "reviewer": "evaluation-state-check", "note": "Request further evidence; no payment decision."})
                assert requested["status"] == "needs_evidence"
                assert call("held_after_request", "get", f"/escrow/{mandate['id']}")["status"] == "held"
                # Real human decision quality must be reviewed separately; this is a state-transition test.
                row["workflow_passed"] = True
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"[:300]
                row["workflow_passed"] = False
            finally:
                save()
    print(json.dumps(metrics(rows), indent=2))


if __name__ == "__main__":
    main()
