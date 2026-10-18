"""Untrusted model outlines become explicit, conservative reference masks."""
from pathlib import Path

import cv2
import numpy as np


def valid_outline(points: list[list[int]]) -> bool:
    if not 6 <= len(points) <= 40:
        return False
    if any(len(p) != 2 or any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 1000 for v in p) for p in points):
        return False
    contour = np.array([[x, y] for y, x in points], np.int32)
    # Reject degenerate polygons. This is structural validity, not a claim that
    # a model has segmented the garment correctly.
    return abs(cv2.contourArea(contour)) >= 20000


def reference_masks(coverage: dict, frames: dict[str, Path]) -> dict[str, np.ndarray]:
    masks = {}
    for view in coverage.get("views", []):
        points = view.get("garment_outline", [])
        evidence = view.get("evidence", [])
        if view.get("region") not in ("front", "back") or view.get("status") != "shown" or not evidence or not valid_outline(points):
            continue
        # Each outline belongs ONLY to its first cited frame. Never transplant
        # coordinates to another photograph of the same region.
        fid = evidence[0].get("frame_id")
        if fid not in frames:
            continue
        image = cv2.imread(str(frames[fid]))
        if image is None:
            continue
        h, w = image.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        contour = np.array([[min(w-1, round(x*w/1000)), min(h-1, round(y*h/1000))] for y, x in points], np.int32)
        cv2.fillPoly(mask, [contour], 255)
        # Remove uncertain boundary pixels; garment edges often include bed/floor.
        border = max(1, round(min(h, w)*.005))
        mask = cv2.erode(mask, np.ones((2*border+1, 2*border+1), np.uint8))
        if np.mean(mask > 0) < .02:
            continue
        masks[fid] = cv2.bitwise_or(masks[fid], mask) if fid in masks else mask
    return masks
