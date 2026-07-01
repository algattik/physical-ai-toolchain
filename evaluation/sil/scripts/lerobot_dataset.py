"""Shared LeRobot dataset helpers for the SIL evaluation scripts."""

from __future__ import annotations

from typing import Any


def select_image_key(features: dict[str, Any]) -> str:
    """Return the image feature key to feed the policy.

    Prefers an ``observation.images.*`` camera, falls back to the first
    video/image feature, and finally to a conventional default when the
    dataset exposes no image features.
    """
    video_keys = [k for k, v in features.items() if v.get("dtype") in ("video", "image")]
    return next(
        (k for k in video_keys if k.startswith("observation.images.")),
        video_keys[0] if video_keys else "observation.images.color",
    )
