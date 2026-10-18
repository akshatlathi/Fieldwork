"""Real-capture checks prevent missing media and group leakage from entering a benchmark."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.capture_schema import CaptureTruth, validate_capture


def example():
    return json.loads((Path(__file__).resolve().parents[1] / "eval/capture-truth.example.json").read_text())


def test_changed_case_requires_change_reference():
    row = example()
    row["actual_change"] = True
    with pytest.raises(ValueError, match="change annotation"):
        CaptureTruth(**row)


def test_synthetic_is_not_real_benchmark():
    row = example()
    row["synthetic"] = True
    with pytest.raises(ValueError, match="stress-test"):
        CaptureTruth(**row)


def test_missing_media_rejected(tmp_path):
    (tmp_path / "truth.json").write_text(json.dumps(example()))
    with pytest.raises(ValueError, match="Missing"):
        validate_capture(tmp_path)


def test_media_cannot_escape_case_folder(tmp_path):
    row = example()
    row["seller_video"] = "../outside.mp4"
    (tmp_path / "truth.json").write_text(json.dumps(row))
    with pytest.raises(ValueError, match="invalid capture path"):
        validate_capture(tmp_path)


def test_workflow_errors_and_uncertainty_remain_in_denominators():
    from eval.workflow_eval import metrics
    rows = [{"group": "a", "actual_change": True, "same_garment": True, "expected_assessment": "differs", "assessment": "differs"},
            {"group": "b", "actual_change": True, "same_garment": True, "expected_assessment": "differs", "assessment": "cant_tell"},
            {"group": "c", "actual_change": True, "same_garment": True, "expected_assessment": "differs", "error": "failed"}]
    report = metrics(rows)
    assert report["change_recall"]["k"] == 1
    assert report["change_recall"]["n"] == 3
    assert report["errors"] == 1
