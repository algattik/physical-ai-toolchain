#!/usr/bin/env python3
"""Scene alignment webapp.

Serves a single-page UI that overlays the live ROS 2 camera feed (MJPEG) on
top of the first frame of the chosen dataset and camera. Operators use it to
reset a physical scene to match a recorded starting pose before capturing new
demonstrations.
"""

from __future__ import annotations

import io
import os
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import rclpy
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image

import queue
from collections import OrderedDict
from .episodes import (
    episode_video_path,
    find_episode,
    load_episodes,
)
from pydantic import BaseModel, Field, field_validator

DATASETS_DIR = Path(os.environ.get('DATASETS_DIR', '/data/sample_datasets'))
DEFAULT_CAMERA_KEY = os.environ.get('DEFAULT_CAMERA_KEY', '')
# Topic derived from a camera key: ``observation.images.image_<name>`` →
# ``/sensor/<name>_camera/rgbd/color`` with the default template. Override per
# deployment to match your robot's topic naming.
CAMERA_TOPIC_TEMPLATE = os.environ.get(
    'CAMERA_TOPIC_TEMPLATE', '/sensor/{name}_camera/rgbd/color')
STREAM_FPS = float(os.environ.get('STREAM_FPS', '15'))
JPEG_QUALITY = int(os.environ.get('JPEG_QUALITY', '70'))
# Maximum number of cached references and thumbnails. References hold both
# JPEG bytes and a full BGR ndarray (~900 KB at 640×480) so the cap matters.
REFERENCE_CACHE_MAX = int(os.environ.get('REFERENCE_CACHE_MAX', '64'))
THUMBNAIL_CACHE_MAX = int(os.environ.get('THUMBNAIL_CACHE_MAX', '512'))


def _camera_short_name(camera_key: str) -> str:
    """Strip the lerobot ``observation.images.image_`` prefix if present."""
    for prefix in ('observation.images.image_', 'observation.images.'):
        if camera_key.startswith(prefix):
            return camera_key[len(prefix):]
    return camera_key


def _topic_for_camera(camera_key: str) -> str:
    return CAMERA_TOPIC_TEMPLATE.format(
        name=_camera_short_name(camera_key),
        key=camera_key,
    )


def _camera_video_path(ds_dir: Path, camera_key: str) -> Path:
    return ds_dir / 'videos' / camera_key / 'chunk-000' / 'file-000.mp4'

# ---------------------------------------------------------------------------
# Live frame slot, populated by background ROS subscriber
# ---------------------------------------------------------------------------

_frame_lock = threading.Lock()
_latest_frame: Optional[np.ndarray] = None
_frame_seq = 0


class CameraSubscriber(Node):
    def __init__(self) -> None:
        super().__init__('aligner_camera_subscriber')
        self._qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=2,
        )
        self._sub = None
        self._topic = ''
        self._pending: queue.Queue[str] = queue.Queue()
        # Drain pending topic changes on the ROS executor thread.
        self.create_timer(0.05, self._apply_pending)

    def request_topic(self, topic: str) -> None:
        """Thread-safe topic change request. Applied on the ROS executor."""
        self._pending.put(topic)

    def _apply_pending(self) -> None:
        latest: Optional[str] = None
        try:
            while True:
                latest = self._pending.get_nowait()
        except queue.Empty:
            pass
        if latest is None or latest == self._topic:
            return
        if self._sub is not None:
            self.destroy_subscription(self._sub)
            self._sub = None
        self._topic = latest
        if latest:
            self._sub = self.create_subscription(
                Image, latest, self._on_image, self._qos)
            self.get_logger().info(f'Subscribed to {latest}')
            global _latest_frame
            with _frame_lock:
                _latest_frame = None  # invalidate previous camera's frame

    @staticmethod
    def _decode(msg: Image) -> Optional[np.ndarray]:
        enc = msg.encoding.lower()
        h, w = msg.height, msg.width
        step = msg.step or 0
        try:
            buf = np.frombuffer(msg.data, dtype=np.uint8)
            channels = {
                'bgr8': 3, 'rgb8': 3, 'bgra8': 4, 'rgba8': 4,
                'mono8': 1, '8uc1': 1,
            }.get(enc)
            if channels is None:
                return None
            row_pixels = step // channels if step else w
            if row_pixels < w:
                return None
            view = buf.reshape(h, row_pixels * channels) if step else buf.reshape(h, w * channels)
            view = view[:, : w * channels]  # drop row padding
            if channels == 1:
                gray = view.reshape(h, w)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            arr = view.reshape(h, w, channels)
            if enc == 'bgr8':
                return arr.copy()  # detach from msg.data
            if enc == 'rgb8':
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            if enc == 'bgra8':
                return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
            if enc == 'rgba8':
                return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        except (ValueError, cv2.error):
            return None
        return None

    def _on_image(self, msg: Image) -> None:
        global _latest_frame, _frame_seq
        frame = self._decode(msg)
        if frame is None:
            self.get_logger().warning(
                f'Unsupported encoding/shape: enc={msg.encoding} '
                f'{msg.width}x{msg.height} step={msg.step}',
                throttle_duration_sec=5.0)
            return
        with _frame_lock:
            _latest_frame = frame
            _frame_seq += 1


