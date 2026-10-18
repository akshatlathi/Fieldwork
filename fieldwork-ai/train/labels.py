"""Dataset label policy shared by audits and training. Unknown is never clean by default."""
import numpy as np


def defect_label(value, *, null_policy="exclude"):
    if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() == "":
        return 0 if null_policy == "negative" else -1
    text = str(value).strip().casefold()
    if text in {"minor", "major", "yes"}:
        return 1
    if text in {"none", "no"}:
        return 0
    return -1


def grade_label(value):
    try:
        number = float(value)
        return int(number) if number.is_integer() and 1 <= number <= 5 else -1
    except (ValueError, TypeError):
        return -1
