# Scene Aligner

Web overlay that helps an operator reset a physical scene to match the starting frame of a previously recorded teleoperation episode. The first frame of a chosen camera in a LeRobot dataset is shown as a stationary "ghost" reference; the live ROS 2 image feed for that camera is composited on top server-side. The operator nudges objects in the scene until live ≈ reference, then starts a new recording from a known starting pose.

This package is the standalone, locally-runnable form of the tool, suitable for development and small on-site deployments. It ships only two components:

- `scene_aligner.aligner` — the actual product: FastAPI web server, ROS 2 subscriber, OpenCV compositor.
- `scene_aligner_dev.fake_camera` — local-only debugging helper that replays every camera in a recorded dataset onto the corresponding ROS 2 topics so the aligner can be exercised without a real robot. Lives in a separate top-level package and is excluded from production wheels.

## Architecture

```text
┌──────────────┐  sensor_msgs/Image, BEST_EFFORT        ┌──────────────┐
│ fake_camera  │  on a topic derived from the chosen    │   aligner    │
│  (DEV only:  │  camera key (e.g. .../scene_camera/...)│  FastAPI +   │
│   replays    │ ─────────────────────────────────────► │  rclpy +     │
│   dataset    │                                        │  OpenCV)     │
│   MP4s)      │                                        │              │
└──────────────┘                                        └──────┬───────┘
                                                               │ HTTP/MJPEG
                                                               ▼
                                                          browser UI
```

Compositing is done **server-side** (`out = ref·R + live·L` per pixel, with optional inversion of either layer) so the two opacity sliders behave linearly and matched pixels can collapse to a flat gray cue. CSS `opacity` stacking does not have this property — see the *Design notes* section below.

## Layout

```text
scene-aligner/
├── docker/Dockerfile          # ROS 2 Jazzy + rclpy + opencv + fastapi
├── docker-compose.yml         # aligner (default) + scene_aligner_dev fake_camera (--profile dev)
├── pyproject.toml             # Python package metadata
├── sample_data/               # (gitignored) drop datasets here for local use
├── src/
│   ├── scene_aligner/         # the product (shipped in production wheel)
│   │   ├── __init__.py
│   │   ├── aligner.py         # web app + ROS subscriber + compositor + scoring
│   │   ├── episodes.py        # parquet-based episode metadata reader
│   │   └── static/            # HTML/CSS/JS served by FastAPI StaticFiles
│   │       ├── aligner.html
│   │       ├── aligner.css
│   │       └── aligner.js
│   └── scene_aligner_dev/     # debugging helpers — NOT in production wheel
│       ├── __init__.py
│       └── fake_camera.py     # multi-camera dataset → ROS Image replayer
├── tests/                     # behavioural tests (pytest)
└── README.md
```

## Prerequisites

- Docker 24+ with the Compose plugin (Docker Desktop, Rancher Desktop, or native).
- A directory of LeRobot-format datasets. Each dataset is a folder containing `meta/info.json`, optionally `meta/episodes/**/*.parquet` for per-episode references, optionally `meta/episode_labels.json` (shared format with the dataviewer sibling project) for SUCCESS/FAILURE/PARTIAL tags, and at least one camera video at `videos/<camera_key>/chunk-000/file-000.mp4`
  (e.g. `observation.images.image_scene`, `observation.images.image_left_wrist`).
  Cameras are auto-discovered from each dataset's `info.json` (any `features` entry with `dtype == "video"`). Nesting is allowed; the aligner walks the mount recursively.

## Quick start (with bundled fake-camera dev tool)

```bash
cd data-management/scene-aligner

# 1. Point the stack at your datasets and pick which one to replay.
cp .env.example .env
$EDITOR .env   # set SCENE_ALIGNER_DATASETS_DIR and SCENE_ALIGNER_PUBLISH_DATASET

# 2. Build images and start both services. The fake camera lives behind the
#    `dev` Compose profile so it is opt-in.
docker compose --profile dev up --build

# 3. Open the UI (bound to 127.0.0.1 by default).
open http://localhost:8080
```

Stop with `Ctrl+C`, tear down with `docker compose --profile dev down`.

## Quick start (against a real robot)

If you already have something publishing `sensor_msgs/Image` topics, run only the aligner — without the `--profile dev` flag the fake camera is not started:

```bash
docker compose up --build
```

Reach the robot's DDS traffic by either (a) sharing the same `ROS_DOMAIN_ID` and the same network namespace via `network_mode: host` (Linux only), or (b) configuring `ROS_DISCOVERY_SERVER` / FastDDS XML to point at the robot.

> [!WARNING]
> The aligner has no authentication. The Compose port mapping binds to `127.0.0.1` by default. To expose the UI on the LAN, set `SCENE_ALIGNER_BIND=0.0.0.0` in your `.env` — and only do so on a trusted network, since anyone reachable can drive the UI and view the live camera feed.

## Configuration

All settings are environment variables on the `aligner` service.

