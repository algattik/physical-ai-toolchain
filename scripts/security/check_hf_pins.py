#!/usr/bin/env python3
"""Fail if a production HuggingFace download omits an explicit ``revision``.

Bare ``repo_id`` calls resolve a mutable HEAD, so an upstream account or org
compromise can silently ship new weights or a poisoned dataset into evaluation
and deployed inference. This guard parses the AST of production ``.py`` files and
of inline ``python3 << 'DELIM'`` heredocs and ``python -c "..."`` one-liners
embedded in workflow YAML — the OSMO download paths live there, invisible to a
``.py``-only walk — and rejects any
``from_pretrained`` / ``snapshot_download`` / ``hf_hub_download`` call that has no
explicit ``revision`` keyword. A literal ``revision=None`` is rejected too: it is
provably unpinned. A ``**kwargs`` splat is accepted, since it cannot be resolved
statically.

Test files and vendored code are excluded — the pin is a production requirement,
and tests deliberately exercise the unpinned/local-path forms. Multi-line calls
are handled by the AST, so this is robust where a line-oriented grep is not.

Usage:
    python scripts/security/check_hf_pins.py [ROOT ...]
"""

from __future__ import annotations

import ast
import re
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

_GUARDED_FUNCTIONS = frozenset({"from_pretrained", "snapshot_download", "hf_hub_download"})

_DEFAULT_ROOTS = (
    "evaluation",
    "training",
    "fleet-deployment",
    "data-management/viewer/backend",
)

_EXCLUDED_PARTS = frozenset({"tests", "external", "node_modules", ".venv", ".git"})

# ``python3 << 'DELIM'``, ``python3 - <<'DELIM'``, ``python -u <<-"DELIM"`` heredoc
# opener in workflow YAML. The optional ``[^<\n]*`` allows the stdin ``-`` marker and
# any interpreter flags that commonly precede the redirection. A trailing token after
# the delimiter (a redirect ``> log`` or pipe ``| tee``) is allowed so those forms are
# not silently skipped.
_HEREDOC_RE = re.compile(r"\bpython3?\s+(?:[^<\n]*\s)?<<-?\s*['\"]?(\w+)['\"]?(?:\s|$)")

# ``python -c "<code>"`` / ``python3 -c '<code>'`` one-liner in workflow YAML. The
# shell-quoted payload is captured so its AST can be scanned like any other source.
_INLINE_C_RE = re.compile(r"\bpython3?\s+(?:-\S+\s+)*-c\s+(['\"])(?P<code>.*?)\1", re.DOTALL)


class ScanError(RuntimeError):
    """Raised when a source file cannot be scanned safely."""


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
    """True if the call pins ``revision`` (or forwards an unverifiable ``**kwargs``).

    A ``**kwargs`` splat (keyword with ``arg is None``) cannot be resolved
    statically, so it is accepted rather than flagged as a false positive. A
    literal ``revision=None`` is provably unpinned and is rejected; a non-constant
    ``revision`` expression (a variable or attribute) is accepted.
    """
    has_splat = False
    for keyword in node.keywords:
        if keyword.arg is None:
            has_splat = True
        elif keyword.arg == "revision":
            return not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None)
    return has_splat


def _violations_in_source(source: str, filename: str) -> list[tuple[int, int, str]]:
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as error:
        line = error.lineno or 0
        raise ScanError(f"unable to parse Python source at line {line}") from error

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node)
        if name in _GUARDED_FUNCTIONS and not _has_revision(node):
            found.append((node.lineno, node.col_offset, name))
    return found


def _python_heredocs(text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(body_start_lineno, dedented_source)`` for each Python heredoc.

    OSMO workflow YAML embeds its real download code as ``python3 << 'DELIM'``
    heredocs; the quoted delimiter means the body is literal Python. Line numbers
    are 1-based against the YAML file so AST positions map back correctly.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _HEREDOC_RE.search(lines[i])
        if not match:
            i += 1
            continue
        delimiter = match.group(1)
        body_start = i + 1
        end = body_start
        while end < len(lines) and lines[end].strip() != delimiter:
            end += 1
        yield body_start + 1, textwrap.dedent("\n".join(lines[body_start:end]))
        i = end + 1


def _python_inline_c(text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(lineno, code)`` for each ``python -c "<code>"`` invocation.

    Workflow YAML embeds guarded downloads as ``python -c`` one-liners as well as
    heredocs; the quoted payload is extracted so its AST can be scanned. Line
    numbers are 1-based against the YAML file.
    """
    for match in _INLINE_C_RE.finditer(text):
        lineno = text.count("\n", 0, match.start()) + 1
        yield lineno, match.group("code")


def _violations_in_inline(code: str, filename: str) -> list[tuple[int, int, str]]:
    """Scan a ``python -c`` payload, failing closed only when a guarded call is unverifiable.

    Inline snippets frequently contain shell ``${VAR}`` interpolation that is not
    valid Python; such a snippet is skipped. But if it mentions a guarded function,
    an unparseable payload is a hard failure rather than a silent bypass.
    """
    try:
        return _violations_in_source(code, filename)
    except ScanError:
        if any(fn in code for fn in _GUARDED_FUNCTIONS):
            raise
        return []


def _violations_in_file(path: Path) -> list[tuple[int, int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ScanError("unable to decode as UTF-8") from error

    if path.suffix in (".yaml", ".yml"):
        found = []
        for offset, block in _python_heredocs(text):
            for lineno, col, name in _violations_in_source(block, str(path)):
                found.append((offset + lineno - 1, col, name))
        for lineno, code in _python_inline_c(text):
            for _code_lineno, col, name in _violations_in_inline(code, str(path)):
                found.append((lineno, col, name))
        return found

    return _violations_in_source(text, str(path))


def _iter_source_files(root: Path) -> Iterator[Path]:
    """Yield production ``.py`` files plus workflow YAML carrying Python heredocs."""
    yield from root.rglob("*.py")
    for suffix in ("*.yaml", "*.yml"):
        for path in root.rglob(suffix):
            if "workflows" in path.parts:
                yield path


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    roots = [Path(arg) for arg in argv[1:]] or [repo_root / root for root in _DEFAULT_ROOTS]

    violations = []
    scan_errors = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(set(_iter_source_files(root))):
            if _is_excluded(path):
                continue
            rel = path.relative_to(repo_root) if path.is_relative_to(repo_root) else path
            try:
                file_violations = _violations_in_file(path)
            except ScanError as error:
                scan_errors.append(f"{rel}: {error}")
                continue
            for lineno, col, name in file_violations:
                violations.append(f"{rel}:{lineno}:{col}: {name}() call missing an explicit 'revision' argument")

    if scan_errors or violations:
        print("HuggingFace revision-pin guard failed:\n", file=sys.stderr)
        if scan_errors:
            print("  Files could not be scanned:", file=sys.stderr)
            for error in scan_errors:
                print(f"    {error}", file=sys.stderr)
            print(file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "\nPin every from_pretrained/snapshot_download/hf_hub_download to an immutable "
            "commit SHA via a 'revision=' argument. A literal 'revision=None' is rejected as "
            "provably unpinned; pass a resolved SHA (a variable is accepted for local-path callers).",
            file=sys.stderr,
        )
        return 1

    print("HuggingFace revision-pin guard passed: all guarded calls carry a 'revision' argument.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
