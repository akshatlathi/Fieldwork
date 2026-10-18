"""Regression checks for evidence corruption and unsupported public answers."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from fieldwork import ask as qa
from fieldwork.spec import Box, Capture, Claim, ConditionRecord, Item, Lane, Severity
from fieldwork.take.record import Draft, DraftClaim, to_claims
from fieldwork.unbox import gate
from fieldwork.unbox.align import align
from fieldwork.unbox.diff import crop_pair


def record(claims):
    return ConditionRecord(id="test", item=Item(type="shirt"), claims=claims,
                           capture=Capture(code_expected="test", code_seen=False,
                                           take_sha256="hash", frames=["f1"]))


def flaw(box=None, frame="f1"):
    return Claim(id="c1", lane=Lane.shown, code="stain", severity=Severity.minor,
                 region="front", evidence=[Box(frame_id=frame, box_2d=box or [100, 100, 300, 300])])


def test_alignment_preserves_two_references_for_one_received_frame(tmp_path):
    rng = np.random.default_rng(8)
    image = rng.integers(0, 256, (480, 480, 3), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    received = tmp_path / "received.jpg"
    cv2.imwrite(str(received), image)
    refs = []
    for i, dx in enumerate((0, 12)):
        folder = tmp_path / str(i)
        folder.mkdir()
        path = folder / "reference.jpg"  # even identical basenames must be distinct
        cv2.imwrite(str(path), cv2.warpAffine(image, np.float32([[1, 0, dx], [0, 1, 0]]), (480, 480)))
        refs.append(path)
    first = align(refs[0], received)
    assert first.ok
    saved = first.warped_path.read_bytes()
    second = align(refs[1], received)
    assert second.ok
    assert first.warped_path != second.warped_path
    assert first.warped_path.read_bytes() == saved
    assert second.warped_path.read_bytes() != saved


@pytest.mark.parametrize("box", [[400, 100, 200, 300], [-1, 0, 500, 500],
                                 [0, 0, 1001, 1000], [100, 100, 100, 200]])
def test_invalid_evidence_is_demoted_and_cannot_be_cropped(tmp_path, box):
    draft = Draft(item=Item(type="shirt"), code_read=None, listing_text_en="Shirt",
                  claims=[DraftClaim(lane=Lane.shown, code="stain", region="front",
                                     severity=Severity.minor, note="Mark", evidence=[Box(frame_id="f1", box_2d=box)])])
    claim = to_claims(draft, {"f1"})[0]
    assert claim.lane == Lane.cant_judge and not claim.evidence
    with pytest.raises(ValueError, match="positive area"):
        crop_pair(tmp_path / "absent.jpg", tmp_path / "absent.jpg", box)


@pytest.mark.parametrize("claims,citations", [([], ["invented"]),
    ([flaw(frame="missing")], ["c1"]), ([flaw([400, 0, 200, 500])], ["c1"]),
    ([Claim(id="c1", lane=Lane.declared, code="washed")], ["c1"])])
def test_unsupported_answer_text_is_removed(monkeypatch, claims, citations):
    monkeypatch.setattr(qa, "store", SimpleNamespace(get_file=lambda *a: None))
    monkeypatch.setattr(qa.gemini, "generate", lambda *a, **k: qa.Answer(
        answer="Guaranteed spotless", lang="ja", state="shown", claim_ids=citations))
    answer = qa.ask(record(claims), "Is it spotless?")
    assert answer.state == "not_in_take" and answer.claim_ids == []
    assert "Guaranteed" not in answer.answer
    assert "close-up" in answer.answer and answer.lang == "en"


def test_supported_record_answer_is_preserved(monkeypatch):
    monkeypatch.setattr(qa, "store", SimpleNamespace(get_file=lambda *a: None))
    monkeypatch.setattr(qa.gemini, "generate", lambda *a, **k: qa.Answer(
        answer="A stain is recorded on the front.", lang="en", state="shown", claim_ids=["c1"]))
    answer = qa.ask(record([flaw()]), "Any marks?")
    assert answer.state == "shown" and answer.claim_ids == ["c1"]


def test_answer_state_is_constrained():
    with pytest.raises(ValidationError):
        qa.Answer(answer="Yes", lang="en", state="guaranteed")


@pytest.mark.parametrize("evidence", [[], [Box(frame_id="missing", box_2d=[0, 0, 500, 500])],
                                    [Box(frame_id="f1", box_2d=[500, 0, 200, 500])]])
def test_uncheckable_listed_flaw_cannot_suggest_consistent(tmp_path, monkeypatch, evidence):
    claim = flaw()
    claim.evidence = evidence
    monkeypatch.setattr(gate, "_near_identical", lambda *a: False)
    monkeypatch.setattr(gate, "align", lambda *a: SimpleNamespace(ok=True, warped_path=tmp_path / "aligned.jpg"))
    monkeypatch.setattr(gate, "change_regions", lambda *a, **k: [])
    monkeypatch.setattr(gate.judge, "flaw_still_there", lambda *a: pytest.fail("No usable flaw crop"))
    result = gate.check(record([claim]), {"f1": tmp_path / "ref.jpg"},
                        [("f1", tmp_path / "received.jpg")], tmp_path / "work")
    assert result.pairs_aligned == 1
    assert result.verdict == "cant_tell" and result.closeup_request
    assert any("could not be checked" in text for text in result.limitations)