_camera_node: Optional[CameraSubscriber] = None
_pending_initial_topic: Optional[str] = None  # set before node exists


def _ros_thread() -> None:
    global _camera_node
    rclpy.init()
    node = CameraSubscriber()
    _camera_node = node
    if _pending_initial_topic:
        node.request_topic(_pending_initial_topic)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


# ---------------------------------------------------------------------------
# Reference frame extraction (cached)
# ---------------------------------------------------------------------------

_reference_cache: OrderedDict[tuple[str, str, int], tuple[bytes, np.ndarray]] = OrderedDict()
_thumbnail_cache: OrderedDict[tuple[str, str, int], bytes] = OrderedDict()
_info_cache: dict[str, dict] = {}
_labels_cache: dict[str, tuple[float, dict]] = {}  # dataset_id -> (mtime, parsed)
_reference_lock = threading.Lock()


def _cache_get(cache: OrderedDict, key):
    if key in cache:
        cache.move_to_end(key)
        return cache[key]
    return None


def _cache_put(cache: OrderedDict, key, value, max_items: int) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > max_items:
        cache.popitem(last=False)


def _list_cameras_for_info(info: dict) -> list[str]:
    """Camera keys present in info.json (features with dtype == 'video')."""
    feats = info.get('features', {}) if isinstance(info, dict) else {}
    return sorted(k for k, v in feats.items()
                  if isinstance(v, dict) and v.get('dtype') == 'video')


def _list_cameras(ds_dir: Path, dataset_id: str) -> list[str]:
    info = _read_info(dataset_id)
    keys = _list_cameras_for_info(info)
    # Filter to those that actually have a video file on disk.
    return [k for k in keys if _camera_video_path(ds_dir, k).is_file()]


def _resolve_camera(ds_dir: Path, dataset_id: str,
                    requested: Optional[str]) -> Optional[str]:
    cams = _list_cameras(ds_dir, dataset_id)
    if not cams:
        return None
    if requested and requested in cams:
        return requested
    if DEFAULT_CAMERA_KEY and DEFAULT_CAMERA_KEY in cams:
        return DEFAULT_CAMERA_KEY
    return cams[0]


import json
import re

_DATE_RE = re.compile(r'(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z')


def _acquired_at(dataset_id: str, ds_dir: Path) -> Optional[str]:
    """Parse ISO acquisition timestamp from path; fall back to fs mtime."""
    m = _DATE_RE.search(dataset_id)
    if m:
        y, mo, d, h, mi, s = m.groups()
        return f'{y}-{mo}-{d}T{h}:{mi}:{s}Z'
    info_path = ds_dir / 'meta' / 'info.json'
    src = info_path if info_path.is_file() else ds_dir
    try:
        ts = src.stat().st_mtime
    except OSError:
        return None
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).isoformat(
        timespec='seconds').replace('+00:00', 'Z')


