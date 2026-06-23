<!-- markdownlint-disable-file -->
# PR Regression Safety — narrated deck

Research-advocacy deck for `microsoft/physical-ai-toolchain`. Thesis: green CPU-only CI is blind to the costly regression classes (CUDA / Isaac / interpreter ABI), and a phased gate fixes it — four controls that ship now (~$0) plus one funded GPU capstone.

Current build: **53 slides** (34 core + 19 appendix) · narrated **MP4 ~25m52s @ 1×**. Re-cut applies a 7-lens critique (see `critique-SYNTHESIS.md` under research, below).

## What's here

| Path | Tracked | Notes |
| --- | --- | --- |
| `gen_content.py` | ✅ | Single source of truth — slide structure, render kinds, snippets, narration. Self-contained. |
| `slides_src.py` | ✅ | Legacy dark-theme generator; **no longer imported** by `gen_content.py`. Kept for reference/history. |
| `build_video.sh` | ✅ | macOS `say` TTS + ffmpeg → per-slide clips → `presentation.mp4`. |
| `PRESENTATION_SPEC.md` | ✅ | Durable requirements + applied-critique record. **Read before editing.** |
| `narration-script.md` | ✅ | Full exported narration (one section per slide). |
| `deck/presentation.pdf` | ✅ | Lightweight viewable export (~3.4 MB). |
| `presentation.mp4` | ✅ | The narrated video (~60 MB). |
| `content/`, `narration/`, `slides/` | ❌ ignored | Generator output — recreated by `gen_content.py` + the render steps. |
| `deck/presentation.pptx` | ❌ ignored | ~37 MB on the slim template — rebuild it. |
| `audio/`, `clips/` | ❌ ignored | Pure TTS/encode caches — `build_video.sh` regenerates them. |
| the brand template | ❌ ignored | Large Microsoft-internal asset — **provide it yourself** (see below). |

## Prerequisites

- macOS (the video step uses the `say` TTS CLI and the System Voice — **no `-v` flag**).
- `ffmpeg` + `ffprobe` on `PATH`.
- The HVE-Core PowerPoint skill venv (provides `build_deck.py` / `export_slides.py` / `render_pdf_images.py` + `soffice`):
  `~/.copilot/installed-plugins/hve-core/hve-core-all/skills/experimental/powerpoint/.venv/bin/python`
- The **Global-Skilling-PowerPoint-Template-slim.pptx** brand template (~52 MB). Not in git. Default location:
  `~/OneDrive - Microsoft/Tools/Templates/Global-Skilling-PowerPoint-Template-slim.pptx` (path has spaces — quote it).
  The slim variant shares the masters/layouts/theme of the full ~547 MB source but downscales embedded media, so the built PPTX is ~37 MB instead of ~157 MB. Renders are pixel-identical at 1080p.

## Rebuild

```bash
SK=~/.copilot/installed-plugins/hve-core/hve-core-all/skills/experimental/powerpoint
VENV=$SK/.venv/bin/python
TPL="$HOME/OneDrive - Microsoft/Tools/Templates/Global-Skilling-PowerPoint-Template-slim.pptx"

# 1. content/ + narration/ + narration-script.md  (no template needed)
$VENV gen_content.py

# 2. build the PPTX  (needs the slim template)
$VENV $SK/scripts/build_deck.py --content-dir content --style content/global/style.yaml \
  --template "$TPL" --output deck/presentation.pptx

# 3. export + render slide images  (ignore "MuPDF error: No common ancestor" warnings)
$VENV $SK/scripts/export_slides.py --input deck/presentation.pptx --output deck/presentation.pdf
$VENV $SK/scripts/render_pdf_images.py --input deck/presentation.pdf --output-dir slides --dpi 120

# 4. narrate + encode the video  (re-synthesizes audio if the slide set changed)
SPEED=1.0 ./build_video.sh
```

Rebuilding **only the video** (e.g. after a narration tweak) needs steps 1, 3, then 4. Clear `audio/` + `clips/` first when the slide set changes, so narration re-synthesizes.

## Research and critique

Full evidence and the 7-lens critique live under the (otherwise git-ignored) tracking tree, force-added so they travel with this branch:

- `.copilot-tracking/research/2026-06-19/pr-regression-safety-research.md` — main research doc.
- `.copilot-tracking/research/subagents/2026-06-19/` — per-thread captures + `critique-*.md` (incl. `critique-SYNTHESIS.md`).
