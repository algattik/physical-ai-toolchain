"""Generate the restructured deck on the Global-Skilling template (light brand).

Structure: Cover -> AA Current state -> per Phase (A Problem today / B What others
do / C Recommendation) with ample real config + YAML -> Roadmap & close.
Reuses refined slide bodies/notes from slides_src; adds code/compare slides.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

FONT = "Segoe UI"
MONO = "DejaVu Sans Mono"
TEXT = "#1A1A1A"
MUTED = "#5B5B5B"
BODY = "#2B2B2B"
WHITE = "#FFFFFF"
SUBWHITE = "#EAF1FB"
BLUE = "#0078D4"
GREEN = "#107C10"
RED = "#C4314B"
AMBER = "#9D5D00"
PURPLE = "#5C2E91"
CARD = "#F2F3F5"
LINE = "#E1E4E8"
CODECLR = "#16324F"

W, H = 13.333, 7.5
ML = 0.92
CW = W - 2 * ML

# Template slide-number placeholder (TITLE-1 / DIVIDER_* layouts), bottom-right.
PAGENUM_L, PAGENUM_T, PAGENUM_W, PAGENUM_H = 12.567, 7.079, 0.629, 0.221
PAGENUM_SIZE = 8


def _inline_runs(text, base_font, size, color, bold):
    """Split a line on backtick spans -> rich runs; code spans use MONO font.

    Backticks themselves are dropped (they are markup, not literal text).
    """
    runs = []
    for i, part in enumerate(str(text).split("`")):
        if part == "":
            continue
        is_code = (i % 2 == 1)
        runs.append({"text": part, "font": MONO if is_code else base_font,
                     "size": size, "color": color, "bold": bold})
    if not runs:
        runs = [{"text": " ", "font": base_font, "size": size, "color": color, "bold": bold}]
    return runs


def tb(left, top, width, height, text, size, color, bold=False, align="left", font=FONT):
    """Text box with inline-code (backtick) -> monospace and markdown-style bullets."""
    paras = []
    for line in str(text).split("\n"):
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if m:
            level = len(m.group(1).replace("\t", "  ")) // 2
            p = {"alignment": align, "level": level, "bullet_char": "\u2022",
                 "bullet_margin_left": 228600, "bullet_indent": -228600,
                 "runs": _inline_runs(m.group(2), font, size, color, bold)}
        else:
            p = {"alignment": align, "runs": _inline_runs(line, font, size, color, bold)}
        paras.append(p)
    return {"type": "textbox", "left": left, "top": top, "width": width, "height": height,
            "paragraphs": paras}


def rect(left, top, width, height, fill):
    return {"type": "shape", "shape": "rectangle", "left": left, "top": top,
            "width": width, "height": height, "fill": fill}


def code_box(left, top, width, height, code, size, color=CODECLR):
    paras = [{"text": ln, "font": MONO, "font_size": size, "font_color": color}
             for ln in code.strip("\n").split("\n")]
    return {"type": "textbox", "left": left, "top": top, "width": width, "height": height,
            "paragraphs": paras}


def _code_lines(code):
    return len(code.strip("\n").split("\n"))


def _code_height(code, size, pad=0.40, hdr=0.0):
    """Inches needed to render `code` at `size` pt — so cards fit the snippet
    instead of a fixed too-tall box (avoids top-heavy slides with hollow bottoms)."""
    return pad + hdr + _code_lines(code) * (size / 72.0 * 1.34)


def heading(title, accent):
    return [rect(ML, 0.62, 0.11, 0.82, accent),
            tb(ML + 0.30, 0.55, CW - 0.3, 1.0, title, 28, TEXT, bold=True),
            rect(ML, 1.55, CW, 0.012, LINE)]


# ---- cover / divider (white text overlaid on the template's colored layout) ----
def render_title(s):
    return [tb(0.72, 2.25, 7.0, 1.8, s["title"], 46, WHITE, bold=True),
            tb(0.74, 4.05, 6.6, 1.0, s["subtitle"], 22, WHITE),
            tb(0.74, 6.45, 7.2, 0.5, s["sub2"], 14, SUBWHITE)]


def render_section(s):
    el = [tb(0.72, 2.5, 7.4, 0.6, s["part"], 22, WHITE, bold=True),
          tb(0.72, 3.15, 7.6, 1.5, s["title"], 37, WHITE, bold=True)]
    if s.get("sub"):
        el.append(tb(0.74, 4.95, 7.0, 0.9, s["sub"], 18, SUBWHITE))
    return el


# ---- content (dark on white TITLE-1 layout) ----
def render_bullets(s):
    el = heading(s["title"], s["accent"])
    el.append(tb(ML, 1.85, CW, 4.5, s["body"], s.get("body_size", 20), BODY))
    return el


def render_stat(s):
    accent = s["accent"]
    el = heading(s["title"], accent)
    el.append(tb(ML - 0.03, 1.8, CW, 1.5, s["stat"], 70, accent, bold=True))
    el.append(tb(ML, 3.4, CW, 0.8, s["statcap"], 21, TEXT))
    el.append(tb(ML, 4.4, CW, 1.9, s["body"], s.get("body_size", 19), BODY))
    return el


def render_twocol(s):
    accent = s["accent"]
    el = heading(s["title"], accent)
    gap = 0.6
    colw = (CW - gap) / 2
    lx, rx = ML, ML + colw + gap
    la = s.get("left_accent", accent)
    ra = s.get("right_accent", accent)
    el.append(tb(lx, 1.85, colw, 0.7, s["left_head"], 20, la, bold=True))
    el.append(tb(lx, 2.62, colw, 3.9, s["left_body"], s.get("body_size", 18), BODY))
    el.append(rect(ML + colw + gap / 2 - 0.008, 1.95, 0.014, 4.2, LINE))
    el.append(tb(rx, 1.85, colw, 0.7, s["right_head"], 20, ra, bold=True))
    el.append(tb(rx, 2.62, colw, 3.9, s["right_body"], s.get("body_size", 18), BODY))
    return el


def render_code(s):
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    has_cap = bool(s.get("caption"))
    if has_cap:
        el.append(tb(ML, 1.66, CW, 0.45, s["caption"], 15, MUTED))
    region_top = 2.2 if has_cap else 1.8
    avail = 6.55 - region_top
    size = s.get("code_size", 13)
    hdr = 0.40 if s.get("file") else 0.0
    h = min(avail, _code_height(s["code"], size, pad=0.44, hdr=hdr))
    top = region_top + min(0.7, max(0.0, (avail - h) / 2))
    el.append(rect(ML, top, CW, h, CARD))
    el.append(rect(ML, top, 0.07, h, accent))
    if s.get("file"):
        el.append(tb(ML + 0.28, top + 0.12, CW - 0.6, 0.32, s["file"], 12, MUTED, font=MONO))
        code_top = top + 0.50
    else:
        code_top = top + 0.20
    el.append(code_box(ML + 0.34, code_top, CW - 0.7, top + h - code_top - 0.12,
                       s["code"], size))
    return el


def render_codecompare(s):
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    if s.get("caption"):
        el.append(tb(ML, 1.64, CW, 0.4, s["caption"], 14.5, MUTED))
    gap = 0.45
    colw = (CW - gap) / 2
    top, bot = 2.6, 6.55
    h = bot - top
    for side, x, dac in (("left", ML, s.get("left_accent", RED)),
                         ("right", ML + colw + gap, s.get("right_accent", GREEN))):
        el.append(tb(x, 2.14, colw, 0.4, s[side + "_head"], 16, dac, bold=True))
        el.append(rect(x, top, colw, h, CARD))
        el.append(rect(x, top, 0.06, h, dac))
        el.append(code_box(x + 0.24, top + 0.18, colw - 0.42, h - 0.34,
                           s[side + "_code"], s.get("code_size", 11)))
    return el


def render_primer(s):
    """Teaching slide: explanation paragraph + key terms (left), code card (right)."""
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    gap = 0.5
    lw = (CW - gap) * 0.46
    rw = CW - gap - lw
    rx = ML + lw + gap
    el.append(tb(ML, 1.9, lw, 3.6, s["body"], s.get("body_size", 16), BODY))
    if s.get("terms"):
        el.append(tb(ML, 5.7, lw, 0.9, "Key terms: " + s["terms"], 12, MUTED))
    region_top, avail = 1.9, 4.5
    csize = s.get("code_size", 11.5)
    hdr = 0.36 if s.get("file") else 0.0
    h = min(avail, _code_height(s["code"], csize, pad=0.40, hdr=hdr))
    top = region_top + max(0.0, (avail - h) / 2)
    el.append(rect(rx, top, rw, h, CARD))
    el.append(rect(rx, top, 0.06, h, accent))
    if s.get("file"):
        el.append(tb(rx + 0.22, top + 0.12, rw - 0.4, 0.3, s["file"], 11, MUTED, font=MONO))
        ct = top + 0.46
    else:
        ct = top + 0.18
    el.append(code_box(rx + 0.28, ct, rw - 0.5, top + h - ct - 0.10,
                       s["code"], csize))
    return el


def render_deflist(s):
    """Heading + optional caption + label→definition rows (single column)."""
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    rows = s["rows"]
    top = 1.95
    if s.get("caption"):
        el.append(tb(ML, 1.64, CW, 0.4, s["caption"], 14.5, MUTED))
        top = 2.25
    n = len(rows)
    rowh = min(0.78, (6.55 - top) / n)
    labw = s.get("label_w", 3.1)
    for i, (label, desc) in enumerate(rows):
        y = top + i * rowh
        el.append(rect(ML, y + 0.06, 0.07, rowh - 0.18, accent))
        el.append(tb(ML + 0.24, y + 0.04, labw, rowh - 0.1, label, s.get("label_size", 14), TEXT, bold=True))
        el.append(tb(ML + 0.24 + labw + 0.2, y + 0.04, CW - labw - 0.5, rowh - 0.1,
                     desc, s.get("desc_size", 13), BODY))
    return el


def render_glossary(s):
    """Two-column compact term (bold) + definition, non-overlapping."""
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    rows = s["rows"]
    half = (len(rows) + 1) // 2
    cols = [rows[:half], rows[half:]]
    gap = 0.5
    colw = (CW - gap) / 2
    sz = s.get("size", 11.5)
    termw = s.get("term_w", 1.95)
    for ci, col in enumerate(cols):
        x = ML + ci * (colw + gap)
        rowh = (6.45 - 1.95) / max(half, 1)
        for ri, (term, desc) in enumerate(col):
            y = 1.95 + ri * rowh
            el.append(tb(x, y, termw, rowh - 0.04, term, sz, accent, bold=True))
            el.append(tb(x + termw + 0.12, y, colw - termw - 0.12, rowh - 0.04,
                         "— " + desc, sz, BODY))
    return el


RENDER = {"title": render_title, "section": render_section, "bullets": render_bullets,
          "stat": render_stat, "twocol": render_twocol, "code": render_code,
          "codecompare": render_codecompare, "primer": render_primer,
          "deflist": render_deflist, "glossary": render_glossary}


_MARK_CLR = {"y": GREEN, "~": AMBER, "n": MUTED, "x": RED}
_MARK_GLY = {"y": "\u2713", "~": "\u223c", "n": "\u2013", "x": "\u2717"}


def render_matrix(s):
    """Failure map: incidents (rows) x controls/phases (columns), marked cells."""
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    top = 1.95
    if s.get("caption"):
        el.append(tb(ML, 1.64, CW, 0.4, s["caption"], 14.5, MUTED))
        top = 2.3
    cols = s["cols"]
    rows = s["rows"]
    labw = s.get("label_w", 3.5)
    gx = ML + labw
    cw = (CW - labw) / len(cols)
    el.append(tb(ML + 0.02, top, labw - 0.1, 0.4, s.get("corner", ""), 12.5, MUTED, bold=True))
    for j, c in enumerate(cols):
        el.append(tb(gx + j * cw, top, cw, 0.4, c, 12.5, TEXT, bold=True, align="center"))
    body_top = top + 0.52
    el.append(rect(ML, body_top - 0.08, CW, 0.014, LINE))
    n = len(rows)
    rowh = min(0.9, (6.42 - body_top) / n)
    for i, r in enumerate(rows):
        y = body_top + i * rowh
        if i:
            el.append(rect(ML, y, CW, 0.008, LINE))
        el.append(tb(ML + 0.02, y + 0.07, labw - 0.12, rowh * 0.6, r["label"],
                     s.get("label_size", 13.5), TEXT, bold=True))
        if r.get("sub"):
            el.append(tb(ML + 0.02, y + 0.06 + rowh * 0.48, labw - 0.12, rowh * 0.4,
                         r["sub"], 10.5, MUTED))
        for j, m in enumerate(r["cells"]):
            el.append(tb(gx + j * cw, y + 0.04, cw, rowh - 0.08, _MARK_GLY.get(m, m),
                         18, _MARK_CLR.get(m, BODY), bold=True, align="center"))
    if s.get("legend"):
        el.append(tb(ML, 6.52, CW, 0.4, s["legend"], 11.5, MUTED))
    return el


RENDER["matrix"] = render_matrix


def render_phases(s):
    accent = s.get("accent", BLUE)
    el = heading(s["title"], accent)
    phases = s["phases"]
    n = len(phases)
    top = 1.8
    gap = 0.16
    rowh = (6.55 - top - (n - 1) * gap) / n
    tagw, costw = 2.0, 1.65
    cx = ML + tagw + 0.24
    cw = CW - tagw - costw - 0.55
    costx = ML + CW - costw
    for i, p in enumerate(phases):
        y = top + i * (rowh + gap)
        pa = p.get("accent", accent)
        el.append(rect(ML, y, CW, rowh, CARD))
        el.append(rect(ML, y, 0.10, rowh, pa))
        el.append(tb(ML + 0.30, y + 0.14, tagw - 0.34, 0.4, p["tag"], 16, pa, bold=True))
        el.append(tb(ML + 0.30, y + 0.52, tagw - 0.30, 0.3, p["when"], 10.5, MUTED))
        el.append(rect(ML + tagw, y + 0.16, 0.012, rowh - 0.32, LINE))
        el.append(tb(cx, y + 0.13, cw, 0.4, p["head"], 16, TEXT, bold=True))
        el.append(tb(cx, y + 0.50, cw, rowh - 0.58, p["items"], 11.5, BODY))
        el.append(rect(costx - 0.18, y + 0.16, 0.012, rowh - 0.32, LINE))
        el.append(tb(costx, y + (rowh - 0.4) / 2, costw - 0.12, 0.4, p["cost"], 15, pa,
                     bold=True, align="center"))
    return el


RENDER["phases"] = render_phases

# ----------------------------------------------------------------------------
# ---- code snippets (real current state + proposed) ----
C_DEPENDABOT_TODAY = """
updates:
- package-ecosystem: uv
  directory: /training/rl
  groups:
    training-dependencies:
      patterns: ["*"]          # catch-all: no risk split
  ignore:
  - dependency-name: marshmallow
    versions: [">=4.0.0"]      # reactive pin, post-breakage
  schedule: { interval: weekly, day: monday }