def _safe_dataset_dir(dataset_id: str) -> Path:
    """Resolve dataset_id under DATASETS_DIR, blocking traversal."""
    base = DATASETS_DIR.resolve()
    target = (base / dataset_id).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(400, f'Bad dataset id: {dataset_id}')
    if not target.is_dir():
        raise HTTPException(404, f'No such dataset: {dataset_id}')
    return target


def _list_datasets() -> list[dict]:
    """A dataset is any directory containing meta/info.json. Walk recursively."""
    if not DATASETS_DIR.is_dir():
        return []
    base = DATASETS_DIR.resolve()
    out: list[dict] = []
    seen: set[Path] = set()
    for info_path in sorted(base.glob('**/meta/info.json')):
        ds_dir = info_path.parent.parent.resolve()
        if ds_dir in seen:
            continue
        seen.add(ds_dir)
        rel = ds_dir.relative_to(base).as_posix()
        meta = _read_info(rel)
        cams = _list_cameras(ds_dir, rel)
        out.append({
            'id': rel,
            'name': ds_dir.name,
            'acquired_at': _acquired_at(rel, ds_dir),
            'robot_type': meta.get('robot_type'),
            'total_episodes': meta.get('total_episodes'),
            'total_frames': meta.get('total_frames'),
            'total_tasks': meta.get('total_tasks'),
            'fps': meta.get('fps'),
            'codebase_version': meta.get('codebase_version'),
            'cameras': cams,
            'has_video': bool(cams),
        })
    return out


def _read_info(dataset_id: str) -> dict:
    if dataset_id in _info_cache:
        return _info_cache[dataset_id]
    info_path = _safe_dataset_dir(dataset_id) / 'meta' / 'info.json'
    if not info_path.is_file():
        return {}
    try:
        with open(info_path) as f:
            data = json.load(f)
    except Exception:
        data = {}
    _info_cache[dataset_id] = data
    return data


def _read_labels(dataset_id: str) -> dict:
    """Load the dataviewer's episode_labels.json. Cached by file mtime so edits
    in the dataviewer show up here without restarting the aligner."""
    labels_path = _safe_dataset_dir(dataset_id) / 'meta' / 'episode_labels.json'
    if not labels_path.is_file():
        return {'available_labels': [], 'episodes': {}}
    try:
        mtime = labels_path.stat().st_mtime
    except OSError:
        mtime = 0.0
    cached = _labels_cache.get(dataset_id)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        with open(labels_path) as f:
            data = json.load(f)
    except Exception:
        data = {'available_labels': [], 'episodes': {}}
    data.setdefault('available_labels', [])
    data.setdefault('episodes', {})
    _labels_cache[dataset_id] = (mtime, data)
    return data


def _episode_labels_map(dataset_id: str) -> dict[int, list[str]]:
    raw = _read_labels(dataset_id).get('episodes', {})
    out: dict[int, list[str]] = {}
    for k, v in raw.items():
        try:
            out[int(k)] = list(v) if isinstance(v, list) else []
        except (TypeError, ValueError):
            continue
    return out


