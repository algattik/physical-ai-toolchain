#!/usr/bin/env python3
"""Fail if a production HuggingFace download omits an explicit ``revision``.

Bare ``repo_id`` calls resolve a mutable HEAD, so an upstream account or org
compromise can silently ship new weights or a poisoned dataset into evaluation
and deployed inference. This guard parses the AST of production ``.py`` files and
rejects any ``from_pretrained`` / ``snapshot_download`` / ``hf_hub_download``
call that has no ``revision`` keyword argument.

Test files and vendored code are excluded — the pin is a production requirement,
and tests deliberately exercise the unpinned/local-path forms. Multi-line calls
are handled by the AST, so this is robust where a line-oriented grep is not.

Usage:
    python scripts/security/check_hf_pins.py [ROOT ...]
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_GUARDED_FUNCTIONS = frozenset({"from_pretrained", "snapshot_download", "hf_hub_download"})

_DEFAULT_ROOTS = (
    "evaluation",
    "training",
    "fleet-deployment",
    "data-management/viewer/backend",
)

_EXCLUDED_PARTS = frozenset({"tests", "external", "node_modules", ".venv", ".git"})


def _is_excluded(path: Path) -> bool:
    """Skip test suites, vendored trees, and test-named modules."""
    if any(part in _EXCLUDED_PARTS for part in path.parts):
        return True
    return path.name.startswith("test_")


def _callee_name(node: ast.Call) -> str | None:
    """Return the attribute/name of a call's callee, or None."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _has_revision(node: ast.Call) -> bool:
    """True if the call passes ``revision`` explicitly or forwards ``**kwargs``.

    A ``**kwargs`` splat (keyword with ``arg is None``) cannot be verified
    statically, so it is accepted rather than flagged as a false positive.
    """
    return any(keyword.arg == "revision" or keyword.arg is None for keyword in node.keywords)


def _violations_in_file(path: Path) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node)
        if name in _GUARDED_FUNCTIONS and not _has_revision(node):
            found.append((node.lineno, node.col_offset, name))
    return found


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    roots = [Path(arg) for arg in argv[1:]] or [repo_root / root for root in _DEFAULT_ROOTS]

    violations = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if _is_excluded(path):
                continue
            for lineno, col, name in _violations_in_file(path):
                rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
                violations.append(f"{rel}:{lineno}:{col}: {name}() call missing an explicit 'revision' argument")

    if violations:
        print("HuggingFace revision-pin guard failed:\n", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "\nPin every from_pretrained/snapshot_download/hf_hub_download to an immutable "
            "commit SHA via a 'revision=' argument (None is allowed for local-path callers).",
            file=sys.stderr,
        )
        return 1

    print("HuggingFace revision-pin guard passed: all guarded calls carry a 'revision' argument.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
