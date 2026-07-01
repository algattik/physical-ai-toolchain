"""Helpers for pinned HuggingFace model and dataset downloads."""

from __future__ import annotations

from pathlib import Path


def resolve_hf_revision(repo_id: str, revision: object, *, revision_name: str = "revision") -> str | None:
    """Return a non-empty revision, or allow local paths to load without one.

    Remote HuggingFace repository IDs must be pinned by an explicit revision so
    callers do not resolve mutable HEAD. Local paths are allowed without a
    revision because no Hub download occurs.
    """
    resolved = str(revision or "").strip()
    if resolved:
        return resolved

    repo = str(repo_id or "").strip()
    if not repo:
        raise ValueError("policy repository or local path is required")

    local_path = Path(repo).expanduser()
    if local_path.exists() or local_path.is_absolute() or repo.startswith("."):
        return None

    raise ValueError(
        f"{revision_name} is required when loading a remote HuggingFace policy repo; "
        "use a local path for development or pass an immutable commit SHA"
    )