def _load_reference(dataset_id: str, camera_key: str,
                    episode_idx: int = 0) -> tuple[bytes, np.ndarray]:
    key = (dataset_id, camera_key, episode_idx)
    with _reference_lock:
        cached = _cache_get(_reference_cache, key)
        if cached is not None:
            return cached

    ds_dir = _safe_dataset_dir(dataset_id)
    fps_meta = float(_read_info(dataset_id).get('fps') or 30.0)
    ep = find_episode(ds_dir, dataset_id, episode_idx, fps=fps_meta)
    if ep is not None:
        video_path = episode_video_path(ds_dir, camera_key, ep)
        from_ts = ep['cameras'].get(camera_key, {}).get('from_timestamp', 0.0)
    else:
        # Fallback: chunk-000/file-000, frame 0.
        video_path = _camera_video_path(ds_dir, camera_key)
        from_ts = 0.0
    if video_path is None or not video_path.is_file():
        raise HTTPException(404, f'No camera video at {video_path}')

    target_frame = int(round(from_ts * fps_meta))
    cap = cv2.VideoCapture(str(video_path))
    try:
        # Two-step seek for frame accuracy: jump close, then walk forward.
        # OpenCV's POS_FRAMES set lands at the prior keyframe and decodes to
        # the requested frame for FFmpeg backends, but on some builds it can
        # under- or over-shoot by a few frames. We verify with the actual
        # decoded position and advance up to a small bounded number of frames
        # if we landed before the target. If we landed past the target (rare),
        # we accept it — re-seeking would amplify the error.
        if target_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(target_frame))
        ok, frame = cap.read()
        if not ok or frame is None:
            raise HTTPException(
                500, f'Could not decode frame {target_frame} of {video_path}')
        max_walk = 60  # ~2 s at 30 fps, hard cap on cost
        for _ in range(max_walk):
            actual = int(round(cap.get(cv2.CAP_PROP_POS_FRAMES))) - 1
            if actual >= target_frame:
                break
            ok, frm = cap.read()
            if not ok or frm is None:
                break
            frame = frm
    finally:
        cap.release()

    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise HTTPException(500, 'JPEG encode failed')
    entry = (bytes(buf), frame)
    with _reference_lock:
        _cache_put(_reference_cache, key, entry, REFERENCE_CACHE_MAX)
    return entry


def _load_thumbnail(dataset_id: str, camera_key: str,
                    episode_idx: int = 0, max_w: int = 320) -> bytes:
    cache_key = (dataset_id, camera_key, episode_idx)
    with _reference_lock:
        cached = _cache_get(_thumbnail_cache, cache_key)
    if cached is not None:
        return cached
    _, frame = _load_reference(dataset_id, camera_key, episode_idx)
    h, w = frame.shape[:2]
    if w > max_w:
        scale = max_w / w
        frame = cv2.resize(frame, (max_w, int(h * scale)),
                           interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok:
        raise HTTPException(500, 'thumbnail encode failed')
    jpg = bytes(buf)
    with _reference_lock:
        _cache_put(_thumbnail_cache, cache_key, jpg, THUMBNAIL_CACHE_MAX)
    return jpg


# ---------------------------------------------------------------------------
# Alignment score (lighting-invariant via gradient ZNCC)
# ---------------------------------------------------------------------------

_score_lock = threading.Lock()
_score_state = {
    'value': None,        # 0..1, higher = better aligned; None if low-texture
    'updated_at': 0.0,
    'history': [],        # list of (t_unix, value), capped
    'low_texture': False, # last sample was rejected for low texture
}
_SCORE_HISTORY_MAX = 600  # ~2 min @ 5 Hz


def _alignment_score(live: np.ndarray, ref: np.ndarray) -> Optional[float]:
    """Zero-mean NCC of gradient magnitudes — lighting-invariant in [0, 1].

    Returns ``None`` if either frame is too low-texture for the score to be
    meaningful (variance of gradient magnitudes near zero would otherwise
    yield 0/0 → 0, which would mislead an operator into thinking a
    perfectly-aligned blank wall is catastrophically misaligned).
    """
    if ref.shape[:2] != live.shape[:2]:
        ref = cv2.resize(ref, (live.shape[1], live.shape[0]),
                         interpolation=cv2.INTER_AREA)
    L = cv2.cvtColor(live, cv2.COLOR_BGR2GRAY)
    R = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    L = cv2.GaussianBlur(L, (3, 3), 0)
    R = cv2.GaussianBlur(R, (3, 3), 0)
    gxL = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3)
    gyL = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    gxR = cv2.Sobel(R, cv2.CV_32F, 1, 0, ksize=3)
    gyR = cv2.Sobel(R, cv2.CV_32F, 0, 1, ksize=3)
    magL = cv2.magnitude(gxL, gyL)
    magR = cv2.magnitude(gxR, gyR)
    a = magL - float(magL.mean())
    b = magR - float(magR.mean())
    var_a = float((a * a).sum())
    var_b = float((b * b).sum())
    # Empirical low-texture floor: variance < 1e3 corresponds to a near-flat
    # gradient field where ZNCC is dominated by noise. Tested on 640×480 BGR.
    if var_a < 1e3 or var_b < 1e3:
        return None
    zncc = float((a * b).sum() / (np.sqrt(var_a * var_b) + 1e-9))
    return max(0.0, min(1.0, zncc))


