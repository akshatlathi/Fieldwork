"""Regression checks for the observed legacy and missing-label errors."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train.labels import defect_label, grade_label


@pytest.mark.parametrize("value", ["Yes", "yes", " Minor ", "major", "Major"])
def test_defect_positive(value):
    assert defect_label(value) == 1


@pytest.mark.parametrize("value", ["No", "none", "None", " NO "])
def test_explicit_absence(value):
    assert defect_label(value) == 0


@pytest.mark.parametrize("value", [None, "", " ", float("nan"), "unlabelled"])
def test_missing_is_not_clean(value):
    assert defect_label(value) == -1


def test_explicit_sensitivity_policy():
    assert defect_label(None, null_policy="negative") == 0


@pytest.mark.parametrize("value", [None, "", 0, 6, 3.5])
def test_bad_grades_excluded(value):
    assert grade_label(value) == -1


def test_conformal_finite_sample_rank():
    import numpy as np
    from train.evaluate_heads import threshold
    # Nine calibration scores .1,...,.9 require the ninth order statistic at alpha=.1.
    probabilities = np.zeros((9, 5))
    probabilities[:, 0] = 1 - np.arange(1, 10) / 10
    assert threshold(probabilities, np.ones(9, dtype=int)) == pytest.approx(.9)
