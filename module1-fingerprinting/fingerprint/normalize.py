# fingerprint/normalize.py — Pre-normalization pipeline for video frames.

import cv2
import numpy as np
import config


def strip_letterbox(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Crop out top/bottom/left/right black bars by detecting rows/columns
    whose pixel variance falls below NORM_LETTERBOX_THRESHOLD.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    thresh = config.NORM_LETTERBOX_THRESHOLD

    row_var = gray.var(axis=1)  # variance of each row
    col_var = gray.var(axis=0)  # variance of each column

    rows = np.where(row_var > thresh)[0]
    cols = np.where(col_var > thresh)[0]

    if rows.size == 0 or cols.size == 0:
        return frame_bgr  # all black — return as-is to avoid crash

    return frame_bgr[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def center_crop_square(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Take the central square region (80% of the shorter side).
    Makes mild edge-cropping attacks a no-op.
    """
    h, w = frame_bgr.shape[:2]
    side = int(min(h, w) * 0.8)
    cy, cx = h // 2, w // 2
    half = side // 2
    return frame_bgr[cy - half:cy + half, cx - half:cx + half]


def mask_logo_regions(gray: np.ndarray) -> np.ndarray:
    """
    Zero out top-left and bottom-right squares (each NORM_LOGO_MASK_RATIO
    of the frame dimension) to defeat logo overlay attacks.
    """
    h, w = gray.shape[:2]
    mask_h = int(h * config.NORM_LOGO_MASK_RATIO)
    mask_w = int(w * config.NORM_LOGO_MASK_RATIO)

    out = gray.copy()
    out[:mask_h, :mask_w] = 0            # top-left
    out[h - mask_h:, w - mask_w:] = 0   # bottom-right
    return out


def histogram_equalize(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE-style equalization to defeat brightness/contrast attacks."""
    return cv2.equalizeHist(gray)


def canonicalize_frame(frame_bgr: np.ndarray) -> np.ndarray:
    """
    Full pipeline:
      strip_letterbox → center_crop_square → grayscale →
      resize to NORM_TARGET_SIZE → mask_logo_regions → histogram_equalize
    Returns a normalized 2D grayscale array ready for hashing.
    """
    frame = strip_letterbox(frame_bgr)
    frame = center_crop_square(frame)

    # Safety: ensure we still have a non-zero frame
    if frame.size == 0:
        frame = frame_bgr

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, config.NORM_TARGET_SIZE, interpolation=cv2.INTER_AREA)
    gray = mask_logo_regions(gray)
    gray = histogram_equalize(gray)
    return gray
