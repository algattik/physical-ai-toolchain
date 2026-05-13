#!/usr/bin/env python3
"""Local debugging tool — publish every camera in a dataset onto its ROS 2 topic.

This is **not** part of the scene-aligner deployment. It exists so the
aligner can be tested without a real robot present: walks
``<dataset>/videos/<camera_key>/`` for every camera in the dataset, opens
each chunked MP4 with OpenCV, and publishes frames as
``sensor_msgs/Image`` (encoding bgr8) at each video's native frame rate
(overridable via ``--fps``). Each camera's topic is derived from its key
via ``--topic-template`` (default ``/sensor/{name}_camera/rgbd/color``),
matching the aligner's ``CAMERA_TOPIC_TEMPLATE``. Loops by default; pass
``--once`` to stop after one pass.

Usage::

    python -m scene_aligner.dev_tools.fake_camera --dataset /path/to/dataset
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Iterator, Optional

import av
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image

DEFAULT_TOPIC_TEMPLATE = '/sensor/{name}_camera/rgbd/color'
DEFAULT_FRAME_ID_TEMPLATE = '{name}_camera'


def _short_camera_name(camera_key: str) -> str:
    for prefix in ('observation.images.image_', 'observation.images.'):
        if camera_key.startswith(prefix):
            return camera_key[len(prefix):]
    return camera_key


class CameraStream:
    def __init__(self, *, key: str, videos: list[Path], fps_override: Optional[float],
                 publisher, frame_id: str, logger):
        self.key = key
        self.short = _short_camera_name(key)
        self.videos = videos
        self.fps_override = fps_override
        self.publisher = publisher
        self.frame_id = frame_id
        self.logger = logger
        self.video_idx = 0
        self.container: Optional[av.container.InputContainer] = None
        self.decoder: Optional[Iterator[av.VideoFrame]] = None
        self.period = 1.0 / 30.0
        self.next_t = time.monotonic()
        self.count = 0
        self.exhausted = False

    def open_next(self, loop: bool) -> bool:
        self._close_container()
        if self.video_idx >= len(self.videos):
            if not loop:
                self.exhausted = True
                return False
            self.video_idx = 0
        path = self.videos[self.video_idx]
        try:
            container = av.open(str(path))
        except av.FFmpegError as exc:
            self.logger.warning(f'[{self.short}] cannot open {path}: {exc}')
            self.video_idx += 1
            return self.open_next(loop)
        stream = next((s for s in container.streams.video if s.type == 'video'), None)
        if stream is None:
            container.close()
            self.logger.warning(f'[{self.short}] no video stream in {path}')
            self.video_idx += 1
            return self.open_next(loop)
        native = float(stream.average_rate) if stream.average_rate else 30.0
        fps = self.fps_override or native
        self.period = 1.0 / fps if fps > 0 else 1.0 / 30.0
        self.container = container
        self.decoder = container.decode(stream)
        self.video_idx += 1
        self.logger.info(
            f'[{self.short}] streaming {path.name} @ {fps:.2f} fps '
            f'({self.video_idx}/{len(self.videos)})')
        return True

    def tick(self, now: float, get_clock, loop: bool) -> None:
        if self.exhausted:
            return
        if self.decoder is None and not self.open_next(loop):
            return
        if now < self.next_t:
            return
        try:
            decoded = next(self.decoder)
        except StopIteration:
            if not self.open_next(loop):
                return
            self.next_t = now
            return
        except av.FFmpegError as exc:
            self.logger.warning(f'[{self.short}] decode error, advancing: {exc}')
            if not self.open_next(loop):
                return
            self.next_t = now
            return
        frame = decoded.to_ndarray(format='bgr24')
        self._publish(frame, get_clock)
        self.next_t += self.period
        # Don't spiral if the loop fell badly behind.
        if self.next_t < now - 1.0:
            self.next_t = now

    def _publish(self, frame, get_clock) -> None:
        h, w = frame.shape[:2]
        msg = Image()
        msg.header.stamp = get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.height = h
        msg.width = w
        msg.encoding = 'bgr8'
        msg.is_bigendian = 0
        msg.step = w * 3
        msg.data = frame.tobytes()
        self.publisher.publish(msg)
        self.count += 1

    def _close_container(self) -> None:
        if self.container is not None:
            self.container.close()
            self.container = None
            self.decoder = None

    def close(self) -> None:
        self._close_container()


class MultiCameraPublisher(Node):
    def __init__(self, dataset_dir: Path, *, topic_template: str,
                 frame_id_template: str, fps_override: Optional[float],
                 loop: bool, only: Optional[set[str]] = None) -> None:
        super().__init__('fake_camera_multi')
        self.loop = loop
        sensor_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )
        videos_root = dataset_dir / 'videos'
        if not videos_root.is_dir():
            raise RuntimeError(f'{videos_root} does not exist')

        cam_dirs = sorted(p for p in videos_root.iterdir() if p.is_dir())
        if not cam_dirs:
            raise RuntimeError(f'No camera subdirectories in {videos_root}')

        self.streams: list[CameraStream] = []
        for cam_dir in cam_dirs:
            key = cam_dir.name
            if only is not None and key not in only and _short_camera_name(key) not in only:
                continue
            videos = sorted(cam_dir.glob('chunk-*/file-*.mp4'))
            if not videos:
                self.get_logger().warning(f'[{key}] no MP4 files; skipping')
                continue
            short = _short_camera_name(key)
            topic = topic_template.format(name=short, key=key)
            frame_id = frame_id_template.format(name=short, key=key)
            publisher = self.create_publisher(Image, topic, sensor_qos)
            self.streams.append(CameraStream(
                key=key, videos=videos, fps_override=fps_override,
                publisher=publisher, frame_id=frame_id,
                logger=self.get_logger(),
            ))
            self.get_logger().info(
                f'+ {short:>16s} → {topic}  ({len(videos)} file(s))')

        if not self.streams:
            raise RuntimeError('No streams to publish (check --only filter or dataset layout)')

        # 250 Hz tick lets streams up to ~125 fps gate themselves accurately.
        self.create_timer(1.0 / 250.0, self._tick_all)

    def _tick_all(self) -> None:
        now = time.monotonic()
        for s in self.streams:
            s.tick(now, self.get_clock, self.loop)
        if all(s.exhausted for s in self.streams):
            self.get_logger().info('All streams exhausted (--once)')
            rclpy.shutdown()

    def shutdown(self) -> None:
        for s in self.streams:
            s.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=False, default=os.environ.get('FAKE_CAMERA_DATASET', ''),
                        help='Dataset root directory (must contain videos/<camera_key>/...). '
                             'Default: $FAKE_CAMERA_DATASET.')
    parser.add_argument('--topic-template',
                        default=os.environ.get('FAKE_CAMERA_TOPIC_TEMPLATE',
                                                DEFAULT_TOPIC_TEMPLATE),
                        help=f'Topic template (default: {DEFAULT_TOPIC_TEMPLATE}). '
                             '{name} = camera key with the lerobot prefix stripped; '
                             '{key} = full camera key.')
    parser.add_argument('--frame-id-template', default=DEFAULT_FRAME_ID_TEMPLATE,
                        help=f'frame_id template (default: {DEFAULT_FRAME_ID_TEMPLATE})')
    parser.add_argument('--fps', type=float, default=None,
                        help='Override playback fps for ALL streams (default: each video native).')
    parser.add_argument('--only', action='append', default=[],
                        help='Restrict to specific camera key or short name; repeatable.')
    parser.add_argument('--once', action='store_true',
                        help='Play through once and exit (default: loop)')
    args, ros_args = parser.parse_known_args(argv)

    if not args.dataset:
        parser.error('--dataset (or $FAKE_CAMERA_DATASET) is required')

    rclpy.init(args=ros_args)
    only = set(args.only) if args.only else None
    node = MultiCameraPublisher(
        Path(args.dataset),
        topic_template=args.topic_template,
        frame_id_template=args.frame_id_template,
        fps_override=args.fps,
        loop=not args.once,
        only=only,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