| Variable                    | Default                              | Description                                                                                                       |
|-----------------------------|--------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `DATASETS_DIR`              | `/data/sample_datasets`              | Root path searched for `meta/info.json`. Bind-mount your dataset tree here.                                       |
| `DEFAULT_CAMERA_KEY`        | *(empty)*                            | Camera key the UI preselects when a dataset opens. Empty → use first camera reported by that dataset.             |
| `STREAM_FPS`                | `15`                                 | MJPEG output frame rate served to the browser.                                                                    |
| `JPEG_QUALITY`              | `70`                                 | Quality of the composited MJPEG frames (0–100).                                                                   |
| `REFERENCE_CACHE_MAX`       | `64`                                 | Maximum cached reference frames (JPEG + decoded ndarray; ~900 KB each at 640×480).                                |
| `THUMBNAIL_CACHE_MAX`       | `512`                                | Maximum cached episode thumbnails.                                                                                |
| `TOPIC_PROBE_TIMEOUT_S`     | `3.0`                                | How long a topic probe waits for one frame before declaring the topic silent.                                     |
| `TOPIC_PROBE_TTL_S`         | `300.0`                              | Cache lifetime for a successful probe result before re-probing on next `/api/topics` call.                        |
| `SCENE_ALIGNER_LOG_LEVEL`   | `INFO`                               | Python + rclpy log level. `DEBUG` adds per-message frame logs and discovery dumps.                                |
| `ROS_DOMAIN_ID`             | `42` (compose) / unset (bare)        | Standard ROS 2 discovery scope.                                                                                   |
| `RMW_IMPLEMENTATION`        | `rmw_cyclonedds_cpp` (compose)       | DDS implementation. Keep aligned with whatever publishes the camera. Compose ships Cyclone because Docker Desktop on macOS drops UDP multicast across bridged networks. |
| `CYCLONEDDS_URI`            | inline XML (compose)                 | Cyclone configuration. Compose embeds an XML that disables multicast and lists `aligner` + `publisher` as unicast peers; override when talking to a real robot. |

Compose-level conveniences (read from `.env`):

| Variable                              | Default                              | Description                                                                                       |
|---------------------------------------|--------------------------------------|---------------------------------------------------------------------------------------------------|
| `SCENE_ALIGNER_DATASETS_DIR`          | `./sample_data`                      | Host directory mounted at `/data/sample_datasets` (read-only).                                    |
| `SCENE_ALIGNER_PUBLISH_DATASET`       | —                                    | Sub-path of the dataset whose videos the fake-camera dev tool replays. Every camera in that dataset is published on its own topic. |
| `SCENE_ALIGNER_DEFAULT_CAMERA`        | *(empty)*                            | Forwarded to `DEFAULT_CAMERA_KEY` in the aligner.                                                 |
| `SCENE_ALIGNER_BIND`                  | `127.0.0.1`                          | Host interface the aligner port is bound to. Set to `0.0.0.0` to expose on the LAN (no auth — trusted networks only). |
| `SCENE_ALIGNER_PORT`                  | `8080`                               | Host port for the web UI.                                                                         |
| `SCENE_ALIGNER_LOG_LEVEL`             | `INFO`                               | Forwarded to the aligner container.                                                               |

## HTTP API

