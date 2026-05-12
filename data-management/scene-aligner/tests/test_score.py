"""Tests for the alignment score's low-texture guard."""

from __future__ import annotations

import numpy as np

from scene_aligner.aligner import _alignment_score


def test_score_returns_none_for_flat_frames():
    flat = np.full((120, 160, 3), 128, dtype=np.uint8)
    assert _alignment_score(flat, flat) is None


def test_score_high_for_identical_textured_frames():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, size=(120, 160, 3), dtype=np.uint8)
    s = _alignment_score(a.copy(), a.copy())
    assert s is not None
    assert s > 0.99


def test_score_drops_for_independent_textured_frames():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, size=(120, 160, 3), dtype=np.uint8)
    b = rng.integers(0, 255, size=(120, 160, 3), dtype=np.uint8)
    s = _alignment_score(a, b)
    assert s is not None
    assert s < 0.2
