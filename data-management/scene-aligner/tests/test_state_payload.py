"""Tests for the Pydantic state payload validator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scene_aligner.aligner import _StatePayload


def test_state_payload_accepts_valid():
    p = _StatePayload(
        dataset='ok/v1',
        camera='observation.images.image_chin',
        episode=10,
        ref_op=0.5,
        live_op=0.5,
        invert_ref=True,
        invert_live=False,
    )
    assert p.dataset == 'ok/v1'
    assert p.camera == 'observation.images.image_chin'
    assert p.episode == 10


def test_state_payload_rejects_traversal_dataset():
    with pytest.raises(ValidationError):
        _StatePayload(dataset='../escape')


def test_state_payload_rejects_absolute_dataset():
    with pytest.raises(ValidationError):
        _StatePayload(dataset='/etc')


def test_state_payload_rejects_camera_with_slash():
    with pytest.raises(ValidationError):
        _StatePayload(camera='hax/escape')


def test_state_payload_rejects_camera_with_control_char():
    with pytest.raises(ValidationError):
        _StatePayload(camera='hax\nbad')


@pytest.mark.parametrize('bad', [-0.01, 1.01, -1, 100])
def test_state_payload_rejects_out_of_range_opacity(bad):
    with pytest.raises(ValidationError):
        _StatePayload(ref_op=bad)


def test_state_payload_rejects_negative_episode():
    with pytest.raises(ValidationError):
        _StatePayload(episode=-1)