| Method | Path                                          | Description                                                                                                                                              |
|--------|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| GET    | `/`                                           | Single-page HTML UI.                                                                                                                                     |
| GET    | `/stream.mjpg`                                | Server-composited MJPEG (`multipart/x-mixed-replace`).                                                                                                   |
| GET    | `/api/datasets`                               | List of detected datasets (id, name, acquired_at, episodes, frames, …).                                                                                  |
| GET    | `/api/dataset/{id}/info?camera=<key>`         | Curated metadata summary for a dataset (defaults to the first camera).                                                                                   |
| GET    | `/api/dataset/{id}/raw`                       | Full `info.json`.                                                                                                                                        |
| GET    | `/api/dataset/{id}/thumbnail?camera=<key>`    | 320-pixel JPEG of frame 0.                                                                                                                               |
| GET    | `/api/dataset/{id}/video?camera=<key>`        | Camera MP4 (HTTP `Range` supported, used by the in-grid previews).                                                                                       |
| GET    | `/api/episodes?dataset=<id>`                  | Episode index for the picker (labels, task name, frame range, etc.).                                                                                     |
| GET    | `/api/labels?dataset=<id>`                    | Per-dataset label vocabulary and per-episode label map (mirrors the dataviewer's `episode_labels.json`).                                                 |
| GET    | `/api/episode/info`                           | Metadata for one episode (query: `dataset`, `episode`).                                                                                                  |
| GET    | `/api/episode/thumbnail`                      | JPEG of an episode's reference frame at small size (query: `dataset`, `camera`, `episode`).                                                              |
| GET    | `/api/episode/reference`                      | Full-resolution JPEG of an episode's reference frame.                                                                                                    |
| GET    | `/api/episode/video`                          | Episode-scoped MP4 (`Range` supported).                                                                                                                  |
| GET    | `/api/reference?dataset=<id>&camera=<key>`    | Full-resolution JPEG of the dataset-level reference frame.                                                                                               |
| GET    | `/api/state`                                  | Current selection + blend parameters (dataset, camera, ROS topic, episode, opacities, invert flags).                                                     |
| POST   | `/api/state`                                  | Update any of `dataset`, `camera`, `topic`, `episode`, `ref_op`, `live_op`, `invert_ref`, `invert_live` (all fields optional; only those present change). |
| GET    | `/api/topics`                                 | All discovered ROS 2 topics. `sensor_msgs/Image` entries are enriched with a `probe` record (`encoding`, `width`, `height`, `step`, `publisher_count`, `displayable`, `error`); the server requests probes lazily and the cache fills in across polls. |
| GET    | `/api/live_status`                            | Snapshot of the currently-subscribed topic: publisher count, last message timestamp, last decode error, and a human-readable diagnostic message.         |
| GET    | `/api/issues?since=<seq>&limit=<n>`           | Incremental pull of journal entries (warnings, decode failures, missing publishers, score exceptions, dataset I/O errors). Used by the UI toasts.        |
| GET    | `/api/score?since=<unix_ts>`                  | Latest alignment score plus history points newer than `since`; `low_texture` flag set when the scene lacks enough gradient for a stable score.           |

## Local Python development (without Docker)

You'll still need a working ROS 2 Jazzy install to provide `rclpy` and `sensor_msgs`. From an environment that already sources `/opt/ros/jazzy/setup.bash`:

```bash
uv venv --python 3.12 --system-site-packages   # inherit rclpy from ROS
source .venv/bin/activate
uv pip install -e ".[dev]"

# Terminal 1 — synthetic camera
python -m scene_aligner_dev.fake_camera \
    --dataset /path/to/dataset \
    --topic-template '/sensor/{name}_camera/rgbd/color'

# Terminal 2 — web app
DATASETS_DIR=/path/to/sample_datasets \
  uvicorn scene_aligner.aligner:app --host 0.0.0.0 --port 8080
```

`--system-site-packages` is required because `rclpy` ships only as a Debian package, not on PyPI.

## Tests

Behavioural tests live under `tests/`. They cover the path-traversal guard, the LRU cache, the Pydantic state validator, the alignment-score low-texture floor, the parquet episode reader, and the issue-journal that powers UI toasts. Run them inside the same image to inherit `rclpy`/`pyarrow`/`opencv`:

```bash
docker compose run --rm --no-deps -v "$PWD:/work" -w /work aligner \
  bash -lc 'source /opt/ros/jazzy/setup.bash \
            && pip3 install --quiet --break-system-packages --no-deps pytest \
            && python3 -m pytest -q tests/'
```

There are no integration tests against a live ROS topic; the score endpoint and MJPEG stream are exercised manually via `docker compose --profile dev up`.

## Design notes

### Why server-side compositing

A naïve frontend implementation stacks two `<img>` elements with CSS `opacity`. CSS opacity is the "over" operator applied successively against the page background, not a true linear average — so two layers at 50/50 produce `0.5·live + 0.25·(255 − ref) + 0.25·bg`, which still leaks the live image's chroma when matched. Computing `out = α_R·R + α_L·L` in OpenCV makes the sliders mean what they say, so 50/50 with the reference inverted collapses matched pixels to flat mid-gray.

### Why MJPEG, not WebSocket / WebRTC

The browser decodes MJPEG natively via `<img src="/stream.mjpg">`. Zero JavaScript decoding loop, no codec setup, and CSS transformations apply uniformly. WebRTC would cut bandwidth at the cost of a TURN/STUN setup we don't need on a LAN. WebSocket + canvas would re-implement what the `<img>` element gives us for free.

### Alignment score

The score is the zero-mean normalised cross-correlation (ZNCC) of the Sobel gradient magnitudes of the live and reference frames, in `[0, 1]`.
Subtracting the mean removes additive brightness offsets; dividing by std removes multiplicative gain — so turning a lamp on/off, opening curtains, or tweaking exposure barely moves the gauge, but moved props do.
A low-texture floor (variance threshold) returns `null` instead of a misleading 0/0 → 0 collapse for near-flat scenes; the UI surfaces that as "low texture: scene needs more detail to score".
The displayed value is EMA-smoothed (α ≈ 0.4) and the gauge auto-zooms to the last ~12 s sliding window so fine adjustments stay visible.

### Why one Dockerfile

Both services need ROS 2, OpenCV, and NumPy. The aligner additionally needs FastAPI/uvicorn, which the dev-only fake-camera does not — but the cost of dragging those extra ~30 MB along on the dev tool is far smaller than the cost of maintaining a second Dockerfile, a second layer cache, and a second build step for a local-development helper. If you redeploy this in a constrained environment, splitting `docker/Dockerfile.aligner` and `docker/Dockerfile.fake-camera` is straightforward.

## License

Same license as the parent repository.
