#!/usr/bin/env python3
"""Scene alignment webapp.

Serves a single-page UI that overlays the live ROS 2 camera feed (MJPEG) on
top of the first frame of the chosen dataset and camera. Operators use it to
reset a physical scene to match a recorded starting pose before capturing new
demonstrations.
"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Optional

import av
import cv2
import numpy as np
import rclpy
import rclpy.logging
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image

from .episodes import (
    episode_video_path,
    find_episode,
    load_episodes,
)

DATASETS_DIR = Path(os.environ.get('DATASETS_DIR', '/data/sample_datasets'))
DEFAULT_CAMERA_KEY = os.environ.get('DEFAULT_CAMERA_KEY', '')
STREAM_FPS = float(os.environ.get('STREAM_FPS', '15'))
JPEG_QUALITY = int(os.environ.get('JPEG_QUALITY', '70'))
# Maximum number of cached references and thumbnails. References hold both
# JPEG bytes and a full BGR ndarray (~900 KB at 640×480) so the cap matters.
REFERENCE_CACHE_MAX = int(os.environ.get('REFERENCE_CACHE_MAX', '64'))
THUMBNAIL_CACHE_MAX = int(os.environ.get('THUMBNAIL_CACHE_MAX', '512'))
# How long a topic probe is allowed to wait for a message before being declared
# silent. Keep generous: low-rate publishers may take >1s between messages.
TOPIC_PROBE_TIMEOUT_S = float(os.environ.get('TOPIC_PROBE_TIMEOUT_S', '3.0'))
# Cache TTL for successful probe results. Re-probing flushes stale encoding
# information if the publisher has been reconfigured.
TOPIC_PROBE_TTL_S = float(os.environ.get('TOPIC_PROBE_TTL_S', '300.0'))
# Encodings the current decoder can render (kept in sync with
# CameraSubscriber._decode below).
DISPLAYABLE_ENCODINGS = frozenset({
    'bgr8', 'rgb8', 'bgra8', 'rgba8', 'mono8', '8uc1',
})


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
        self._first_msg_logged = False
        self._msg_count = 0
        self._last_log_t = 0.0
        self._pending: queue.Queue[str] = queue.Queue()
        # Live-status counters consulted by /api/live_status. Updated only
        # from the rclpy executor thread; reads are cheap so no lock needed
        # to publish them — they're snapshotted under self._status_lock.
        self._status_lock = threading.Lock()
        self._last_msg_at: Optional[float] = None
        self._last_decode_error: Optional[dict] = None
        self._last_publisher_count: Optional[int] = None
        self._last_frame_info: Optional[dict] = None

        # ------------------------------------------------------------------
        # Probe state. Probes run on the rclpy executor; the FastAPI side
        # only enqueues requests and reads the cache.
        # ------------------------------------------------------------------
        self._probe_lock = threading.Lock()
        self._probe_cache: dict[str, dict] = {}
        self._probe_requests: queue.Queue[str] = queue.Queue()
        self._probe_in_flight: dict[str, dict] = {}

        # Drain pending topic changes on the ROS executor thread.
        self.create_timer(0.05, self._apply_pending)
        self.create_timer(0.1, self._tick_probes)

    # ------------------------------------------------------------------
    # Live status (read by /api/live_status)
    # ------------------------------------------------------------------

    def get_live_status(self) -> dict:
        with self._status_lock:
            return {
                'topic': self._topic,
                'subscribed': self._sub is not None,
                'msg_count': self._msg_count,
                'last_msg_at': self._last_msg_at,
                'last_publisher_count': self._last_publisher_count,
                'last_decode_error': dict(self._last_decode_error) if self._last_decode_error else None,
                'last_frame_info': dict(self._last_frame_info) if self._last_frame_info else None,
            }

    # ------------------------------------------------------------------
    # Topic probes (read by /api/topics)
    # ------------------------------------------------------------------

    def get_probe(self, topic: str) -> Optional[dict]:
        with self._probe_lock:
            entry = self._probe_cache.get(topic)
            return dict(entry) if entry else None

    def get_probes(self) -> dict[str, dict]:
        with self._probe_lock:
            return {k: dict(v) for k, v in self._probe_cache.items()}

    def request_probe(self, topic: str) -> None:
        """Queue ``topic`` for probing. Idempotent — no-op while in flight
        or while a fresh cache entry exists."""
        if not topic:
            return
        now = time.time()
        with self._probe_lock:
            entry = self._probe_cache.get(topic)
            if entry and (now - entry.get('ts', 0)) < TOPIC_PROBE_TTL_S:
                return
            if topic in self._probe_in_flight:
                return
        self._probe_requests.put(topic)

    def _record_probe(
        self,
        topic: str,
        *,
        encoding: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        step: Optional[int] = None,
        publisher_count: Optional[int] = None,
        displayable: Optional[bool] = None,
        error: Optional[str] = None,
    ) -> None:
        with self._probe_lock:
            self._probe_cache[topic] = {
                'topic': topic,
                'ts': time.time(),
                'encoding': encoding,
                'width': width,
                'height': height,
                'step': step,
                'publisher_count': publisher_count,
                'displayable': displayable,
                'error': error,
            }

    def _tick_probes(self) -> None:
        """rclpy-thread timer: start queued probes, time out in-flight ones."""
        # Start new probes (cap concurrency).
        while len(self._probe_in_flight) < 8:
            try:
                topic = self._probe_requests.get_nowait()
            except queue.Empty:
                break
            if topic in self._probe_in_flight or topic == self._topic:
                continue
            try:
                pubs = self.get_publishers_info_by_topic(topic)
            except Exception as exc:  # noqa: BLE001
                _record_issue(
                    'warning', 'topic_probe',
                    f'discovery query failed for {topic}: {exc}',
                    key=f'probe-discovery:{topic}',
                    topic=topic)
                self._record_probe(topic, publisher_count=0, displayable=False,
                                   error=f'discovery failed: {exc}')
                continue
            if not pubs:
                self._record_probe(topic, publisher_count=0, displayable=False,
                                   error='no publisher')
                continue
            try:
                sub = self.create_subscription(
                    Image, topic,
                    lambda msg, t=topic: self._on_probe_message(t, msg),
                    self._qos)
            except Exception as exc:  # noqa: BLE001
                _record_issue(
                    'warning', 'topic_probe',
                    f'subscribe failed for {topic}: {exc}',
                    key=f'probe-subscribe:{topic}',
                    topic=topic)
                self._record_probe(topic, publisher_count=len(pubs),
                                   displayable=False, error=f'subscribe failed: {exc}')
                continue
            self._probe_in_flight[topic] = {
                'sub': sub,
                'deadline': time.monotonic() + TOPIC_PROBE_TIMEOUT_S,
                'publisher_count': len(pubs),
            }

        # Time out in-flight probes that never got a message.
        if self._probe_in_flight:
            now = time.monotonic()
            expired = [t for t, info in self._probe_in_flight.items() if now >= info['deadline']]
            for topic in expired:
                info = self._probe_in_flight.pop(topic)
                self.destroy_subscription(info['sub'])
                self._record_probe(
                    topic,
                    publisher_count=info['publisher_count'],
                    displayable=False,
                    error=f'no message within {TOPIC_PROBE_TIMEOUT_S:.1f}s')
                _record_issue(
                    'info', 'topic_probe',
                    f'no message on {topic} within {TOPIC_PROBE_TIMEOUT_S:.1f}s '
                    f'(publishers={info["publisher_count"]})',
                    key=f'probe-timeout:{topic}',
                    topic=topic)

    def _on_probe_message(self, topic: str, msg: Image) -> None:
        info = self._probe_in_flight.pop(topic, None)
        if info is not None:
            try:
                self.destroy_subscription(info['sub'])
            except Exception:  # noqa: BLE001
                pass
        enc = (msg.encoding or '').lower() or None
        displayable = bool(enc and enc in DISPLAYABLE_ENCODINGS)
        self._record_probe(
            topic,
            encoding=enc,
            width=int(msg.width),
            height=int(msg.height),
            step=int(msg.step),
            publisher_count=(info or {}).get('publisher_count'),
            displayable=displayable,
            error=None if displayable else f'encoding {enc!r} not displayable',
        )
        if not displayable:
            _record_issue(
                'info', 'topic_probe',
                f'{topic} carries non-displayable encoding {enc!r} '
                f'({msg.width}x{msg.height}); will be greyed out in the picker',
                key=f'probe-undisplayable:{topic}',
                topic=topic)

    # ------------------------------------------------------------------
    # Topic subscription change
    # ------------------------------------------------------------------

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
            self.get_logger().info(
                f'Unsubscribing from {self._topic} (received {self._msg_count} message(s))')
            self.destroy_subscription(self._sub)
            self._sub = None
        self._topic = latest
        self._first_msg_logged = False
        self._msg_count = 0
        with self._status_lock:
            self._last_msg_at = None
            self._last_decode_error = None
            self._last_publisher_count = None
            self._last_frame_info = None
        if latest:
            try:
                self._sub = self.create_subscription(
                    Image, latest, self._on_image, self._qos)
            except Exception as exc:  # noqa: BLE001
                self._sub = None
                _record_issue(
                    'error', 'ros_subscribe',
                    f'failed to subscribe to {latest}: {exc}',
                    key=f'subscribe:{latest}',
                    topic=latest)
                return
            self.get_logger().info(
                f'Subscribed to {latest} (QoS: BEST_EFFORT, KEEP_LAST depth=2)')
            # Diagnose discovery: list publishers and their QoS for this topic.
            try:
                pubs = self.get_publishers_info_by_topic(latest)
                with self._status_lock:
                    self._last_publisher_count = len(pubs)
                if not pubs:
                    _record_issue(
                        'warning', 'ros_subscribe',
                        f'No publishers currently advertise {latest}. '
                        f'Check topic name spelling, ROS_DOMAIN_ID, and DDS discovery.',
                        key=f'no-publisher:{latest}',
                        topic=latest)
                for p in pubs:
                    qos = p.qos_profile
                    self.get_logger().info(
                        f'  publisher node="{p.node_namespace}/{p.node_name}" '
                        f'type={p.topic_type} '
                        f'reliability={qos.reliability.name} '
                        f'durability={qos.durability.name} '
                        f'history={qos.history.name} depth={qos.depth}')
            except Exception as exc:  # noqa: BLE001
                _record_issue(
                    'warning', 'ros_subscribe',
                    f'discovery query failed for {latest}: {exc}',
                    key=f'discovery:{latest}',
                    topic=latest)
            global _latest_frame
            with _frame_lock:
                _latest_frame = None  # invalidate previous camera's frame
        else:
            self.get_logger().info('Topic cleared; live feed will show placeholder.')

    @staticmethod
    def _decode(msg: Image) -> tuple[Optional[np.ndarray], Optional[str]]:
        """Decode ``msg`` to BGR. Returns ``(array, reason_if_failed)``."""
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
                return None, f'unsupported encoding {enc!r}'
            row_pixels = step // channels if step else w
            if row_pixels < w:
                return None, (
                    f'step={step} too small for width={w} channels={channels} '
                    f'(expected step >= {w * channels})')
            view = buf.reshape(h, row_pixels * channels) if step else buf.reshape(h, w * channels)
            view = view[:, : w * channels]  # drop row padding
            if channels == 1:
                gray = view.reshape(h, w)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), None
            arr = view.reshape(h, w, channels)
            if enc == 'bgr8':
                return arr.copy(), None  # detach from msg.data
            if enc == 'rgb8':
                return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), None
            if enc == 'bgra8':
                return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR), None
            if enc == 'rgba8':
                return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR), None
        except (ValueError, cv2.error) as exc:
            return None, f'reshape/convert error: {exc}'
        return None, 'unreachable decode branch'

    def _on_image(self, msg: Image) -> None:
        global _latest_frame, _frame_seq
        self._msg_count += 1
        frame, reason = self._decode(msg)
        if frame is None:
            err = {
                'reason': reason,
                'encoding': msg.encoding,
                'width': int(msg.width),
                'height': int(msg.height),
                'step': int(msg.step),
                'ts': time.time(),
            }
            with self._status_lock:
                self._last_decode_error = err
            # Update probe cache so the dropdown disables this topic from
            # now on (a live decode failure is authoritative).
            self._record_probe(
                self._topic,
                encoding=(msg.encoding or '').lower() or None,
                width=int(msg.width),
                height=int(msg.height),
                step=int(msg.step),
                publisher_count=self._last_publisher_count,
                displayable=False,
                error=f'decode failed: {reason}',
            )
            _record_issue(
                'warning', 'ros_decode',
                f'[{self._topic}] decode failed: {reason}; '
                f'enc={msg.encoding} {msg.width}x{msg.height} step={msg.step} '
                f'data_len={len(msg.data)}',
                key=f'decode:{self._topic}:{reason}',
                topic=self._topic)
            return
        info = {
            'width': int(msg.width),
            'height': int(msg.height),
            'encoding': msg.encoding,
            'step': int(msg.step),
            'frame_id': msg.header.frame_id,
        }
        if not self._first_msg_logged:
            self._first_msg_logged = True
            _LOGGER.info(
                '[%s] first frame received: %dx%d encoding=%s step=%d frame_id=%r',
                self._topic, msg.width, msg.height, msg.encoding,
                msg.step, msg.header.frame_id)
        else:
            now = time.monotonic()
            if now - self._last_log_t >= 5.0:
                self._last_log_t = now
                _LOGGER.info(
                    '[%s] still receiving: msg #%d %dx%d enc=%s',
                    self._topic, self._msg_count, msg.width, msg.height, msg.encoding)
        with self._status_lock:
            self._last_msg_at = time.time()
            self._last_decode_error = None
            self._last_frame_info = info
        # A live frame proves the topic is displayable; refresh the probe
        # cache so the picker reflects current reality.
        enc = (msg.encoding or '').lower() or None
        self._record_probe(
            self._topic,
            encoding=enc,
            width=int(msg.width),
            height=int(msg.height),
            step=int(msg.step),
            publisher_count=self._last_publisher_count,
            displayable=bool(enc and enc in DISPLAYABLE_ENCODINGS),
            error=None,
        )
        with _frame_lock:
            _latest_frame = frame
            _frame_seq += 1

    def list_topics(self) -> list[tuple[str, list[str]]]:
        """Return all available ROS 2 topics and their message types."""
        return self.get_topic_names_and_types()


import logging

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get('SCENE_ALIGNER_LOG_LEVEL', 'INFO'),
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)


# ---------------------------------------------------------------------------
# Issue journal: every error/warning that the user might care about is
# recorded here so the UI can render it as a toast. The journal also logs
# the event at the matching Python log level (INFO minimum), so the same
# event lands in stderr too — operators see it whether they look at the
# console or the browser.
# ---------------------------------------------------------------------------

_ISSUES_MAX = 500
_ISSUES_LOCK = threading.Lock()
_ISSUES: 'deque[dict]' = deque(maxlen=_ISSUES_MAX)
_ISSUES_SEQ = 0
# (level, source, key) -> last_emit_monotonic. Used to throttle bursts of
# identical events (e.g. a decode failure that fires at the camera fps).
_ISSUES_THROTTLE: dict[tuple[str, str, str], float] = {}
_ISSUES_THROTTLE_S = 5.0


def _record_issue(
    level: str,
    source: str,
    message: str,
    *,
    key: Optional[str] = None,
    topic: Optional[str] = None,
    extra: Optional[dict] = None,
    throttle_s: float = _ISSUES_THROTTLE_S,
) -> None:
    """Record an operator-visible event.

    Always logs at the matching Python log level (lifted to INFO minimum so
    the user sees it without enabling DEBUG) and pushes onto the in-memory
    journal that ``/api/issues`` exposes to the UI.

    ``topic`` lets the UI dismiss toasts that became stale when the user
    switched to a different ROS topic. ``key`` (default = source + message)
    governs throttling so that a repeating event doesn't fill the journal.
    The throttled occurrences are still counted on the last surfaced entry.
    """
    global _ISSUES_SEQ
    level = level.lower()
    log_level = {
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }.get(level, logging.INFO)
    # Lift below-INFO events to INFO so the user requirement
    # "errors logged at INFO minimum" holds.
    log_level = max(log_level, logging.INFO)
    _LOGGER.log(log_level, '[%s] %s', source, message)

    throttle_key = (level, source, key or message)
    now = time.monotonic()
    with _ISSUES_LOCK:
        last = _ISSUES_THROTTLE.get(throttle_key, 0.0)
        if last and (now - last) < throttle_s and _ISSUES:
            # Bump the count on the most recent matching entry instead of
            # appending a fresh one.
            for entry in reversed(_ISSUES):
                if (entry['level'] == level
                        and entry['source'] == source
                        and entry.get('key') == (key or message)):
                    entry['count'] = entry.get('count', 1) + 1
                    entry['last_ts'] = time.time()
                    return
        _ISSUES_THROTTLE[throttle_key] = now
        _ISSUES_SEQ += 1
        entry = {
            'seq': _ISSUES_SEQ,
            'ts': time.time(),
            'last_ts': time.time(),
            'level': level,
            'source': source,
            'message': message,
            'key': key or message,
            'topic': topic or '',
            'count': 1,
        }
        if extra:
            entry['extra'] = extra
        _ISSUES.append(entry)


def _issues_since(since: int = 0, limit: int = 100) -> tuple[int, list[dict]]:
    """Return ``(latest_seq, entries)`` with ``seq > since``."""
    with _ISSUES_LOCK:
        latest = _ISSUES_SEQ
        out = [dict(e) for e in _ISSUES if e['seq'] > since]
    return latest, out[-limit:]


# ---------------------------------------------------------------------------
# Topic probe registry: opens a short-lived Subscription on every observed
# ``sensor_msgs/Image`` topic to read its real encoding + dimensions. This
# is the only reliable filter — topic names lie ("/color" can be 16UC1) and
# QoS alone doesn't tell you what the decoder will do with the bytes.
#
# Lives inside CameraSubscriber so all rclpy state stays single-threaded.
# ---------------------------------------------------------------------------

_camera_node: Optional['CameraSubscriber'] = None
_pending_topics: 'queue.Queue[str]' = queue.Queue()



def _ros_thread() -> None:
    global _camera_node
    rclpy.init()
    node = CameraSubscriber()
    _camera_node = node
    # Mirror SCENE_ALIGNER_LOG_LEVEL onto the rclpy logger so the node's
    # info/debug calls actually appear. rclpy maintains its own severity
    # filter independent of Python's logging module.
    level_name = os.environ.get('SCENE_ALIGNER_LOG_LEVEL', 'INFO').upper()
    try:
        ros_level = getattr(rclpy.logging.LoggingSeverity, level_name)
        rclpy.logging.set_logger_level(node.get_logger().name, ros_level)
    except AttributeError:
        _LOGGER.warning('Unknown SCENE_ALIGNER_LOG_LEVEL=%s; rclpy stays at INFO', level_name)
    _LOGGER.info('ROS subscriber initialised (log level=%s)', level_name)

    # Enumerate all available topics at startup
    topics = node.list_topics()
    _LOGGER.info('Available ROS 2 topics (%d):', len(topics))
    for topic_name, topic_types in sorted(topics):
        _LOGGER.info('  %s: %s', topic_name, ', '.join(topic_types))
    
    # Drain any topic requests queued before the node existed.
    try:
        while True:
            node.request_topic(_pending_topics.get_nowait())
    except queue.Empty:
        pass
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
        _record_issue(
            'warning', 'dataset_io',
            f'DATASETS_DIR does not exist: {DATASETS_DIR}',
            key='datasets-dir-missing')
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
    _LOGGER.info('Discovered %d dataset(s) under %s', len(out), DATASETS_DIR)
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
    except Exception as exc:  # noqa: BLE001
        _record_issue(
            'error', 'dataset_io',
            f'failed to parse {info_path}: {exc}',
            key=f'info-parse:{dataset_id}')
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
    except Exception as exc:  # noqa: BLE001
        _record_issue(
            'warning', 'dataset_io',
            f'failed to parse {labels_path}: {exc}',
            key=f'labels-parse:{dataset_id}')
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


def _decode_reference_frame(video_path: Path, target_frame: int, fps: float) -> np.ndarray:
    """Decode the BGR frame nearest ``target_frame`` from ``video_path``.

    Seeks to ~1 s before the target keyframe (FFmpeg native ``backward=True``)
    then walks the decoder until the first frame whose presentation
    timestamp meets or exceeds the target. ``to_ndarray`` is called only
    on the frame actually returned, so intermediate decodes do not pay
    the YUV→BGR conversion cost.
    """
    target_time = target_frame / fps if fps > 0 else 0.0
    seek_time = max(0.0, target_time - 1.0)
    try:
        with av.open(str(video_path)) as container:
            stream = next((s for s in container.streams.video if s.type == 'video'), None)
            if stream is None:
                raise HTTPException(500, f'No video stream in {video_path}')
            if seek_time > 0.0 and stream.time_base is not None:
                container.seek(int(seek_time / float(stream.time_base)),
                               stream=stream, backward=True)
            last: Optional[av.VideoFrame] = None
            for decoded in container.decode(stream):
                last = decoded
                if target_time <= 0.0 or decoded.time is None or decoded.time >= target_time:
                    return decoded.to_ndarray(format='bgr24')
            if last is not None:
                return last.to_ndarray(format='bgr24')
    except av.FFmpegError as exc:
        raise HTTPException(
            500, f'Could not decode frame {target_frame} of {video_path}') from exc
    raise HTTPException(500, f'Could not decode frame {target_frame} of {video_path}')


def _load_reference(dataset_id: str, camera_key: str,
                    episode_idx: int = 0,
                    which: str = 'first') -> tuple[bytes, np.ndarray]:
    """Decode a reference frame for ``(dataset, camera, episode, which)``.

    ``which`` is ``'first'`` (default — frame at ``from_timestamp``) or
    ``'last'`` (frame at ``from_timestamp + (length - 1) / fps``). Both
    cache safely: the key is ``(dataset_id, camera_key, episode_idx, which)``
    and each tuple maps to a single video file + frame index.
    """
    if which not in ('first', 'last'):
        raise HTTPException(400, f'invalid which={which!r}')
    key = (dataset_id, camera_key, episode_idx, which)
    with _reference_lock:
        cached = _cache_get(_reference_cache, key)
        if cached is not None:
            return cached

    ds_dir = _safe_dataset_dir(dataset_id)
    fps_meta = float(_read_info(dataset_id).get('fps') or 30.0)
    ep = find_episode(ds_dir, dataset_id, episode_idx, fps=fps_meta)
    length = 1
    if ep is not None:
        video_path = episode_video_path(ds_dir, camera_key, ep)
        from_ts = ep['cameras'].get(camera_key, {}).get('from_timestamp', 0.0)
        length = max(1, int(ep.get('length', 1) or 1))
    else:
        # Fallback: chunk-000/file-000, frame 0.
        video_path = _camera_video_path(ds_dir, camera_key)
        from_ts = 0.0
    if video_path is None or not video_path.is_file():
        raise HTTPException(404, f'No camera video at {video_path}')

    target_frame = int(round(from_ts * fps_meta))
    if which == 'last':
        target_frame += length - 1
    frame = _decode_reference_frame(video_path, target_frame, fps_meta)

    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise HTTPException(500, 'JPEG encode failed')
    entry = (bytes(buf), frame)
    with _reference_lock:
        _cache_put(_reference_cache, key, entry, REFERENCE_CACHE_MAX)
    _LOGGER.info('Decoded reference: %s ep=%d cam=%s which=%s frame=%d (%dx%d)',
                 dataset_id, episode_idx, camera_key, which, target_frame,
                 frame.shape[1], frame.shape[0])
    return entry


def _load_thumbnail(dataset_id: str, camera_key: str,
                    episode_idx: int = 0, max_w: int = 320,
                    which: str = 'first') -> bytes:
    cache_key = (dataset_id, camera_key, episode_idx, which)
    with _reference_lock:
        cached = _cache_get(_thumbnail_cache, cache_key)
    if cached is not None:
        return cached
    _, frame = _load_reference(dataset_id, camera_key, episode_idx, which=which)
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
    'topic': '',
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

_PLACEHOLDER_LOCK = threading.Lock()
_PLACEHOLDER_CACHE: dict[str, bytes] = {}


def _placeholder_jpeg(message: str = 'Waiting for camera...') -> bytes:
    with _PLACEHOLDER_LOCK:
        cached = _PLACEHOLDER_CACHE.get(message)
        if cached:
            return cached
        img = np.full((360, 640, 3), 32, dtype=np.uint8)
        # Word-wrap the message so long diagnostic strings don't run off the
        # edge. ~50 chars/line at the chosen font scale.
        lines: list[str] = []
        for paragraph in str(message).splitlines() or ['']:
            words = paragraph.split(' ')
            row = ''
            for w in words:
                candidate = (row + ' ' + w).strip()
                if len(candidate) <= 50:
                    row = candidate
                else:
                    if row:
                        lines.append(row)
                    row = w
            lines.append(row)
        font_scale = 0.6 if max((len(l) for l in lines), default=0) > 30 else 0.8
        line_h = 28
        y = max(40, 180 - (len(lines) - 1) * line_h // 2)
        for line in lines:
            cv2.putText(img, line, (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                        (210, 210, 210), 2, cv2.LINE_AA)
            y += line_h
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        jpg = bytes(buf) if ok else b''
        _PLACEHOLDER_CACHE[message] = jpg
        # Cap the cache to avoid unbounded growth from changing messages.
        if len(_PLACEHOLDER_CACHE) > 32:
            _PLACEHOLDER_CACHE.pop(next(iter(_PLACEHOLDER_CACHE)))
        return jpg


def _live_status_message(intended_topic: str = '') -> str:
    """Human-readable summary of why no live frame is available right now.

    ``intended_topic`` is the topic the *user* asked for (taken from
    ``_state['topic']``). It may briefly differ from the camera node's actual
    subscription because ``_apply_pending`` runs on a 50 ms timer; speaking
    to the intended topic avoids surfacing stale decode-errors from the
    previous subscription right after the user picks a new one.
    """
    if _camera_node is None:
        return 'ROS subscriber not yet ready'
    status = _camera_node.get_live_status()
    actual = status.get('topic') or ''
    intended = intended_topic or actual
    if not intended:
        return 'No ROS topic selected'
    # Subscription hasn't caught up with the user's last pick yet.
    if intended != actual:
        return f'Switching to {intended}…'
    if not status.get('subscribed'):
        return f'Not subscribed to {intended}'
    err = status.get('last_decode_error')
    if err:
        return (f'Decode failed on {intended}: '
                f'encoding {err.get("encoding")!r} '
                f'{err.get("width")}x{err.get("height")} — {err.get("reason")}')
    pubs = status.get('last_publisher_count')
    if pubs is not None and pubs == 0:
        return (f'No publishers on {intended} '
                f'(check ROS_DOMAIN_ID and DDS discovery)')
    return f'Waiting for first frame on {intended}…'


# Single shared composite is produced by a background thread so multiple
# MJPEG clients (e.g. the main view + the lens loupe) don't each pay the
# OpenCV blend + JPEG encode cost. Each generator just reads the latest
# encoded frame.
_composite_lock = threading.Lock()
_composite_jpeg: Optional[bytes] = None
_composite_seq = 0


def _composite_loop() -> None:
    """Background producer: latest live frame + state → JPEG, on a slot."""
    global _composite_jpeg, _composite_seq
    period = 1.0 / STREAM_FPS if STREAM_FPS > 0 else 0
    next_t = time.monotonic()
    last_score_t = 0.0
    last_no_frame_log = 0.0
    SCORE_PERIOD = 0.2  # seconds, ~5 Hz
    NO_FRAME_LOG_PERIOD = 5.0
    while True:
        with _frame_lock:
            live = None if _latest_frame is None else _latest_frame.copy()
        with _state_lock:
            st = dict(_state)

        if live is None:
            now_m = time.monotonic()
            if now_m - last_no_frame_log >= NO_FRAME_LOG_PERIOD:
                last_no_frame_log = now_m
                topic = st.get('topic') or '<none>'
                _LOGGER.info(
                    'No live frame available; serving placeholder. Selected topic=%s',
                    topic)
            jpg = _placeholder_jpeg(_live_status_message(st.get('topic') or ''))
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
                except Exception as exc:  # noqa: BLE001
                    _record_issue(
                        'error', 'score',
                        f'alignment score failed: {type(exc).__name__}: {exc}',
                        key='score-exception')
                    _LOGGER.exception('alignment score failed')
            ok, buf = cv2.imencode('.jpg', composed,
                                   [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            jpg = bytes(buf) if ok else None

        if jpg is not None:
            with _composite_lock:
                _composite_jpeg = jpg
                _composite_seq += 1

        next_t += period
        sleep = next_t - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            next_t = time.monotonic()


def _mjpeg_generator(client_addr: str = '?'):
    """Per-client MJPEG generator — reads the shared composite slot."""
    boundary = b'--frame'
    period = 1.0 / STREAM_FPS if STREAM_FPS > 0 else 0
    last_seen = -1
    next_t = time.monotonic()
    _LOGGER.info('MJPEG client connected: %s', client_addr)
    try:
        while True:
            with _composite_lock:
                seq = _composite_seq
                jpg = _composite_jpeg
            if jpg is not None and seq != last_seen:
                last_seen = seq
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
    except (GeneratorExit, BrokenPipeError, ConnectionError):
        pass
    finally:
        _LOGGER.info('MJPEG client disconnected: %s', client_addr)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    t_ros = threading.Thread(target=_ros_thread, name='rclpy-spin', daemon=True)
    t_ros.start()
    t_comp = threading.Thread(target=_composite_loop, name='composite', daemon=True)
    t_comp.start()
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
        # Allow JS-driven element.style.X assignments (slider widths, loupe
        # position, sparkline updates) while still blocking <style> blocks
        # and stylesheets from anywhere other than 'self'.
        "style-src-attr 'unsafe-inline'; "
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
                          camera: Optional[str] = None,
                          which: str = Query('first')) -> Response:
    if which not in ('first', 'last'):
        raise HTTPException(400, f'invalid which={which!r}')
    ds_dir = _safe_dataset_dir(dataset)
    cam = _resolve_camera(ds_dir, dataset, camera)
    if not cam:
        raise HTTPException(404, f'No video features in {dataset}')
    return Response(content=_load_thumbnail(dataset, cam, episode, which=which),
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
    """Re-subscribe ROS to the user-selected topic.

    Safe to call from any thread: enqueues the request; the ROS executor
    applies it on its own timer callback. If called before the ROS thread
    has constructed the node, the request is buffered in ``_pending_topics``
    and drained once the node exists.
    """
    with _state_lock:
        topic = _state.get('topic') or ''
    if _camera_node is None:
        _pending_topics.put(topic)
        return
    _camera_node.request_topic(topic)


class _StatePayload(BaseModel):
    dataset:     Optional[str]   = None
    camera:      Optional[str]   = None
    topic:       Optional[str]   = None
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

    @field_validator('topic')
    @classmethod
    def _validate_topic(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == '':
            return v
        if any(c in v for c in ('\x00', '\n', '\r', ' ')):
            raise ValueError('invalid topic name')
        return v


@app.post('/api/state')
def api_state_set(payload: _StatePayload) -> dict:
    selection_changed = False
    topic_changed = False
    with _state_lock:
        if payload.dataset is not None:
            if payload.dataset != _state['dataset']:
                selection_changed = True
            _state['dataset'] = payload.dataset
        if payload.camera is not None:
            if payload.camera != _state['camera']:
                selection_changed = True
            _state['camera'] = payload.camera
        if payload.topic is not None:
            if payload.topic != _state['topic']:
                topic_changed = True
            _state['topic'] = payload.topic
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
    if topic_changed:
        _apply_active_topic()
    return out


@app.get('/api/state')
def api_state_get() -> dict:
    with _state_lock:
        out = dict(_state)
    out['default_camera'] = DEFAULT_CAMERA_KEY
    return out


@app.get('/api/topics')
def api_topics() -> dict:
    """List all discovered ROS 2 topics with their message types.

    Image topics are enriched with the latest probe result so the UI can
    grey out non-displayable feeds (depth maps, exotic encodings) instead
    of relying on name heuristics. Probes are requested lazily here and
    fulfilled on the rclpy executor; the first call typically returns
    ``displayable: null`` for fresh entries while probes are in flight,
    and subsequent calls fill in.
    """
    if _camera_node is None:
        return {'topics': []}
    discovered = _camera_node.list_topics()
    probes_snapshot = _camera_node.get_probes()
    topics: list[dict] = []
    image_count = 0
    displayable_count = 0
    for name, types in discovered:
        types_list = list(types)
        is_image = 'sensor_msgs/msg/Image' in types_list
        entry: dict = {
            'name': name,
            'types': types_list,
            'is_image': is_image,
            'probe': None,
        }
        if is_image:
            image_count += 1
            probe = probes_snapshot.get(name)
            if probe is None or (time.time() - probe.get('ts', 0)) > TOPIC_PROBE_TTL_S:
                _camera_node.request_probe(name)
            entry['probe'] = probe
            if probe and probe.get('displayable'):
                displayable_count += 1
        topics.append(entry)
    topics.sort(key=lambda t: t['name'])
    _LOGGER.info(
        'Topic discovery: %d topic(s) visible (%d image, %d displayable)',
        len(topics), image_count, displayable_count)
    return {'topics': topics}


@app.get('/api/issues')
def api_issues(since: int = 0, limit: int = 100) -> dict:
    """Return journal entries with ``seq > since`` for UI toast rendering."""
    latest, entries = _issues_since(since=since, limit=limit)
    return {'seq': latest, 'issues': entries}


@app.get('/api/live_status')
def api_live_status() -> dict:
    """Snapshot of the currently-subscribed live feed for the status badge."""
    if _camera_node is None:
        return {
            'ready': False,
            'message': 'ROS subscriber not yet ready',
            'status': None,
        }
    status = _camera_node.get_live_status()
    with _state_lock:
        intended = _state.get('topic') or ''
    msg = _live_status_message(intended)
    has_frame = False
    with _frame_lock:
        has_frame = _latest_frame is not None
    return {
        'ready': True,
        'has_frame': has_frame,
        'message': msg,
        'intended_topic': intended,
        'status': status,
    }


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
def stream(request: Request) -> StreamingResponse:
    client = f'{request.client.host}:{request.client.port}' if request.client else '?'
    return StreamingResponse(
        _mjpeg_generator(client),
        media_type='multipart/x-mixed-replace; boundary=frame',
        headers={'Cache-Control': 'no-store'},
    )