def _record_score(value: Optional[float]) -> None:
    now = time.time()
    with _score_lock:
        _score_state['value'] = value
        _score_state['updated_at'] = now
        if value is not None:
            hist = _score_state['history']
            hist.append((now, value))
            if len(hist) > _SCORE_HISTORY_MAX:
                del hist[: len(hist) - _SCORE_HISTORY_MAX]


def _reset_score_history() -> None:
    with _score_lock:
        _score_state['value'] = None
        _score_state['history'] = []
        _score_state['low_texture'] = False


# ---------------------------------------------------------------------------
# Blend state (server-side compositing)
# ---------------------------------------------------------------------------

_state_lock = threading.Lock()
_state = {
    'dataset': '',
    'camera': '',
    'episode': 0,
    'ref_op': 0.5,
    'live_op': 0.5,
    'invert_ref': False,
    'invert_live': False,
}


def _composite(live: np.ndarray, ref: Optional[np.ndarray],
               ref_op: float, live_op: float,
               invert_ref: bool, invert_live: bool) -> np.ndarray:
    """True linear blend: out = ref_op*R + live_op*L, optional inversion per layer.

    Page-background contamination that plagues CSS opacity stacking is gone
    because the only contributors are R and L, weighted exactly as labeled.
    """
    L = (255 - live).astype(np.float32) if invert_live else live.astype(np.float32)
    if ref is None:
        out = live_op * L
    else:
        if ref.shape[:2] != live.shape[:2]:
            ref = cv2.resize(ref, (live.shape[1], live.shape[0]),
                             interpolation=cv2.INTER_AREA)
        R = (255 - ref).astype(np.float32) if invert_ref else ref.astype(np.float32)
        out = ref_op * R + live_op * L
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# MJPEG streaming
# ---------------------------------------------------------------------------

_PLACEHOLDER: bytes = b''