# ... repeated x21: npm, 10x uv, terraform, go, docker, actions
"""

C_CI_TODAY = """
jobs:
  test:
    runs-on: ubuntu-latest        # 4 vCPU - 16 GB - ~14 GB disk - NO GPU
    steps:
      - uses: actions/setup-python@...   # python-version: '3.12'
      - run: uv sync --group dev
      - run: uv pip install torch==2.11.0      # force-installed
# training/il/lerobot/uv.lock pins torch 2.10.0  ->  live desync (#958)
"""

C_GHAW_TODAY = """
on:
  slash_command:
    name: aw-dependabot-review   # a maintainer types it (can run pre-CI)
permissions:
  contents: read
  pull-requests: read            # advisory only - it never writes
engine: copilot
"""

C_OTHERS_GROUPING = """
# vercel/ai - split production vs development (npm)
groups:
  packages-production:
    dependency-type: production
    update-types: [minor, patch]
  packages-development:
    dependency-type: development
    update-types: [minor, patch]
# huggingface/transformers - 7-day stability window
cooldown:
  default-days: 7
"""

CMP_DB_LEFT = """
groups:
  training-deps:
    patterns: ["*"]
ignore:
- dependency-name:
    marshmallow
  versions: [">=4.0.0"]
# x21 blocks
# patch == major
"""
CMP_DB_RIGHT = """
groups:
  prod-min-patch:
    dependency-type:
      production
    update-types:
      [minor, patch]
# majors isolated
cooldown:
  default-days: 7
# security: ungrouped
"""

CMP_REV_LEFT = """
on:
  slash_command:
    name:
      aw-dependabot-review
# maintainer-triggered
# may run before CI
# re-comments on rebase
"""
CMP_REV_RIGHT = """
on:
  workflow_run:
    workflows:
      ["PR Validation"]
    types: [completed]
  skip-if-check-failing:
    include: ["PR Validation"]
safe-outputs:
  add-comment:
    hide-older-comments:
      true
"""

C_SMOKE = """
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - run: uv lock --check                       # resolution drift
      - run: uv pip install torch --index-url https://download.pytorch.org/whl/cpu
      - run: python -c "import lerobot, torch"      # ABI / import smoke
      - run: ./training/rl/scripts/submit-osmo-training.sh --config-preview
      - uses: jlumbroso/free-disk-space@...
      - run: docker build -f evaluation/sil/docker/Dockerfile.lerobot-eval .
"""

C_AUTOMERGE = """
on: pull_request_target          # base context; do NOT checkout the PR head here
permissions: { contents: write, pull-requests: write }   # NOT id-token
jobs:
  automerge:
    steps:
      - uses: dependabot/fetch-metadata@<sha>   # reads metadata; runs no PR code
        id: meta
      - if: >                    # conservative scope: patch-only, dev/docs/actions
          steps.meta.outputs.update-type == 'version-update:semver-patch' &&
          steps.meta.outputs.dependency-type == 'direct:development'
        run: gh pr merge --auto --squash "$PR_URL"   # waits for green required checks
# security PRs are never auto-merged; torch/cuda/isaac/numpy excluded by allowlist
"""

C_GPU_E2E = """
# Two jobs: untrusted PR code never runs on the token-bearing runner.
# Job A — on: pull_request (fork-safe: read-only token, NO secrets, no cloud login)
jobs:
  render-spec:
    steps:
      - run: ./scripts/render-osmo-spec.sh > job.json   # build a constrained spec
      - uses: actions/upload-artifact@<sha>             # hand off job.json only
