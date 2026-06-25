#!/usr/bin/env bash
# Run a domain's runtime-image import smoke in its production container.
# Resolves the domain's image, then runs shared/ci/smoke-import.sh inside it
# against the repository mounted at /workspace. Shared by CI and local runs.
set -o errexit -o nounset -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$SCRIPT_DIR/../.." && pwd))"
# shellcheck source=../../scripts/lib/common.sh
source "$REPO_ROOT/scripts/lib/common.sh"

# Source of truth for the LeRobot runtime image (the default-values block).
LEROBOT_WORKFLOW="training/il/workflows/osmo/lerobot-train.yaml"

show_help() {
    cat << EOF
Usage: $(basename "$0") DOMAIN

Run a domain's runtime-image import smoke in its production container. The
repository is mounted at /workspace and shared/ci/smoke-import.sh runs inside
the container on the real interpreter. Requires Docker.

DOMAIN:
    rl    Isaac Lab container (\$DEFAULT_ISAAC_LAB_IMAGE)
    il    LeRobot PyTorch container (from ${LEROBOT_WORKFLOW})

EXAMPLES:
    $(basename "$0") rl
    $(basename "$0") il
EOF
}

domain=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help) show_help; exit 0 ;;
        -*) fatal "Unknown option: $1" ;;
        *)
            [[ -z "$domain" ]] || fatal "Unexpected argument: $1"
            domain="$1"
            shift
            ;;
    esac
done

[[ -n "$domain" ]] || { show_help; fatal "DOMAIN is required"; }

case "$domain" in
    rl) image="$DEFAULT_ISAAC_LAB_IMAGE" ;;
    il)
        image="$(grep -m1 -E '^[[:space:]]*image:[[:space:]]*pytorch/' \
            "$REPO_ROOT/$LEROBOT_WORKFLOW" | awk '{print $2}')"
        [[ -n "$image" ]] || fatal "Could not resolve LeRobot image from $LEROBOT_WORKFLOW"
        ;;
    evaluation)
        fatal "evaluation has no runtime-image smoke; run: smoke-import.sh evaluation --mode cpu"
        ;;
    *) fatal "Unknown domain: $domain (expected rl or il)" ;;
esac

require_tools docker

section "Runtime-image smoke: ${domain}"
print_kv "Image" "$image"
print_kv "Mount" "${REPO_ROOT} -> /workspace"

docker run --rm --entrypoint bash \
    -v "${REPO_ROOT}:/workspace" -w /workspace \
    "$image" \
    shared/ci/smoke-import.sh "$domain" --mode image