def _placeholder_jpeg() -> bytes:
    global _PLACEHOLDER
    if _PLACEHOLDER:
        return _PLACEHOLDER
    img = np.full((360, 640, 3), 32, dtype=np.uint8)
    cv2.putText(img, 'Waiting for camera...', (60, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2,
                cv2.LINE_AA)
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    _PLACEHOLDER = bytes(buf) if ok else b''
    return _PLACEHOLDER


def _mjpeg_generator():
    boundary = b'--frame'
    period = 1.0 / STREAM_FPS if STREAM_FPS > 0 else 0
    next_t = time.monotonic()
    last_score_t = 0.0
    SCORE_PERIOD = 0.2  # seconds, ~5 Hz
    while True:
        with _frame_lock:
            live = None if _latest_frame is None else _latest_frame.copy()
        with _state_lock:
            st = dict(_state)

        if live is None:
            jpg = _placeholder_jpeg()
        else:
            ref_arr = None
            if st['dataset'] and st['camera']:
                try:
                    _, ref_arr = _load_reference(
                        st['dataset'], st['camera'], int(st.get('episode', 0)))
                except HTTPException:
                    ref_arr = None
            composed = _composite(live, ref_arr,
                                  st['ref_op'], st['live_op'],
                                  st['invert_ref'], st['invert_live'])
            now_m = time.monotonic()
            if ref_arr is not None and (now_m - last_score_t) >= SCORE_PERIOD:
                last_score_t = now_m
                try:
                    sv = _alignment_score(live, ref_arr)
                    _record_score(sv)
                    with _score_lock:
                        _score_state['low_texture'] = sv is None
                except Exception:
                    pass
            ok, buf = cv2.imencode('.jpg', composed,
                                   [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            jpg = bytes(buf) if ok else None

        if jpg is not None:
            chunk = (boundary + b'\r\n'
                     b'Content-Type: image/jpeg\r\n'
                     b'Content-Length: ' + str(len(jpg)).encode() + b'\r\n\r\n'
                     + jpg + b'\r\n')
            yield chunk

        next_t += period
        sleep = next_t - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            next_t = time.monotonic()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    t = threading.Thread(target=_ros_thread, name='rclpy-spin', daemon=True)
    t.start()
    yield
    if rclpy.ok():
        rclpy.shutdown()


app = FastAPI(title='Scene Aligner', lifespan=_lifespan)

_STATIC_DIR = Path(__file__).parent / 'static'
app.mount('/static', StaticFiles(directory=str(_STATIC_DIR)), name='static')


# Strict CSP: scripts and styles only from same origin (no inline).
@app.middleware('http')
async def _security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "script-src 'self'; "
        "style-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('Referrer-Policy', 'no-referrer')
    return resp


@app.get('/')
def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / 'aligner.html'),
                        media_type='text/html; charset=utf-8')


@app.get('/api/datasets')
def api_datasets() -> dict:
    return {'datasets': _list_datasets()}


@app.get('/api/dataset/{dataset_id:path}/info')
def api_dataset_info(dataset_id: str, camera: Optional[str] = None) -> dict:
    ds_dir = _safe_dataset_dir(dataset_id)
    info = _read_info(dataset_id)
    keys = ['codebase_version', 'robot_type', 'total_episodes',
            'total_frames', 'total_tasks', 'fps',
            'data_files_size_in_mb', 'video_files_size_in_mb', 'splits']
    summary = {k: info.get(k) for k in keys}
    cams = _list_cameras(ds_dir, dataset_id)
    summary['cameras'] = cams
    cam = camera if camera in cams else (cams[0] if cams else None)
    summary['camera'] = cam
    if cam:
        feat = info.get('features', {}).get(cam, {})
        summary['camera_video'] = {
            'shape': feat.get('shape'),
            'codec': feat.get('info', {}).get('video.codec'),
            'fps': feat.get('info', {}).get('video.fps'),
        }
    summary['acquired_at'] = _acquired_at(dataset_id, ds_dir)
    summary['has_video'] = bool(cams)
    return summary


@app.get('/api/dataset/{dataset_id:path}/raw')
def api_dataset_raw(dataset_id: str) -> dict:
    """Full info.json for the details pane."""
    _safe_dataset_dir(dataset_id)
    return _read_info(dataset_id)


@app.get('/api/dataset/{dataset_id:path}/thumbnail')
def api_dataset_thumbnail(dataset_id: str, camera: Optional[str] = None) -> Response:
    ds_dir = _safe_dataset_dir(dataset_id)
    cam = _resolve_camera(ds_dir, dataset_id, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset_id}')
    return Response(content=_load_thumbnail(dataset_id, cam),
                    media_type='image/jpeg',
                    headers={'Cache-Control': 'public, max-age=3600'})


@app.get('/api/dataset/{dataset_id:path}/video')
def api_dataset_video(dataset_id: str, request: Request,
                      camera: Optional[str] = None) -> Response:
    base = _safe_dataset_dir(dataset_id)
    cam = _resolve_camera(base, dataset_id, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset_id}')
    path = _camera_video_path(base, cam)
    if not path.is_file():
        raise HTTPException(404, f'No camera video at {path}')

    file_size = path.stat().st_size
    range_header = request.headers.get('range')
    if range_header and range_header.startswith('bytes='):
        try:
            start_s, end_s = range_header[6:].split('-', 1)
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
        except ValueError:
            raise HTTPException(416, 'Bad Range header')
        end = min(end, file_size - 1)
        if start > end:
            raise HTTPException(416, 'Bad Range header')
        length = end - start + 1

        def _iter():
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Cache-Control': 'public, max-age=3600',
        }
        return StreamingResponse(_iter(), status_code=206,
                                 media_type='video/mp4', headers=headers)

    return FileResponse(str(path), media_type='video/mp4',
                        headers={'Accept-Ranges': 'bytes',
                                 'Cache-Control': 'public, max-age=3600'})


@app.get('/api/episodes')
def api_episodes(dataset: str = Query(..., min_length=1)) -> dict:
    ds_dir = _safe_dataset_dir(dataset)
    fps = float(_read_info(dataset).get('fps') or 30.0)
    eps = load_episodes(ds_dir, dataset, fps=fps)
    labels_by_idx = _episode_labels_map(dataset)
    labels_meta = _read_labels(dataset)
    if labels_by_idx:
        eps = [{**ep, 'labels': labels_by_idx.get(ep['idx'], [])} for ep in eps]
    else:
        eps = [{**ep, 'labels': []} for ep in eps]
    return {
        'fps': fps,
        'episodes': eps,
        'available_labels': labels_meta.get('available_labels', []),
    }


@app.get('/api/labels')
def api_labels(dataset: str = Query(..., min_length=1)) -> dict:
    _safe_dataset_dir(dataset)
    return _read_labels(dataset)


@app.get('/api/episode/info')
def api_episode_info(dataset: str = Query(..., min_length=1),
                     episode: int = Query(...)) -> dict:
    ds_dir = _safe_dataset_dir(dataset)
    fps = float(_read_info(dataset).get('fps') or 30.0)
    ep = find_episode(ds_dir, dataset, episode, fps=fps)
    if ep is None:
        raise HTTPException(404, f'No such episode: {episode}')
    return ep


@app.get('/api/episode/thumbnail')
def api_episode_thumbnail(dataset: str = Query(..., min_length=1),
                          episode: int = Query(...),
                          camera: Optional[str] = None) -> Response:
    ds_dir = _safe_dataset_dir(dataset)
    cam = _resolve_camera(ds_dir, dataset, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset}')
    return Response(content=_load_thumbnail(dataset, cam, episode),
                    media_type='image/jpeg',
                    headers={'Cache-Control': 'public, max-age=3600'})


@app.get('/api/episode/reference')
def api_episode_reference(dataset: str = Query(..., min_length=1),
                          episode: int = Query(...),
                          camera: Optional[str] = None) -> Response:
    ds_dir = _safe_dataset_dir(dataset)
    cam = _resolve_camera(ds_dir, dataset, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset}')
    jpg, _ = _load_reference(dataset, cam, episode)
    return Response(content=jpg, media_type='image/jpeg',
                    headers={'Cache-Control': 'public, max-age=3600'})


@app.get('/api/episode/video')
def api_episode_video(request: Request,
                      dataset: str = Query(..., min_length=1),
                      episode: int = Query(...),
                      camera: Optional[str] = None) -> Response:
    """Serve the chunk MP4 containing this episode (browser seeks via from_ts)."""
    ds_dir = _safe_dataset_dir(dataset)
    cam = _resolve_camera(ds_dir, dataset, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset}')
    fps = float(_read_info(dataset).get('fps') or 30.0)
    ep = find_episode(ds_dir, dataset, episode, fps=fps)
    if ep is None:
        raise HTTPException(404, f'No such episode: {episode}')
    path = episode_video_path(ds_dir, cam, ep)
    if path is None or not path.is_file():
        raise HTTPException(404, f'No camera video at {path}')
    cam_meta = ep['cameras'].get(cam, {})
    extra_headers = {
        'X-Episode-From-Ts': f'{cam_meta.get("from_timestamp", 0.0):.6f}',
        'X-Episode-To-Ts':   f'{cam_meta.get("to_timestamp", 0.0):.6f}',
    }

    file_size = path.stat().st_size
    range_header = request.headers.get('range')
    if range_header and range_header.startswith('bytes='):
        try:
            start_s, end_s = range_header[6:].split('-', 1)
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
        except ValueError:
            raise HTTPException(416, 'Bad Range header')
        end = min(end, file_size - 1)
        if start > end:
            raise HTTPException(416, 'Bad Range header')
        length = end - start + 1

        def _iter():
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Cache-Control': 'public, max-age=3600',
            **extra_headers,
        }
        return StreamingResponse(_iter(), status_code=206,
                                 media_type='video/mp4', headers=headers)

    return FileResponse(str(path), media_type='video/mp4',
                        headers={'Accept-Ranges': 'bytes',
                                 'Cache-Control': 'public, max-age=3600',
                                 **extra_headers})