# Job B — on: pull_request_review (approved) → runs TRUSTED base-branch workflow
  submit-gpu:
    if: github.event.review.state == 'approved'
    environment: e2e-approval        # required-reviewers gate releases OIDC
    steps:
      - uses: actions/checkout@<sha>            # BASE ref, not the PR head
      - uses: actions/download-artifact@<sha>   # the job.json from Job A
      - run: ./scripts/validate-spec.sh job.json   # allowlist-check before submit
      - uses: azure/login@v2                    # OIDC — minted only after approval
      - run: ./training/rl/scripts/submit-osmo.sh job.json  # PR code runs in the pool
"""

C_RENOVATE = """
// run via renovatebot/github-action — no Mend App to approve
{
  "extends": ["config:best-practices"],
  "minimumReleaseAge": "3 days",
  "packageRules": [
    { "matchManagers": ["npm","pep621","terraform","gomod"],
      "groupName": "all-minor-patch",
      "matchUpdateTypes": ["minor","patch"], "automerge": true },
    { "matchPackageNames": ["torch"], "allowedVersions": "<2.11.0" }
  ]
}
"""

# ---- primer snippets ----
P_DEPENDABOT = """
# version updates (scheduled) — one stream
- package-ecosystem: uv
  directory: /training/il/lerobot
  groups:                       # batch into 1 PR
    lerobot-deps: { patterns: ["*"] }
  ignore:                       # deliberate pin
  - dependency-name: torch
    versions: [">=2.11.0"]
  open-pull-requests-limit: 5
# security updates = a SEPARATE stream
"""

P_UVLOCK = """
# pyproject.toml — human-authored (PEP 621)
[project]
requires-python = ">=3.12"
dependencies = ["lerobot==0.5.1"]

# uv.lock — resolver output: exact
#   versions + hashes + platform markers
# CI gate: `uv lock --check`  (no drift)
"""

P_GHSA = """
GHSA-xxxx-xxxx-xxxx   (-> a CVE)
package:    urllib3
vulnerable: < 2.7.0
patched:    >= 2.7.0
severity:   high   (CVSS)
=> security PR: bump to min patched
=> never batch / delay these
"""

P_RENOVATE = """
// renovate.json — ONE config, all ecosystems
{
  "extends": ["config:best-practices"],
  "minimumReleaseAge": "3 days",   // stability window
  "packageRules": [
    { "matchUpdateTypes": ["minor","patch"],
      "automerge": true }
  ]
}
// runs as the Mend GitHub App OR
//   renovatebot/github-action (self-hosted, no App)
"""

P_GATING = """
jobs:
  changes:                      # 1 cheap job computes booleans
    outputs: { training: ... }
  pytest-training:
    needs: changes
    if: needs.changes.outputs.training == 'true'
  pr-validation-summary:        # 1 stable required check
    if: always()                # aggregates everything
"""

P_UNTRUSTED = """
on: pull_request          # fork PR: read-only token, NO secrets  (safe)
# on: pull_request_target # base context, HAS secrets -> "pwn request"
jobs:
  gpu:
    environment: gpu-approved   # gate runs BEFORE any token is minted
    permissions: { contents: read, id-token: write }   # OIDC, no stored secret
    steps: [ { uses: azure/login@<sha> } ]
# id-token:write is safe only if the cloud federated policy pins
#   sub / aud / repo / environment — fork refs must NOT match it
"""

P_GHAW = """
---
engine: copilot                 # markdown file -> compiled .lock.yml
on: { slash_command: { name: aw-dependabot-review } }
permissions: { contents: read, pull-requests: read }   # agent is READ-ONLY
safe-outputs:                   # the only way it can act
  add-comment: { max: 1 }
---
Review this Dependabot PR and post an advisory comment.
"""

NEMO_GATE = """
# NeMo gates the expensive GPU run behind a human/queue approval
cicd-wait-in-queue:
  environment: test          # PAUSES until a reviewer/queue-bot approves
  # ...all GPU jobs `needs: [cicd-wait-in-queue]`
# fork PRs are mirrored to `pull-request/NNN` branches by a bot,
# so untrusted code never runs via pull_request_target ("pwn request")
runner: nemo-ci-aws-gpu-x2   # self-hosted GPU; --gpus all
"""

# ---- Renovate: Microsoft-OSS adoption evidence ----
RENOVATE_ADOPTION = """
Microsoft OSS, by the evidence (Sourcegraph + file fetches):
  Dependabot : the de-facto standard — vscode, TypeScript,
               dotnet/runtime, fluentui, semantic-kernel, …
  Renovate   : ~19 microsoft-org repos (~1.5-3%)
               mostly the VS-team cluster using a shared preset
               github>microsoft/vs-renovate-presets
  Azure: 1   dotnet: ~9   github org: 0
  OSPO page: GitHub-native dep features only (no Renovate mention)
Escape hatch: `renovatebot/github-action` (self-hosted)
              -> NO Mend App approval needed
"""

# ----------------------------------------------------------------------------
C_AML_ENV = """
environment_variables:
  PYTHON: /workspace/isaaclab/isaaclab.sh -p
  ACCEPT_EULA: "Y"
  PRIVACY_CONSENT: "Y"
  HYDRA_FULL_ERROR: "1"
  TRAINING_CHECKPOINT_OUTPUT: ${{outputs.checkpoints}}
  # Do NOT add ${{outputs.X}} env vars here — AzureML does not
  # substitute template expressions in environment_variables
  # (only inside command:). Training reads $AZURE_ML_OUTPUT_<NAME>.
compute: azureml:gpu-cluster
environment: azureml:isaaclab-training-env:latest
"""

# ---- Tier-1 real-image import-smoke (catches the #809/#790 interpreter class) ----
C_TIER1 = """
# Pull the REAL runtime image and reinstall the PR's lock the way prod does,
# then run the launcher's import-check mode (same graph as training, stops
# before AppLauncher — the only GPU step).
docker run --rm --platform linux/amd64 \\
  nvcr.io/nvidia/isaac-lab:2.3.2 bash -lc '
    /isaac-sim/kit/python/bin/python3 -V        # 3.11 — the real runtime
    uv export --frozen --no-emit-project --directory training/rl \\
      | uv pip install --system --no-deps -r -  # <- the #809 3.12-lock fails HERE
    python -m training.rl.scripts.launch --mode import-check  # ABI net: graph loads?
'   # all on CPU — no GPU touched
"""

C_TIER_MATRIX = """
# one image per job (can't co-resident 18+18+9 GB) · path-gated
matrix:
  - {dir: training/rl,         image: isaac-lab:2.3.2}          # on training/rl/**
  - {dir: training/il/lerobot, image: pytorch:2.11.0-cuda12.8}  # on training/il/**
  - {dir: evaluation,          image: <build Dockerfile.lerobot-eval>}
steps:
  - uses: jlumbroso/free-disk-space@<sha>   # Isaac ~18-22 GB unpacked
  - run: docker system prune -af            # between matrix legs
"""

C_RSL_REFACTOR = """
# training/rl/scripts/rsl_rl/train.py — a small refactor widens CPU smoke
# BEFORE (module top level): even `--help` needs a GPU
app_launcher = AppLauncher(args_cli)        # <- runs at import

# AFTER: guard it in main() (like skrl_training.py already does)
def main():
    app_launcher = AppLauncher(args_cli)    # GPU only when actually run
# Acceptance: imports on CPU · --help exits pre-AppLauncher · argv preserved
#   · GPU launch + Hydra/MLflow side-effects unchanged · covered by a test
"""

C_FAILSAFE = """
# Fail-safe path gate: the required check ALWAYS runs and is never 'skipped'.
jobs:
  changes:                     # detect which areas moved (this job is tested)
    outputs: { rl: ..., il: ..., lock: ... }
  smoke-rl:
    needs: changes
    if: needs.changes.outputs.rl == 'true' || needs.changes.outputs.lock == 'true'
  pr-smoke-summary:            # the ONE required check for branch protection
    needs: [changes, smoke-rl, smoke-il]
    if: always()               # never 'skipped' -> a skip can't masquerade as green
    run: |                     # any lockfile change forces the heavy legs;
      [ "$rl" = success ] || [ "$rl_skipped_ok" ] || exit 1   # a wrongly-skipped leg FAILS
"""

C_PROTO = """
# EXECUTED inside nvcr.io/nvidia/isaac-lab:2.3.2 (amd64 emulated), CPU only:
$ docker run ... --entrypoint .../python3 isaac-lab:2.3.2 -c 'print(sys.version)'
  3.11.13                         # the real Isaac runtime

$ pip install .   # a dep with requires-python = ">=3.12"  (the #809 break)
  ERROR: Package requires a different Python: 3.11.13 not in '>=3.12'

# and against the repo's REAL training/rl lock, on the host:
$ uv lock --check --python 3.12
  error: ... incompatible with the project's requires-python `==3.11.*`
