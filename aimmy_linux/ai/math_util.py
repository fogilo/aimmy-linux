"""
Math utilities for Aimmy Linux.
Port of AILogic/MathUtil.cs

Provides distance functions, target scoring, YOLOv8 detection count
calculation, and bitmap-to-float array conversion using numpy.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Prediction:
    """A single detection result from the AI model."""
    # Bounding box in model space (x_min, y_min, width, height)
    rect_x: float = 0.0
    rect_y: float = 0.0
    rect_w: float = 0.0
    rect_h: float = 0.0
    confidence: float = 0.0
    class_id: int = 0
    class_name: str = "Enemy"
    # Center position translated to [0,1] range
    center_x_translated: float = 0.0
    center_y_translated: float = 0.0
    # Absolute screen center position
    screen_center_x: float = 0.0
    screen_center_y: float = 0.0


def l2_norm_squared(x: np.ndarray, y: np.ndarray) -> float:
    """Squared L2 distance between two points."""
    diff = x - y
    return float(np.dot(diff, diff))


def distance_sq(a: Prediction, b: Prediction) -> float:
    """Squared distance between two predictions' screen centers."""
    dx = a.screen_center_x - b.screen_center_x
    dy = a.screen_center_y - b.screen_center_y
    return dx * dx + dy * dy


def calculate_target_score(
    candidate: Prediction,
    current_target: Optional[Prediction],
    predicted_x: float,
    predicted_y: float,
    current_lock_score: float,
    max_lock_score: float,
    threshold: float,
) -> float:
    """Score a detection candidate for target selection.

    Higher score = better candidate. Combines distance, confidence,
    size, and lock-on bonus.
    """
    dx = candidate.screen_center_x - predicted_x
    dy = candidate.screen_center_y - predicted_y
    dist_sq = dx * dx + dy * dy

    threshold_sq = threshold * threshold
    distance_score = max(0.0, 1.0 - (dist_sq / threshold_sq))

    confidence_bonus = candidate.confidence * 0.3

    area = candidate.rect_w * candidate.rect_h
    size_bonus = min(0.2, area / 50000.0)

    lock_bonus = 0.0
    if current_target is not None and distance_score > 0.3:
        lock_bonus = (current_lock_score / max_lock_score) * 0.5

    return distance_score + confidence_bonus + size_bonus + lock_bonus


def calculate_num_detections(image_size: int) -> int:
    """Calculate YOLOv8 detection grid size.

    YOLOv8 uses 3 detection heads at strides 8, 16, 32:
    total = (size/8)² + (size/16)² + (size/32)²
    """
    s8 = image_size // 8
    s16 = image_size // 16
    s32 = image_size // 32
    return (s8 * s8) + (s16 * s16) + (s32 * s32)


def image_to_float_chw(image: np.ndarray, image_size: int) -> np.ndarray:
    """Convert an RGB image (HxWx3 uint8) to CHW float32 tensor.

    The C# version uses unsafe pointer manipulation for speed.
    In Python, numpy vectorized operations achieve similar throughput.

    Args:
        image: numpy array of shape (H, W, 3) in RGB format, uint8
        image_size: Expected square image size

    Returns:
        numpy array of shape (1, 3, H, W) in float32, values [0, 1]
    """
    # Ensure correct size
    if image.shape[0] != image_size or image.shape[1] != image_size:
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(image)
        pil_img = pil_img.resize((image_size, image_size), PILImage.BILINEAR)
        image = np.array(pil_img)

    # Convert uint8 [0,255] to float32 [0,1] and transpose from HWC to CHW
    # numpy is very efficient at this — roughly equivalent to the C# SIMD path
    result = image.astype(np.float32) / 255.0
    result = result.transpose(2, 0, 1)  # HWC -> CHW (RGB channels first)
    result = np.expand_dims(result, axis=0)  # Add batch dim: (1, 3, H, W)
    return np.ascontiguousarray(result)


def get_distance_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    """Squared Euclidean distance between two points."""
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy
