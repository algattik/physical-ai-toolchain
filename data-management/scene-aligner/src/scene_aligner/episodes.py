"""Episode metadata reader for LeRobot v3 datasets.

Walks ``meta/episodes/**/*.parquet`` for a dataset and exposes per-episode
metadata: index, length (frames), task labels, duration, and per-camera
location info needed to seek into the chunked MP4s for that episode's first
frame.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

import pyarrow.parquet as pq

_episodes_cache: dict[str, list[dict]] = {}
_episodes_lock = threading.Lock()


def _row_value(row: dict, key: str, default: Any = None) -> Any:
    if key not in row:
        return default
    val = row[key]
    if hasattr(val, 'as_py'):
        val = val.as_py()
    return val


def load_episodes(ds_dir: Path, dataset_id: str, fps: float = 30.0) -> list[dict]:
    """Return list of per-episode metadata dicts, sorted by episode_index."""
    with _episodes_lock:
        if dataset_id in _episodes_cache:
            return _episodes_cache[dataset_id]

    ep_root = ds_dir / 'meta' / 'episodes'
    out: list[dict] = []
    if ep_root.is_dir():
        for pq_path in sorted(ep_root.glob('**/*.parquet')):
            try:
                table = pq.read_table(str(pq_path))
            except Exception:
                continue
            cols = set(table.column_names)
            cam_keys = sorted({
                c.split('/')[1] for c in cols
                if c.startswith('videos/') and c.endswith('/chunk_index')
            })
            df = table.to_pylist()
            for row in df:
                idx = _row_value(row, 'episode_index')
                if idx is None:
                    continue
                length = _row_value(row, 'length', 0) or 0
                tasks_val = _row_value(row, 'tasks', []) or []
                if isinstance(tasks_val, str):
                    tasks_val = [tasks_val]
                cameras: dict[str, dict] = {}
                for cam in cam_keys:
                    cameras[cam] = {
                        'chunk_index': int(_row_value(
                            row, f'videos/{cam}/chunk_index', 0) or 0),
                        'file_index': int(_row_value(
                            row, f'videos/{cam}/file_index', 0) or 0),
                        'from_timestamp': float(_row_value(
                            row, f'videos/{cam}/from_timestamp', 0.0) or 0.0),
                        'to_timestamp': float(_row_value(
                            row, f'videos/{cam}/to_timestamp', 0.0) or 0.0),
                    }
                duration_s = (length / fps) if fps else 0.0
                out.append({
                    'idx': int(idx),
                    'length': int(length),
                    'duration_s': duration_s,
                    'tasks': list(tasks_val),
                    'cameras': cameras,
                })

    out.sort(key=lambda e: e['idx'])
    with _episodes_lock:
        _episodes_cache[dataset_id] = out
    return out


def find_episode(ds_dir: Path, dataset_id: str, episode_idx: int,
                 fps: float = 30.0) -> Optional[dict]:
    for ep in load_episodes(ds_dir, dataset_id, fps=fps):
        if ep['idx'] == episode_idx:
            return ep
    return None


def episode_video_path(ds_dir: Path, camera_key: str, ep: dict) -> Optional[Path]:
    cam = ep.get('cameras', {}).get(camera_key)
    if cam is None:
        return None
    return (ds_dir / 'videos' / camera_key
            / f'chunk-{cam["chunk_index"]:03d}'
            / f'file-{cam["file_index"]:03d}.mp4')