"""

# ----------------------------------------------------------------------------
SLIDES = [
    # ================= FRAME =================
    {"kind": "title", "title": "PR Regression Safety",
     "subtitle": "Why green CI is not \u201csafe to merge\u201d \u2014 and the phased gate that fixes it",
     "sub2": "Research findings · microsoft/physical-ai-toolchain · June 2026",
     "notes": "This repository has a dependency-regression problem its green pipeline cannot see. The remedy is not one large platform bet; it is four cheap controls that ship now and one funded gate that waits on a budget number. The next slide is the whole case in one statistic."},

    {"kind": "stat", "accent": RED, "title": "Green CI has missed every costly regression",
     "stat": "8  vs  0",
     "statcap": "Eight runtime regressions and test-integrity gaps reconstructed from this repo's own history \u2014 zero caught by the green, CPU-only pipeline.",
     "body": "- Most are runtime, GPU, or interpreter specific \u2014 what CPU CI never exercises\n- Two were caused by CI itself: path-filter bugs switched tests off for weeks\n- In this project a green check has repeatedly meant nothing was actually tested",
     "notes": "Eight distinct runtime regressions and test-integrity gaps were reconstructed from this project's history, and the green pipeline caught none of them. Most break on a real interpreter or a real GPU, which a CPU runner never touches. Two were caused by the pipeline itself, where a path filter quietly switched tests off for weeks. The decision this talk asks for follows directly from that zero."},

    {"kind": "deflist", "accent": RED, "title": "The eight, in one place",
     "caption": "Five named failures carry the argument; the full catalogue is in the appendix",
     "label_w": 3.3, "label_size": 13.5, "desc_size": 13,
     "rows": [
         ("#809 \u2014 interpreter ABI", "RL lock resolved for Python 3.12 against a 3.11 runtime \u2192 four cascading ABI failures"),
         ("#790 \u2014 LeRobot interpreter", "LeRobot needs Python \u2265 3.12 against an OSMO 3.11 runtime"),
         ("#958 \u2014 torch / CUDA", "a torch 2.10\u21922.11 security bump pulled CUDA 13 bindings \u2192 libcudart break; live desync today"),
         ("#691 / #547 \u2014 tests off", "path-filter bugs silently disabled fuzz, data-pipeline, and training tests for weeks"),
         ("churn", "starlette churned 0.52\u21921.0\u21921.3 across ~7 dependency PRs and a downgrade-then-rebump in ~12 days"),
     ],
     "notes": "These five carry the rest of the talk, so they are worth a name. Eight-oh-nine and seven-ninety are interpreter mismatches: a lock resolved for one Python version against a runtime built on another. Nine-fifty-eight is a torch security bump that dragged in an incompatible CUDA runtime, and it still ships today because the lock pins one version while the pipeline force-installs another. Six-ninety-one and five-forty-seven are the pipeline disabling its own tests. And starlette shows the churn. Hold these five; every later recommendation maps back to them."},

    {"kind": "bullets", "accent": BLUE, "title": "What this asks for",
     "body": "- Phase 0 \u2014 risk-aware Dependabot grouping        · config only · ~$0\n- Phase 1 \u2014 GPU-free smoke gate on every PR        · standard runners · ~$0\n- Phase 2 \u2014 safe automation: auto-merge + review  · standard runners · ~$0\n- Phase 3 \u2014 gated GPU end-to-end (the capstone)    · funded GPU compute\n- Evidence: repo history, configs, PRs, and an executed prototype \u2014 cited in the appendix",
     "notes": "The ask is four controls plus one capstone. Phases zero, one, and two are configuration and ordinary Actions runners \u2014 no Azure, no budget. Phase three is the only line that needs funded GPU compute, and it is the only one that can prove the GPU half of safe-to-merge. Each phase stands alone and reduces regressions on its own, so this is adopted incrementally, not as a single bet. Every claim that follows is grounded in the repo's own history and a prototype we ran."},

    # ================= CURRENT STATE (compact) =================
    {"kind": "deflist", "accent": BLUE, "title": "The stack under test \u2014 why this repo is hard",
     "caption": "CI/CD generalists meet the robotics runtime: these concepts drive every later recommendation",
     "label_w": 3.4, "label_size": 13.5, "desc_size": 13,
     "rows": [
         ("Isaac Lab", "GPU simulator (needs Vulkan); ships its own Python 3.11 runtime"),
         ("CUDA / driver ABI", "torch and CUDA wheels are compiled contracts \u2014 they must match the GPU driver"),
         ("MIG", "one datacentre GPU sliced into isolated instances; a config, not a library"),
         ("AzureML / OSMO", "submit-and-poll: CI sends a job spec, a scale-from-zero GPU pool runs it"),
         ("uv / uv.lock", "fast resolver plus an exact pinned graph, one per subproject"),
     ],
     "notes": "This audience knows CI but not necessarily this runtime, so five terms first. Isaac Lab is a GPU simulator that needs Vulkan and ships its own Python three-eleven. CUDA and torch wheels are compiled contracts that must match the driver, which is why a version bump can break on device and nowhere else. MIG slices one GPU into isolated instances. AzureML and OSMO take a submitted job and run it on a pool that scales from zero. And uv produces an exact pinned lock per subproject. Every recommendation later turns on one of these five."},

    {"kind": "code", "accent": BLUE, "title": "Dependency intake today",
     "caption": "21 ecosystem blocks (9 uv · 3 npm · 4 Terraform · 3 Docker · 1 Go · 1 Actions), every group a wildcard",
     "file": ".github/dependabot.yml", "code": C_DEPENDABOT_TODAY,
     "notes": "Dependencies arrive through twenty-one Dependabot blocks, and every group is a single wildcard catch-all, so nothing is split by risk: a harmless patch and a CUDA-breaking major look identical. The ignore-pins, like marshmallow here, were all added reactively, after something already broke. This is the intake that feeds the regressions."},

    {"kind": "deflist", "accent": BLUE, "title": "21 contexts = several independent runtimes",
     "caption": "Not one app with one lock \u2014 the blast radius of a bump is wildly uneven",
     "label_w": 3.0, "label_size": 13.5, "desc_size": 12.5,
     "rows": [
         ("Training · RL", "Isaac Lab SKRL/RSL-RL (Py 3.11, numpy 1.26); AzureML + OSMO GPU jobs"),
         ("Training · IL", "LeRobot ACT/Diffusion; full AzureML command-job + pipeline"),
         ("Evaluation · SIL", "ONNX / Torch inference and the eval container image"),
         ("Dataviewer", "FastAPI backend + React 19 frontend + 2 Docker images"),
         ("Infrastructure", "4 Terraform roots (AKS, DNS, VPN, automation) + Go contract tests"),
     ],
     "notes": "Those twenty-one blocks are not one application with one lockfile; they are several independent runtimes sharing a repository. Reinforcement learning on Isaac Lab pinned to Python three-eleven. Imitation learning on LeRobot. Evaluation and its container. A full web application. Four Terraform roots. The same version bump can be harmless in the React app and fatal in the Isaac training image \u2014 which is exactly why blind, uniform intake is dangerous here."},

    {"kind": "code", "accent": BLUE, "title": "CI and automation today",
     "caption": "All test CI is CPU-only; the torch pin desyncs from the lock; one advisory agent, read-only",
     "file": ".github/workflows/pytest-training.yml", "code": C_CI_TODAY,
     "notes": "Two facts complete the current picture. First, every test job runs on a standard CPU runner with no GPU, and it force-installs a torch version that disagrees with the committed lock \u2014 a live desync that ships today. Second, the only agentic workflow is an advisory Dependabot reviewer: a maintainer types a slash command, it reads, it comments, it never writes. So today's automation is one read-only adviser on top of a pipeline that never touches a GPU."},

    # ================= THE BRIDGE: FAILURE MAP =================
    {"kind": "matrix", "accent": BLUE, "title": "The failure map",
     "caption": "Each incident against the phase that catches it \u2014 the spine of the plan",
     "label_w": 3.7, "label_size": 13,
     "cols": ["Today", "P0 group", "P1 smoke", "P2 auto", "P3 GPU"],
     "rows": [
         {"label": "#809 interpreter/ABI", "sub": "Py3.12 lock vs 3.11 runtime", "cells": ["x", "n", "y", "n", "n"]},
         {"label": "#790 LeRobot Py\u22653.12", "sub": "vs OSMO 3.11 runtime", "cells": ["x", "n", "~", "n", "n"]},
         {"label": "#958 torch / CUDA", "sub": "resolution vs device ABI", "cells": ["x", "~", "~", "n", "y"]},
         {"label": "#691/#547 tests off", "sub": "path-filter silently skipped", "cells": ["x", "n", "y", "n", "n"]},
         {"label": "churn · starlette \u00d77", "sub": "noise / wasted reviews", "cells": ["x", "y", "n", "y", "n"]},
     ],
     "legend": "\u2713 caught/prevented   \u223c partial \u2014 reduces risk   \u2013 n/a   \u2717 missed today.   #958 splits: \u223c resolution caught early; \u2713 the device-ABI break needs Phase 3.",
     "notes": "This is the map the whole plan hangs on. Read each row to the first column that catches it. The interpreter breaks, eight-oh-nine and seven-ninety, are caught by the Phase-one smoke gate, on a CPU. The integrity failures, six-ninety-one and five-forty-seven, are caught by a fail-safe required check, also Phase one. Churn is absorbed by Phase-zero grouping and Phase-two auto-merge. And nine-fifty-eight splits in two: the cheap phases catch the dependency-resolution half early, but the actual device-ABI break can only be proven on a GPU, in Phase three. That split is the honest reason the capstone earns funding."},

    # ================= PHASE 0 =================
    {"kind": "section", "part": "Phase 0", "title": "Dependency intake",
     "sub": "From blind wildcard intake to risk-aware grouping \u2014 config only, ~$0",
     "notes": "Phase zero changes how dependencies arrive. It is pure configuration and ships in an afternoon."},

    {"kind": "bullets", "accent": RED, "title": "Intake has no risk signal",
     "body": "- 21 ecosystem blocks, every one a wildcard catch-all \u2014 no split by risk\n- A harmless patch and a CUDA-breaking major are batched identically\n- ~7 ignore-pins added only after a breakage (torch, numpy, marshmallow\u2026)\n- No stability window: a bump can open the day it is published",
     "notes": "Today every block batches by ecosystem, not by risk, so a patch and a major land in the same pull request and the same review. The seven ignore-pins were all reactive \u2014 added after a break, never before. And there is no cooldown, so a freshly published version can open a pull request the same day. The fix is to give intake the risk signal it lacks."},

    {"kind": "code", "accent": PURPLE, "title": "What others do \u2014 group by risk, add a cooldown",
     "caption": "Real, copyable config: vercel/ai splits prod vs dev; huggingface/transformers adds a window",
     "file": "vercel/ai  ·  huggingface/transformers", "code": C_OTHERS_GROUPING,
     "notes": "The pattern to copy is settled. Vercel's AI SDK splits production from development dependencies and batches minor and patch together. HuggingFace transformers adds a seven-day cooldown, a stability window before a bump opens. Both are real configuration files, not advice \u2014 we can lift them directly."},

    {"kind": "codecompare", "accent": GREEN, "title": "Recommendation \u2014 split by risk, keep security fast",
     "caption": "Batch the safe, isolate majors, add a window \u2014 and never batch security",
     "left_head": "Today \u2014 wildcard catch-all", "left_accent": RED, "left_code": CMP_DB_LEFT,
     "right_head": "Proposed \u2014 risk split + cooldown", "right_accent": GREEN, "right_code": CMP_DB_RIGHT,
     "notes": "Side by side: on the left, one wildcard group per ecosystem, patches and majors treated alike. On the right, update types are split so patches and minors batch into one auto-mergeable pull request while majors are isolated for review, a seven-day cooldown is added, and \u2014 the firm rule \u2014 security updates stay ungrouped and fast-tracked, never held in a weekly batch. This is configuration only; it removes the noise that hides the dangerous bump."},

    {"kind": "deflist", "accent": AMBER, "title": "Renovate \u2014 a scoped spike, not a switch",
     "caption": "One real residual gap; weigh it on evidence (full adoption data in the appendix)",
     "label_w": 3.4, "label_size": 13.5, "desc_size": 13,
     "rows": [
         ("The gap", "Dependabot groups are per-ecosystem \u2014 still 4+ PRs/cycle; no one-config view"),
         ("Not the gap", "uv support \u2014 Dependabot has it since 2025 and this repo already uses it"),
         ("The cost", "the Mend App needs org approval; renovatebot/github-action avoids it entirely"),
         ("The decision", "time-boxed spike via the Action; switch only if PR volume drops without losing the security lane"),
     ],
     "notes": "One alternative deserves a place, not a section. Renovate's single real edge here is cross-ecosystem grouping: one config across npm, Python, Terraform, and Go, where Dependabot needs a block each. What is not the edge is uv \u2014 Dependabot has supported it since twenty-twenty-five and this repo relies on it. The friction is organizational: the hosted app needs approval, but a self-hosted Action sidesteps that. So the recommendation is a time-boxed spike that switches only if it measurably cuts pull-request volume without weakening the security lane. The adoption evidence is in the appendix."},

    # ================= PHASE 1 =================
    {"kind": "section", "part": "Phase 1", "title": "GPU-free smoke gate",
     "sub": "Catch the resolution, import, and interpreter breaks on every PR \u2014 ~$0",
     "notes": "Phase one is the cheap gate that catches the expensive interpreter class, with no GPU and no Azure."},

    {"kind": "bullets", "accent": RED, "title": "A green check tests nothing real",
     "body": "- All test CI is CPU-only ubuntu-latest \u2014 no GPU, no Isaac, no real runtime image\n- The interpreter and ABI breaks fail on the real runtime, which CI never loads\n- Path-filter bugs (#691, #547) switched tests off for weeks \u2014 still green\n- So the gate must run inside the real image, not a generic runner",
     "notes": "The pipeline's blind spot is structural. It runs on a generic Ubuntu image with a generic Python, while the breaks that hurt happen on Isaac's own three-eleven runtime, which CI never loads. And when a path filter misfired, the pipeline reported green while testing nothing. The conclusion writes the design: to catch these, the smoke gate has to run inside the actual runtime image."},

    {"kind": "twocol", "accent": BLUE, "title": "Two depths: Tier 0 and Tier 1",
     "left_head": "Tier 0 \u2014 venv, seconds, every PR", "left_accent": GREEN,
     "left_body": "- `uv lock --check` \u2014 resolution drift\n- import in a CPU venv + `--help`\n- YAML schema-validate, `shellcheck`\n- Cheap; runs on EVERY PR\n- Caveat: CPU wheels \u2260 the production CUDA graph",
     "right_head": "Tier 1 \u2014 inside the real image, minutes", "right_accent": BLUE,
     "right_body": "- `docker run` the ACTUAL runtime image\n- reinstall the PR's lock as prod does\n- import on the real interpreter (Isaac = 3.11)\n- Catches #809, probably #790 \u2014 deterministically\n- Path-gated; bounded by disk, not capability",
     "notes": "CPU smoke has two depths, and naming them prevents a costly confusion. Tier zero runs in a plain virtual environment in seconds \u2014 lock-check, import, schema-validate \u2014 cheap enough for every pull request. But it deliberately installs CPU wheels, so it is checking a different dependency graph than production's CUDA one; it catches import and resolution errors, not production resolution. Tier one is the one that mirrors production: it pulls the real image and reinstalls the pull request's lock exactly as the training job does, on the real interpreter. That tier deterministically catches the interpreter class, eight-oh-nine and probably seven-ninety. Its limit is disk, not capability."},

    {"kind": "code", "accent": GREEN, "title": "Tier 1 \u2014 import inside the real image",
     "caption": "The recipe that catches the #809 class \u2014 no GPU; it fails at import",
     "file": "Proposed: isaac-import-smoke.sh", "code": C_TIER1, "code_size": 12,
     "notes": "Concretely, for the hardest environment: pull the real Isaac image and reinstall the pull request's lock with no-deps, exactly as the training job does, on the real three-eleven interpreter. That install step is the circuit breaker for the interpreter and marker class \u2014 eight-oh-nine was a lock resolved for three-twelve, and it fails right here, before anything imports, on a CPU agent. The import-check mode is the follow-on net: it runs the real launcher far enough to load the Isaac, SKRL, and gym graph, then stops before AppLauncher, the only GPU step \u2014 catching a package that installs but will not load on the runtime. Neither step needs a GPU."},

    {"kind": "code", "accent": GREEN, "title": "We ran it \u2014 it catches #809 on CPU",
     "caption": "Executed this session inside the actual Isaac image, CPU only",
     "file": "prototype result (this session)", "code": C_PROTO, "code_size": 12,
     "notes": "This is not a claim on a slide; we ran it. Inside the actual Isaac image, the runtime interpreter is Python three-eleven-point-one-three. Install a dependency that requires three-twelve \u2014 the exact shape of eight-oh-nine \u2014 and the runtime rejects it at install time, on the CPU. The same mismatch fails a lock-check against the repo's real training lock. The interpreter class breaks before any GPU compute, so a CPU agent is enough to catch it. The harness is saved with this session."},

    {"kind": "code", "accent": GREEN, "title": "Recommendation \u2014 Phase 1a + 1b",
     "caption": "1a Tier 0 every PR · 1b Tier 1 real-image, path-gated · one fail-safe required check",
     "file": "Proposed: .github/workflows/smoke-cpu.yml", "code": C_SMOKE, "code_size": 12.5,
     "notes": "The recommendation is two named jobs. Phase one-a is Tier zero on every pull request: lock-check, a CPU-torch install so the heavy CUDA build does not block it, import smoke, a config-preview of the submit scripts, and the evaluation-image build. Phase one-b is Tier one, the real-image import, path-gated to the area that changed. Both sit behind one fail-safe required check. But state the limit plainly: this catches install, import, and interpreter drift. It cannot prove CUDA, Vulkan, MIG, or a real training loop \u2014 and that limit is exactly what Phase three exists to close."},

    # ================= PHASE 2 =================
    {"kind": "section", "part": "Phase 2", "title": "Safe automation",
     "sub": "Reclaim reviewer time without lowering the bar \u2014 ~$0",
     "notes": "Phase two removes human toil from the safe path without weakening any gate. It auto-merges only the bumps that are provably trivial, and leaves everything riskier to scoped manual review."},

    {"kind": "bullets", "accent": RED, "title": "Every low-risk bump waits on a human",
     "body": "- Dependabot cannot merge its own PRs \u2014 trivial patches queue for a click\n- High-risk and low-risk updates get identical, manual handling\n- ~24 PRs/week of reviewer toil, most of it trivial",
     "notes": "The toil is concentrated in the safe path. Dependabot cannot merge its own pull requests, so every trivial patch waits for a maintainer's click, and high-risk and low-risk updates get the same manual handling \u2014 roughly twenty-four pull requests a week, most of them trivial. That is toil, not safety, and it is fixable without touching the safety bar."},

    {"kind": "code", "accent": GREEN, "title": "Recommendation \u2014 auto-merge, scoped tight",
     "caption": "`fetch-metadata` + `gh pr merge --auto` \u2014 patch-only, no runtime/GPU packages, no security",
     "file": "Proposed: auto-merge workflow", "code": C_AUTOMERGE,
     "notes": "Auto-merge the trivially safe, and only that \u2014 no agent, no inference. Dependabot's fetch-metadata action reads the update type without running the pull request's code; for a development patch it enables auto-merge, which waits for the required checks. The natural objection \u2014 won't this cause incidents \u2014 is answered by scope: patch-only at first, development and docs and actions only, never a runtime or GPU package, never a security pull request, required checks green, and an instant-revert playbook. Everything riskier stays in scoped manual review."},

    # ================= PHASE 3 =================
    {"kind": "section", "part": "Phase 3", "title": "Gated GPU end-to-end \u2014 the capstone",
     "sub": "The only tier that proves the GPU runtime \u2014 when funded",
     "notes": "Phase three is the capstone: the only tier that can assert safe-to-merge on a GPU. Its blocker is a budget number, not a design."},

    {"kind": "bullets", "accent": RED, "title": "The GPU half is never proven",
     "body": "- Safe-to-merge cannot be asserted \u2014 nothing exercises the GPU runtime\n- Only real hardware catches CUDA / driver / Isaac Vulkan / MIG breaks\n- #958's device-ABI half passes every cheap tier, then breaks on the GPU\n- The blocker is funding: a dedicated, budget-capped GPU subscription",
     "notes": "The cheap phases close the dependency and interpreter classes, but one class remains open. Only real hardware catches CUDA and driver breaks, Isaac's Vulkan rendering, and MIG. Recall the failure map: nine-fifty-eight's resolution half is caught early, but its device-ABI half passes every CPU tier and only fails on the GPU. Proving that half is what Phase three buys, and the only thing standing in the way is a funded, capped GPU subscription."},

    {"kind": "code", "accent": PURPLE, "title": "What others do \u2014 NeMo gates the GPU run",
     "caption": "Queue/human approval + fork mirroring \u2014 no pull_request_target",
     "file": "NVIDIA-NeMo/NeMo · cicd-main.yml", "code": NEMO_GATE, "code_size": 12,
     "notes": "NeMo gates the expensive half cleanly. Every GPU job depends on a wait-in-queue job bound to a GitHub Environment, so nothing on a GPU starts until a reviewer or a queue bot approves it. And to run fork code safely, NeMo avoids the dangerous base-context trigger entirely \u2014 a bot mirrors fork pull requests onto internal branches, so untrusted code never executes with secrets in scope. Approval gate plus sandboxed execution: that is the shape we copy."},

    {"kind": "code", "accent": GREEN, "title": "Recommendation \u2014 the gated GPU job",
     "caption": "Two jobs: PR code renders a spec with no secrets; trusted base code submits after approval",
     "file": "Proposed: gated GPU e2e", "code": C_GPU_E2E, "code_size": 11.5,
     "notes": "The safety hinge is that contributor code never runs on the runner that holds the cloud token. Job A runs on the plain pull-request event \u2014 read-only, no secrets \u2014 and only renders a constrained job spec. Job B runs after an approving review, checks out the trusted base workflow rather than the pull request, validates the spec against an allowlist, mints an OIDC token through an Environment gate, and submits. The contributor's code runs inside the GPU pool, never on the privileged runner. That is the difference between a gate and a leak."},

    {"kind": "deflist", "accent": AMBER, "title": "What funding buys",
     "caption": "Illustrative figures \u2014 a budget-capped subscription, not a blank cheque (confidence: low on exact $)",
     "label_w": 3.0, "label_size": 13.5, "desc_size": 13,
     "rows": [
         ("Per gated run", "~$3\u20138 GPU-hour \u00d7 ~0.3\u20131.0 hr; scale-from-zero, idle \u2248 $0"),
         ("Frequency", "only on maintainer approval \u2014 ~5\u201315 runs/week, not per-PR"),
         ("Caps", "60-min timeout/run · concurrency 1 · monthly budget cap"),
         ("Scenarios", "low \u2248 $60/mo · expected \u2248 $150/mo · spike \u2248 $400/mo"),
         ("Buys", "the only proof of CUDA / Vulkan / MIG / training-loop safety"),
         ("Unfunded risk", "GPU-only regressions (e.g. #958 device half) keep merging blind"),
     ],
     "notes": "A capstone needs a number, so here is an honest, capped estimate \u2014 and I label the dollar figures low-confidence. Each gated run is short and the pool idles at near-zero cost; runs happen only on approval, not per pull request, so think five to fifteen a week. With a one-hour timeout, single concurrency, and a monthly cap, the expected spend is on the order of a hundred and fifty dollars a month, a few hundred at peak. What that buys is the only proof of GPU-runtime safety there is. What it costs to skip is that GPU-only regressions keep merging blind."},

    # ================= CLOSE =================
    {"kind": "section", "part": "The decision", "title": "Roadmap and the ask",
     "sub": "What ships now, what waits on funding, and what we need approved today",
     "notes": "Bring it together: the sequence, and the specific decisions requested."},

    {"kind": "phases", "accent": GREEN, "title": "Roadmap \u2014 ship now vs funded",
     "phases": [
         {"tag": "Phase 0", "when": "now · hours", "accent": GREEN, "cost": "$0",
          "head": "Risk-aware intake",
          "items": "group by update-type · cooldown · security stays a fast lane"},
         {"tag": "Phase 1", "when": "now · days", "accent": BLUE, "cost": "$0",
          "head": "GPU-free smoke gate",
          "items": "1a Tier 0 every PR · 1b Tier 1 real-image, path-gated · fail-safe check"},
         {"tag": "Phase 2", "when": "now · days", "accent": BLUE, "cost": "$0",
          "head": "Safe automation",
          "items": "patch-only auto-merge on green · scoped manual review for the rest"},
         {"tag": "Phase 3", "when": "when funded", "accent": AMBER, "cost": "GPU $",
          "head": "Gated GPU e2e",
          "items": "approval-gated, two-job OIDC submit-and-poll to scale-from-zero pool"},
         {"tag": "Spike", "when": "parallel", "accent": PURPLE, "cost": "$0",
          "head": "Renovate evaluation",
          "items": "github-action, time-boxed; switch only if PR volume drops"},
     ],
     "notes": "Everything but Phase three runs on ordinary runners and ships now; Phase three waits on the GPU budget. The order is deliberate: intake first to cut noise, then the smoke gate to catch the interpreter class, then automation to remove toil, and the funded capstone last. The Renovate spike runs in parallel and is reversible. Funding does not gate progress \u2014 only the final proof."},

    {"kind": "bullets", "accent": BLUE, "title": "Decision requested today",
     "body": "- Approve the Phase 0 `dependabot.yml` change (grouping + cooldown)\n- Approve the Phase 1a Tier-0 required check on every PR\n- Approve a Phase 1b Tier-1 real-image spike with a runtime cap\n- Approve a Phase 2 patch-only auto-merge pilot (dev/docs/actions)\n- Approve a time-boxed Renovate spike via github-action\n- Defer Phase 3 pending a GPU budget number \u2014 design is settled\n- Out of band, now: fix the live torch 2.10 / 2.11 desync",
     "notes": "So, concretely, seven decisions. Approve the configuration grouping. Approve the Tier-zero required check on every pull request. Approve a capped Tier-one real-image spike. Approve a patch-only auto-merge pilot scoped to development, docs, and actions. Approve a time-boxed Renovate spike through the Action. Defer Phase three until there is a GPU budget number \u2014 its design is settled and waiting. And separately from all of it, fix the live torch desync now; that one is not a decision, it is a bug."},

    {"kind": "section", "part": "Discussion", "title": "Questions",
     "sub": "Appendix follows: primers, prototype detail, costs, and alternatives",
     "notes": "That is the case: the regressions are real and runtime-specific, four controls ship now for almost nothing, and the GPU capstone is designed and waiting on a budget number. The appendix has the primers, the prototype detail, the economics, and the rejected alternatives. I will stop there."},

    # ================= APPENDIX =================
    {"kind": "section", "part": "Appendix", "title": "Reference and backup",
     "sub": "Tool primers, prototype mechanics, economics, and alternatives",
     "notes": "Reference material for questions: the tool primers, the deeper smoke mechanics, the cost model, and the alternatives we weighed."},

    {"kind": "primer", "accent": BLUE, "title": "Primer \u2014 Dependabot",
     "body": "Dependabot runs TWO streams: scheduled VERSION updates and advisory-driven SECURITY updates \u2014 never mix them. `groups:` batches, `ignore:` pins, `open-pull-requests-limit` caps noise, `cooldown` adds a stability window. It regenerates lockfiles natively.",
     "terms": "version vs security, group, ignore, cooldown, PR limit, lockfile",
     "file": ".github/dependabot.yml", "code": P_DEPENDABOT,
     "notes": "Dependabot runs two separate streams: version updates that keep packages current, and security updates triggered by advisories, which must never be batched behind the version stream. Groups batch, ignore records deliberate pins, the limit caps noise, and a cooldown adds a stability window. It regenerates lockfiles natively."},

    {"kind": "primer", "accent": BLUE, "title": "Primer \u2014 uv and lockfiles",
     "body": "`pyproject.toml` is the human-authored manifest (PEP 621). `uv.lock` is the resolver's exact output \u2014 pinned versions, hashes, platform markers. A PR can edit the manifest but forget the lock, so this repo enforces `uv lock --check` as a CI gate.",
     "terms": "pyproject.toml, PEP 621, uv, uv.lock, resolver, lock drift",
     "file": "pyproject.toml + uv.lock", "code": P_UVLOCK,
     "notes": "The manifest lists direct dependencies and the required Python version; the lock is the resolver's exact output, with hashes and markers. The danger is a pull request that edits the manifest but forgets the lock, so CI installs a different graph. A lock-check gate prevents that drift."},

    {"kind": "primer", "accent": RED, "title": "Primer \u2014 security advisories (GHSA)",
     "body": "A GHSA records a vulnerable package, its affected and patched versions, and a CVSS severity, usually linked to a CVE. When a vulnerable dependency is in your graph, Dependabot opens a security PR to the minimum patched version. These are fast-tracked by severity \u2014 never batched or held in a cooldown.",
     "terms": "GHSA, CVE, CVSS, severity, advisory, patched version",
     "file": "a GHSA, conceptually", "code": P_GHSA,
     "notes": "A GitHub Security Advisory records a vulnerable package, its patched version, and a severity, usually tied to a CVE. When such a package is in your graph, Dependabot opens a security pull request to the minimum patched version. Because these close known exposure, they are fast-tracked by severity, never batched. That separate fast lane recurs throughout the recommendations."},

    {"kind": "primer", "accent": PURPLE, "title": "Primer \u2014 agentic workflows (gh-aw)",
     "body": "gh-aw workflows are markdown that compiles to a normal Actions workflow (`.lock.yml`). The frontmatter picks an AI `engine`, a trigger, and read-only `tools`. The agent CANNOT write directly \u2014 only through declared `safe-outputs` (add-comment, create-issue\u2026). That read-only-plus-safe-outputs model is the whole safety story.",
     "terms": "gh-aw, engine, trigger, safe-outputs, lock file, read-only agent",
     "file": ".github/workflows/*.md", "code": P_GHAW,
     "notes": "Agentic workflows are a markdown file that compiles into a normal Actions workflow. The frontmatter picks an engine, a trigger, and read-only tools. The agent cannot write anything directly; it acts only through declared safe-outputs, like adding a comment or creating an issue. That model is why the repository's existing read-only reviewer can be trusted to post an advisory comment on a dependency pull request."},

    {"kind": "primer", "accent": GREEN, "title": "Primer \u2014 CI gating tiers",
     "body": "Cheap checks (lint, spell, lock-consistency) run on every PR; expensive checks run only when their area changed or a human releases them. This repo computes path booleans in one `changes` job and aggregates into ONE stable required check. The trap: a naive top-level `paths:` filter can leave a required check skipped \u2014 green having tested nothing.",
     "terms": "cheap vs expensive, path gate, required check, branch protection, aggregator",
     "file": ".github/workflows/pr-validation.yml", "code": P_GATING,
     "notes": "Good CI is tiered: cheap checks on every pull request, expensive checks only when their area changed. This repo computes path booleans in one job and aggregates into a single required check. The trap, which bit this repo twice, is a naive paths filter that leaves a required check skipped, so a pull request looks green having tested nothing. The aggregator must be fail-safe."},

    {"kind": "primer", "accent": GREEN, "title": "Primer \u2014 running untrusted PR code",
     "body": "On `pull_request`, fork PRs get a read-only token and NO secrets \u2014 safe to build untrusted code. On `pull_request_target` the job runs in the base context WITH secrets; checking out the PR head there is the classic 'pwn request'. Gate real cloud access behind an Environment, and use OIDC with a tight federated policy.",
     "terms": "fork PR, pull_request vs pull_request_target, pwn request, Environment, OIDC",
     "file": "the safe pattern", "code": P_UNTRUSTED,
     "notes": "A fork pull request is untrusted code. On the plain event it gets a read-only token and no secrets, so building it is safe. On the base-context event it has secrets, and running the contributor's head there is the classic pwn request. So gate genuine cloud access behind an Environment, and remember that the OIDC token is only as safe as the federated policy that pins which repo and environment may mint it."},

    {"kind": "glossary", "accent": BLUE, "title": "Glossary",
     "rows": [
         ("Dependabot", "GitHub's native dependency-update bot"),
         ("Renovate", "third-party update bot; cross-ecosystem config"),
         ("GHSA", "GitHub Security Advisory for a vulnerability"),
         ("CVSS", "standard 0-10 vulnerability severity score"),
         ("lockfile", "pinned exact resolved dependency graph"),
         ("uv", "fast Python resolver; reads pyproject, writes uv.lock"),
         ("PEP 621", "standard [project] metadata in pyproject.toml"),
         ("semver", "patch / minor / major compatibility levels"),
         ("required check", "status check branch protection insists on"),
         ("OIDC", "short-lived federated cloud login; no stored secret"),
         ("Environment", "deploy target w/ required reviewers + secrets"),
         ("pull_request_target", "base-context trigger WITH secrets (risky)"),
         ("MIG", "one datacentre GPU sliced into isolated instances"),
         ("Vulkan", "graphics API Isaac Sim needs to render"),
         ("ABI", "compiled binary contract; mismatch crashes at runtime"),
         ("submit-and-poll", "CI submits a job to a GPU pool, then waits"),
         ("safe-outputs", "the only channel a gh-aw agent may write through"),
         ("smoke test", "tiny fast check that the critical path works"),
     ],
     "notes": "A glossary to leave up for reference \u2014 the terms used through the talk, each in a line. Not read aloud."},

    {"kind": "code", "accent": BLUE, "title": "These are production contracts, not toy configs",
     "caption": "e.g. the AzureML job contract for an Isaac Lab GPU training container",
     "file": "training/rl/workflows/azureml/train.yaml", "code": C_AML_ENV,
     "notes": "Two surfaces can break, not one. This is the AzureML job contract for an Isaac training container \u2014 the runtime wrapper, the mandatory EULA, the checkpoint behavior. A dependency bump can break the container's runtime packaging, caught by import smoke, or the submission contract that renders this YAML, caught by config-preview, or on-device execution, caught only by the GPU tier. Different tests catch each; that is why the gate is layered."},

    {"kind": "code", "accent": BLUE, "title": "Tier 1 \u2014 one image per job, disk-gated",
     "caption": "Disk is the binding constraint, not capability",
     "file": "smoke-environments.yml", "code": C_TIER_MATRIX, "code_size": 12,
     "notes": "Tier one's honest constraint is disk. Isaac unpacks to around twenty gigabytes, the PyTorch image another fifteen, the eval image seven to nine \u2014 they cannot co-reside even after a free-disk step. So it is one image per matrix job, pruned between legs, path-gated to the environment whose dependencies actually moved. The secondary cost, pull time, a nightly cache warm-up absorbs."},

    {"kind": "code", "accent": GREEN, "title": "A small refactor widens the Isaac smoke",
     "caption": "Move AppLauncher into main() \u2014 like skrl already does (with real acceptance criteria)",
     "file": "training/rl/scripts/rsl_rl/train.py", "code": C_RSL_REFACTOR, "code_size": 12.5,
     "notes": "One small repository change deepens the Isaac smoke. Today the RSL launcher builds the Isaac AppLauncher at module top level, so the file cannot be imported or show help without a GPU. Moving that call into a main function, as the SKRL script already does, makes the module importable on a CPU agent. It is small, but it is not zero: it needs acceptance criteria \u2014 imports on CPU, help exits before the launcher, argument order preserved, GPU behavior unchanged, and a test to hold all of that."},

    {"kind": "codecompare", "accent": GREEN, "title": "Phase 2 detail \u2014 reviewer waits for green CI",
     "caption": "Run after CI, skip doomed PRs, keep one updating comment",
     "left_head": "Today \u2014 slash_command", "left_accent": RED, "left_code": CMP_REV_LEFT,
     "right_head": "Proposed \u2014 workflow_run", "right_accent": GREEN, "right_code": CMP_REV_RIGHT,
     "notes": "The reviewer-cost fix in detail. Today a slash command can run before CI and re-comments on every rebase. Proposed: trigger on workflow-run when the pipeline completes, skip when checks are failing so no tokens go to a doomed pull request, and hide older comments for one updating thread. Keep the slash command as a manual override."},

    {"kind": "code", "accent": GREEN, "title": "Smoke operating cost and the fail-safe gate",
     "caption": "Who owns it, what it costs to run, and why a skip can't pass as green",
     "file": "Proposed: pr-smoke-summary", "code": C_FAILSAFE, "code_size": 12,
     "notes": "A new gate has running costs, so own them explicitly. The smoke tier's runtime is minutes; its known flakes are image-pull timeouts and free-disk fragility, triaged by a re-run and a cache; an owner watches schema drift as images change. And the fail-safe pattern is the heart of it: the required summary always runs, never reports skipped, and a wrongly-skipped heavy leg fails the check rather than passing silently \u2014 which is exactly what bit this repo in six-ninety-one and five-forty-seven."},

    {"kind": "deflist", "accent": AMBER, "title": "Anticipated objections",
     "label_w": 4.2, "label_size": 13, "desc_size": 12.5,
     "rows": [
         ("Won't auto-merge cause incidents?", "patch-only, dev/docs/actions, no runtime/GPU pkgs, no security batch, checks green, instant revert"),
         ("Why not just pin Python everywhere?", "necessary but insufficient \u2014 pins don't exercise real-image installs, transitive ABI, or CUDA/MIG"),
         ("Why not replace Dependabot now?", "native grouping covers most of it; the Renovate App is niche in MSFT OSS \u2014 spike first"),
         ("Why not GPU on every PR?", "cost, plus running fork code on a GPU runner; gate + submit-and-poll instead"),
         ("Is emulated-amd64 proof representative?", "enough for interpreter/marker breaks; final confidence needs a native amd64 runner"),
     ],
     "notes": "The objections a skeptical maintainer will raise, answered. Auto-merge is safe because it is scoped to patches in non-runtime areas with an instant revert. Pinning Python is necessary but not sufficient \u2014 it does not exercise a real image install or device execution. Replacing Dependabot now is premature when grouping is native and Renovate is a minority tool here. GPU on every pull request is too costly and unsafe for forks. And the prototype, run under emulation, is enough to prove the interpreter class, though a native runner would harden the final confidence."},

    {"kind": "deflist", "accent": BLUE, "title": "Economics \u2014 the toil being priced out",
     "caption": "Order-of-magnitude, to compare against the status quo (confidence: moderate)",
     "label_w": 3.4, "label_size": 13.5, "desc_size": 13,
     "rows": [
         ("Volume", "~24 dependency PRs/week (~350 opened, ~216 merged all-time)"),
         ("Reviewer toil", "~24 PRs \u00d7 a few minutes triage + rebase comments each week"),
         ("Phase 0+2 saves", "batching + patch auto-merge removes most trivial PRs from the queue"),
         ("Status quo cost", "~8 runtime incidents over the window; mean time-to-diagnose in hours"),
     ],
     "notes": "The case for the cheap phases is also economic. Two dependency pull requests a day, most trivial, each costing reviewer minutes. Batching and patch auto-merge take most of that queue away. Set against the status quo \u2014 eight runtime incidents over the window, each taking hours to diagnose \u2014 the configuration phases pay for themselves immediately, before any GPU spend."},

    {"kind": "code", "accent": AMBER, "title": "Renovate \u2014 adoption across Microsoft OSS",
     "caption": "We checked directly \u2014 it shapes the approval friction",
     "file": "evidence: Sourcegraph + file fetches", "code": RENOVATE_ADOPTION, "code_size": 12,
     "notes": "Because adoption determines approval friction, we measured it. Dependabot is the de-facto standard across Microsoft open source. Renovate appears in roughly nineteen org repositories, mostly one Visual Studio team sharing a preset; one in Azure, about nine in dotnet, zero in the GitHub org, and the open-source program page names only GitHub-native features. So the hosted app is a minority, team-scoped path \u2014 but the self-hosted Action sidesteps the approval entirely."},

    {"kind": "code", "accent": GREEN, "title": "Renovate \u2014 the scoped spike config",
     "caption": "Run via renovatebot/github-action; decide on PR-volume merits",
     "file": "Proposed (spike): renovate.json", "code": C_RENOVATE,
     "notes": "If the spike runs, this is its shape: one config across ecosystems, a stability window, auto-merge for minor and patch, and the torch pin preserved. Run through the Action, not the app, so there is no approval barrier. Auto-detection handles our ecosystems; only the custom pins and groups need translating, a few hours of work. Then decide on the merits \u2014 does it cut pull-request volume without losing the security lane."},

    {"kind": "bullets", "accent": AMBER, "title": "Alternatives considered and rejected",
     "body": "- A custom bot replacing Dependabot \u2014 reinvents native grouping; high upkeep\n- Immediate Renovate via the Mend App \u2014 niche in MSFT OSS; approval friction\n- pull_request_target + PR-head checkout for fork creds \u2014 the classic pwn request\n- GPU on every PR / self-hosted runner running PR code \u2014 too costly and risky unfunded\n- Pin Python everywhere and stop \u2014 necessary but doesn't exercise real installs or device ABI",
     "notes": "For honesty, the paths rejected and why. A custom bot reinvents grouping that is now native. Migrating straight to the Renovate app carries approval friction for a minority tool. Giving forks credentials through the base-context trigger is the pwn request. Running GPU on every pull request, or letting a runner execute contributor code, is too costly and risky unfunded. And pinning Python everywhere helps but does not exercise a real image install or device execution. Each shares one flaw: it buys control by adding risk or upkeep."},

    {"kind": "bullets", "accent": BLUE, "title": "Mandate and method",
     "body": "- Maintainers' ask: \"solve dependabot at the root, and gate safe merges\"\n- Six parallel research threads, each a cited evidence file\n- Grounded in the repo's git history, configs, PRs, and primary upstream sources\n- Plus an executed CPU prototype inside the real Isaac image (this session)\n- Full research: .copilot-tracking/research/2026-06-19/",
     "notes": "Finally, provenance. The maintainers asked to solve the dependency problem at its root and to gate safe merges. The method was six parallel research threads, each writing a cited evidence file, grounded in the repository's own history, configurations, and pull requests, plus the prototype we executed this session inside the real Isaac image. The full research, with citations, lives in the tracking folder."},
]


def _narration(notes: str) -> str:
    """Normalize narration for macOS `say`: spell OIDC, de-hyphenate 'pull-request',
    and split spelled-acronym+word joins (e.g. 'C-P-U-safe' -> 'C-P-U safe',
    which `say` otherwise reads as 'C-safe').

    Applied at generation time so rebuilds always produce correct TTS text
    (GPU/CPU/CI/SDK are left bare per the chosen voice; only OIDC mis-reads).
    """
    notes = re.sub(r"\bOIDC\b", "O-I-D-C", notes)
    notes = notes.replace("pull-request", "pull request")
    notes = re.sub(r"\b([A-Z](?:-[A-Z])+)-([a-z])", r"\1 \2", notes)
    return notes


class _BlockDumper(yaml.SafeDumper):
    """YAML dumper that renders multi-line strings as literal `|` blocks for
    readable, line-by-line diffs of narration and code."""


def _repr_str(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_BlockDumper.add_representer(str, _repr_str)


def _slug(title, seen):
    """Stable id from a slide title (lowercase, dash-joined). Deduped only on
    collision; titles are unique today, so ids never shift when a slide is
    inserted mid-deck -> localized diffs."""
    s = re.sub(r"[\u2010-\u2015]", " ", title.lower())  # unicode dashes -> space
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "slide"
    seen[s] = seen.get(s, 0) + 1
    return s if seen[s] == 1 else f"{s}-{seen[s]}"


def _tuples_to_lists(v):
    if isinstance(v, (list, tuple)):
        return [_tuples_to_lists(x) for x in v]
    if isinstance(v, dict):
        return {k: _tuples_to_lists(x) for k, x in v.items()}
    return v


def write_combined_yaml(slides, path="deck.yaml"):
    """Emit one combined, human-diffable YAML of all slide source, keyed by a
    stable `id`. Robust to mid-deck insertion: a new slide is one added block;
    every other block stays byte-identical. Derived artifact (the renderer reads
    content/slide-NN/, not this) — regenerate via gen_content.py."""
    seen = {}
    items = [{"id": _slug(s["title"], seen), **_tuples_to_lists(s)} for s in slides]
    header = (
        "# Generated by gen_content.py -- do not hand-edit; edit SLIDES in gen_content.py.\n"
        "# Combined slide source keyed by stable `id` (title slug) so diffs stay clean and\n"
        "# localized when slides are inserted mid-deck. Regenerate: python gen_content.py\n"
    )
    body = yaml.dump({"slides": items}, Dumper=_BlockDumper, sort_keys=False,
                     allow_unicode=True, default_flow_style=False, width=4096)
    Path(path).write_text(header + body)
    return len(items)


def main():
    root = Path("content")
    (root / "global").mkdir(parents=True, exist_ok=True)
    Path("narration").mkdir(exist_ok=True)
    for d in root.glob("slide-*"):
        for p in d.glob("*"):
            p.unlink()
        d.rmdir()
    style = {"dimensions": {"width_inches": W, "height_inches": H, "format": "16:9"},
             "metadata": {"title": "PR Regression Safety — Research Findings",
                          "author": "Task Researcher (Copilot)"},
             "defaults": {"speaker_notes_required": True}}
    (root / "global" / "style.yaml").write_text(
        yaml.safe_dump(style, sort_keys=False, allow_unicode=True))

    dividers = ["DIVIDER_BLUE", "DIVIDER_TEAL", "DIVIDER_ORANGE", "DIVIDER_RED",
                "DIVIDER_GRAD-1", "DIVIDER_BLUE-2", "DIVIDER_TEAL", "DIVIDER_ORANGE"]
    sec = 0
    for i, s in enumerate(SLIDES, 1):
        kind = s["kind"]
        if kind == "title":
            layout = "COVER_BLUE"
        elif kind == "section":
            layout = dividers[sec % len(dividers)]
            sec += 1
        else:
            layout = "TITLE-1"
        elements = RENDER[kind](s)
        # Match the template's bottom-right slide number (absent on the cover).
        if kind != "title":
            num_clr = WHITE if kind == "section" else TEXT
            elements.append(tb(PAGENUM_L, PAGENUM_T, PAGENUM_W, PAGENUM_H, str(i),
                               PAGENUM_SIZE, num_clr, align="right"))
        doc = {"slide": i, "title": s["title"], "layout": layout, "elements": elements,
               "speaker_notes": s["notes"]}
        d = root / f"slide-{i:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "content.yaml").write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))
        Path("narration", f"slide-{i:02d}.txt").write_text(_narration(s["notes"]))

    # Full narration script as one Markdown file (raw notes, not TTS-normalized).
    script = ["# PR Regression Safety — Narration Script", "",
              f"{len(SLIDES)} slides. Generated from `gen_content.py`.", ""]
    for i, s in enumerate(SLIDES, 1):
        script.append(f"## Slide {i:02d} — {s['title']}")
        script.append("")
        script.append(s["notes"])
        script.append("")
    Path("narration-script.md").write_text("\n".join(script))
    n_yaml = write_combined_yaml(SLIDES)
    print(f"wrote {len(SLIDES)} slides + narration-script.md + deck.yaml ({n_yaml} slides)")


if __name__ == "__main__":
    main()
