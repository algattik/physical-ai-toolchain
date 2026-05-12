"""Tests for path traversal protection."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from scene_aligner import aligner


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / 'roots'
    base.mkdir()
    (base / 'good').mkdir()
    (base / 'good' / 'meta').mkdir()
    (base / 'good' / 'meta' / 'info.json').write_text('{}')
    monkeypatch.setattr(aligner, 'DATASETS_DIR', base)
    return base


def test_safe_dataset_dir_resolves_simple_path(tmp_path, monkeypatch):
    base = _setup(tmp_path, monkeypatch)
    out = aligner._safe_dataset_dir('good')
    assert out == (base / 'good').resolve()


def test_safe_dataset_dir_rejects_parent_traversal(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        aligner._safe_dataset_dir('../etc/passwd')
    assert exc.value.status_code == 400


def test_safe_dataset_dir_rejects_absolute_path(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        aligner._safe_dataset_dir('/etc')
    assert exc.value.status_code in (400, 404)


def test_safe_dataset_dir_404_for_missing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        aligner._safe_dataset_dir('does-not-exist')
    assert exc.value.status_code == 404
