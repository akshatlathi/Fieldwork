"""Align a handover photo to the listing reference photo (AKAZE + RANSAC homography)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import cv2
import numpy as np

MAX_SIDE = 1280
MIN_INLIERS = 25


@dataclass
class AlignResult:
    ok: bool
    H: np.ndarray | None
    inliers: int
    inlier_ratio: float
    warped_path: Path | None
    method: str = "akaze"
    valid_mask_path: Path | None = None
    overlap_fraction: float = 0.0
    garment_focused: bool = False


def _load(path: str | Path) -> tuple[np.ndarray, float]:
    img = cv2.imread(str(path))
    s = min(1.0, MAX_SIDE / max(img.shape[:2]))
    if s < 1.0:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    return img, s


def _sane(H: np.ndarray) -> bool:
    A = H[:2, :2]
    det = np.linalg.det(A)
    if not 0.2 <= det <= 5 or abs(H[2, 0]) > 2e-3 or abs(H[2, 1]) > 2e-3:
        return False
    sv = np.linalg.svd(A, compute_uv=False)
    return sv[0] / max(sv[1], 1e-9) < 4


def align(ref_path: str | Path, img_path: str | Path, *, method: str = "auto", reference_mask: np.ndarray | None = None) -> AlignResult:
    """Try AKAZE, then scale-robust classical SIFT with the same geometric guards."""
    if method not in ("auto", "akaze", "sift"):
        raise ValueError("Unknown alignment method")
    methods = ("akaze", "sift") if method == "auto" else (method,)
    result = AlignResult(False, None, 0, 0., None)
    for candidate in methods:
        result = (_align_method(ref_path, img_path, candidate, reference_mask=reference_mask)
                  if reference_mask is not None else _align_method(ref_path, img_path, candidate))
        if result.ok:
            return result
    return result


def _align_method(ref_path: str | Path, img_path: str | Path, method: str, reference_mask: np.ndarray | None = None) -> AlignResult:
    ref, s_ref = _load(ref_path)
    img, s_img = _load(img_path)
    akaze = cv2.AKAZE_create() if method == "akaze" else cv2.SIFT_create(nfeatures=3000)
    feature_mask = None
    if reference_mask is not None:
        feature_mask = cv2.resize((reference_mask > 0).astype(np.uint8)*255, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST)
    kr, dr = akaze.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), feature_mask)
    if feature_mask is not None and dr is not None:
        distance = cv2.distanceTransform(feature_mask, cv2.DIST_L2, 3)
        inside = [i for i, kp in enumerate(kr) if distance[min(distance.shape[0]-1, round(kp.pt[1])), min(distance.shape[1]-1, round(kp.pt[0]))] > max(3, 1.5*kp.size)]
        kr, dr = [kr[i] for i in inside], dr[inside] if inside else None
    ki, di = akaze.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
    if dr is None or di is None or len(kr) < 8 or len(ki) < 8:
        return AlignResult(False, None, 0, 0.0, None)
    pairs = cv2.BFMatcher(cv2.NORM_HAMMING if method == "akaze" else cv2.NORM_L2).knnMatch(di, dr, k=2)
    good = [m for p in pairs if len(p) == 2 for m, n in [p] if m.distance < 0.8 * n.distance]
    # Repeated fabric textures must not map many received points onto one seam.
    unique = {}
    for match in sorted(good, key=lambda match: match.distance):
        unique.setdefault(match.trainIdx, match)
    good = list(unique.values())
    if len(good) < 8:
        return AlignResult(False, None, 0, 0.0, None)
    src = np.float32([ki[m.queryIdx].pt for m in good])
    dst = np.float32([kr[m.trainIdx].pt for m in good])
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if H is None:
        return AlignResult(False, None, 0, 0.0, None)
    inliers = int(mask.sum())
    ratio = inliers / len(good)
    ok = bool(inliers >= MIN_INLIERS and ratio >= 0.25 and _sane(H))
    warped_path = None
    mask_path = None
    overlap = 0.
    if ok:
        # H maps resized img -> resized ref; warp the full-res img into the full-res ref frame
        full_ref = cv2.imread(str(ref_path))
        full_img = cv2.imread(str(img_path))
        S_i = np.diag([s_img, s_img, 1.0])
        S_r_inv = np.diag([1 / s_ref, 1 / s_ref, 1.0])
        H_full = S_r_inv @ H @ S_i
        valid = cv2.warpPerspective(np.ones(full_img.shape[:2], np.uint8) * 255, H_full,
                                    (full_ref.shape[1], full_ref.shape[0]), flags=cv2.INTER_NEAREST)
        overlap = float(np.mean(valid > 0))
        if reference_mask is not None:
            garment_mask = cv2.resize((reference_mask > 0).astype(np.uint8)*255, (full_ref.shape[1], full_ref.shape[0]), interpolation=cv2.INTER_NEAREST)
            valid = cv2.bitwise_and(valid, garment_mask)
            # A homography fitted to one tiny detail cannot establish correspondence
            # elsewhere (for example, extrapolating a neckline onto a side seam).
            support = np.zeros(full_ref.shape[:2], np.uint8)
            points = dst[mask.ravel().astype(bool)] / s_ref
            hull = cv2.convexHull(points.astype(np.float32)).astype(np.int32)
            cv2.fillConvexPoly(support, hull, 255)
            valid = cv2.bitwise_and(valid, support)
            overlap = float(np.count_nonzero(valid) / max(1, np.count_nonzero(garment_mask)))
        if overlap < 0.3:
            return AlignResult(False, H_full, inliers, float(ratio), None, method, None, overlap)
        warped = cv2.warpPerspective(full_img, H_full, (full_ref.shape[1], full_ref.shape[0]), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        p = Path(img_path)
        # One received view may match several references. Keep each warp distinct;
        # otherwise later alignments silently replace earlier report evidence.
        ref_tag = hashlib.sha256(str(Path(ref_path).resolve()).encode()).hexdigest()[:16]
        warped_path = p.with_name(f"{p.stem}_{ref_tag}_aligned.jpg")
        if not cv2.imwrite(str(warped_path), warped, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError(f"Could not save aligned evidence: {warped_path}")
        mask_path = warped_path.with_name(warped_path.stem + "_valid.png")
        if not cv2.imwrite(str(mask_path), valid):
            raise OSError("Could not save alignment coverage mask")
        H = H_full
    return AlignResult(ok, H, inliers, float(ratio), warped_path, method, mask_path, overlap, reference_mask is not None)
