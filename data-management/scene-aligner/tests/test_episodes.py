"""Tests for the parquet-based episode metadata reader."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scene_aligner.episodes import (
    episode_video_path,
    find_episode,
    load_episodes,
)


def _write_episode_parquet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), str(path))


@pytest.fixture
def dataset(tmp_path: Path) -> tuple[Path, str]:
    ds_dir = tmp_path / 'ds'
    (ds_dir / 'meta').mkdir(parents=True)
    (ds_dir / 'meta' / 'info.json').write_text(json.dumps({'fps': 30}))

    rows = [
        {
            'episode_index': 0,
            'tasks': ['pick'],
            'length': 90,
            'videos/observation.images.image_chin/chunk_index': 0,
            'videos/observation.images.image_chin/file_index': 0,
            'videos/observation.images.image_chin/from_timestamp': 0.0,
            'videos/observation.images.image_chin/to_timestamp': 3.0,
        },
        {
            'episode_index': 1,
            'tasks': ['place'],
            'length': 60,
            'videos/observation.images.image_chin/chunk_index': 0,
            'videos/observation.images.image_chin/file_index': 0,
            'videos/observation.images.image_chin/from_timestamp': 3.0,
            'videos/observation.images.image_chin/to_timestamp': 5.0,
        },
        {
            'episode_index': 2,
            'tasks': ['pick'],
            'length': 30,
            'videos/observation.images.image_chin/chunk_index': 1,
            'videos/observation.images.image_chin/file_index': 0,
            'videos/observation.images.image_chin/from_timestamp': 0.0,
            'videos/observation.images.image_chin/to_timestamp': 1.0,
        },
    ]
    _write_episode_parquet(
        ds_dir / 'meta' / 'episodes' / 'chunk-000' / 'file-000.parquet',
        rows,
    )
    return ds_dir, 'ds'


def test_load_episodes_returns_all_in_index_order(dataset):
    ds_dir, ds_id = dataset
    eps = load_episodes(ds_dir, ds_id, fps=30.0)
    assert [e['idx'] for e in eps] == [0, 1, 2]
    assert eps[0]['length'] == 90
    assert eps[0]['duration_s'] == pytest.approx(3.0)
    assert eps[0]['tasks'] == ['pick']


def test_load_episodes_caches_and_walks_multiple_files(tmp_path):
    ds_dir = tmp_path / 'big'
    (ds_dir / 'meta').mkdir(parents=True)
    (ds_dir / 'meta' / 'info.json').write_text('{}')
    _write_episode_parquet(
        ds_dir / 'meta' / 'episodes' / 'chunk-000' / 'file-000.parquet',
        [{'episode_index': 0, 'tasks': [], 'length': 10}],
    )
    _write_episode_parquet(
        ds_dir / 'meta' / 'episodes' / 'chunk-000' / 'file-001.parquet',
        [{'episode_index': 1, 'tasks': [], 'length': 20}],
    )
    eps = load_episodes(ds_dir, 'big-id', fps=30.0)
    assert {e['idx'] for e in eps} == {0, 1}


def test_find_episode_returns_match_and_none(dataset):
    ds_dir, ds_id = dataset
    assert find_episode(ds_dir, ds_id, 1, fps=30.0)['length'] == 60
    assert find_episode(ds_dir, ds_id, 99, fps=30.0) is None


def test_episode_video_path_uses_chunk_and_file_indices(dataset):
    ds_dir, ds_id = dataset
    ep = find_episode(ds_dir, ds_id, 2, fps=30.0)
    path = episode_video_path(ds_dir, 'observation.images.image_chin', ep)
    assert path.name == 'file-000.mp4'
    assert path.parent.name == 'chunk-001'
    assert path.parent.parent.name == 'observation.images.image_chin'


def test_episode_video_path_returns_none_for_unknown_camera(dataset):
    ds_dir, ds_id = dataset
    ep = find_episode(ds_dir, ds_id, 0, fps=30.0)
    assert episode_video_path(ds_dir, 'observation.images.image_missing', ep) is None
