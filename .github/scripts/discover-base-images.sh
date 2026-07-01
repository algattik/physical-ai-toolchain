#!/usr/bin/env bash
# Print the unique, digest-pinned external base images referenced by FROM lines
# across every Dockerfile in the repo (one per line). Stage aliases and
# ARG/scratch bases carry no @sha256 digest and are excluded. Shared by
# container-scan.yml and container-cve-remediation.sh so both discover the same
# image set from a single source of truth.
set -o errexit -o nounset -o pipefail

git ls-files -z '*Dockerfile*' \
  | xargs -0 -r grep -hiE '^FROM[[:space:]]' \
  | grep -oiE '([a-z0-9.-]+(:[0-9]+)?/)?[a-z0-9._/-]+(:[a-z0-9._-]+)?@sha256:[0-9a-f]{64}' \
  | sort -u