@app.get('/api/reference')
def api_reference(dataset: str = Query(..., min_length=1),
                  camera: Optional[str] = None) -> Response:
    ds_dir = _safe_dataset_dir(dataset)
    cam = _resolve_camera(ds_dir, dataset, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset}')
    jpg, _ = _load_reference(dataset, cam)
    return Response(content=jpg, media_type='image/jpeg',
                    headers={'Cache-Control': 'public, max-age=3600'})


def _apply_active_topic() -> None:
    """Re-subscribe ROS to the topic implied by current camera state.

    Safe to call from any thread: enqueues the request; the ROS executor
    applies it on its own timer callback.
    """
    global _pending_initial_topic
    cam = _state.get('camera') or ''
    topic = _topic_for_camera(cam) if cam else ''
    if _camera_node is None:
        _pending_initial_topic = topic
        return
    _camera_node.request_topic(topic)


class _StatePayload(BaseModel):
    dataset:     Optional[str]   = None
    camera:      Optional[str]   = None
    episode:     Optional[int]   = Field(default=None, ge=0)
    ref_op:      Optional[float] = Field(default=None, ge=0.0, le=1.0)
    live_op:     Optional[float] = Field(default=None, ge=0.0, le=1.0)
    invert_ref:  Optional[bool]  = None
    invert_live: Optional[bool]  = None

    @field_validator('dataset')
    @classmethod
    def _validate_dataset(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == '':
            return v
        # Block obvious traversal here; full check happens via _safe_dataset_dir.
        if '..' in v.split('/') or v.startswith('/'):
            raise ValueError('invalid dataset path')
        return v

    @field_validator('camera')
    @classmethod
    def _validate_camera(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == '':
            return v
        if any(c in v for c in ('/', '\\', '\x00', '\n', '\r')):
            raise ValueError('invalid camera key')
        return v


@app.post('/api/state')
def api_state_set(payload: _StatePayload) -> dict:
    selection_changed = False
    with _state_lock:
        if payload.dataset is not None:
            if payload.dataset != _state['dataset']:
                selection_changed = True
            _state['dataset'] = payload.dataset
        if payload.camera is not None:
            if payload.camera != _state['camera']:
                selection_changed = True
            _state['camera'] = payload.camera
        if payload.episode is not None:
            if payload.episode != _state['episode']:
                selection_changed = True
            _state['episode'] = payload.episode
        if payload.ref_op is not None:
            _state['ref_op'] = float(payload.ref_op)
        if payload.live_op is not None:
            _state['live_op'] = float(payload.live_op)
        if payload.invert_ref is not None:
            _state['invert_ref'] = bool(payload.invert_ref)
        if payload.invert_live is not None:
            _state['invert_live'] = bool(payload.invert_live)
        out = dict(_state)
    if selection_changed:
        _reset_score_history()
    _apply_active_topic()
    out['active_topic'] = _topic_for_camera(out['camera']) if out['camera'] else ''
    return out


@app.get('/api/state')
def api_state_get() -> dict:
    with _state_lock:
        out = dict(_state)
    out['active_topic'] = _topic_for_camera(out['camera']) if out['camera'] else ''
    out['default_camera'] = DEFAULT_CAMERA_KEY
    return out


@app.get('/api/score')
def api_score(since: float = 0.0) -> dict:
    """Return latest alignment score plus history points after `since` (unix s)."""
    with _score_lock:
        hist = [(t, v) for t, v in _score_state['history'] if t > since]
        return {
            'value': _score_state['value'],
            'updated_at': _score_state['updated_at'],
            'history': hist,
            'low_texture': _score_state.get('low_texture', False),
        }


@app.get('/stream.mjpg')
def stream() -> StreamingResponse:
    return StreamingResponse(
        _mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame',
        headers={'Cache-Control': 'no-store'},
    )


