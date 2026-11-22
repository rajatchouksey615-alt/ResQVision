#!/usr/bin/env python3
"""Check first-party paths, file contents, and commit messages against repository policy."""

from __future__ import annotations

import argparse
import codecs
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_BASE = "".join(chr(value) for value in (112, 104, 97, 115, 101))
_PATTERN = re.compile(re.escape(_BASE) + r"[\w-]*", re.IGNORECASE)
_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        ".env",
        "venv",
        "env",
        ".envdir",
        "site-packages",
        "__pypackages__",
        "node_modules",
        "vendor",
        "pods",
        ".pub",
        ".pub-cache",
        "build",
        "dist",
        "target",
        ".dart_tool",
        ".gradle",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".cache",
        "coverage",
        "htmlcov",
        ".local-postgres",
    }
)


def _excluded(relative_path: Path) -> bool:
    return any(part.lower() in _EXCLUDED_DIRECTORIES for part in relative_path.parts)


def _contains_prohibited_text(value: str) -> bool:
    return _PATTERN.search(value) is not None


def _decode(raw: bytes) -> str | None:
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(codecs.BOM_UTF8):
        raw = raw[len(codecs.BOM_UTF8) :]
    if b"\x00" in raw:
        return None
    return raw.decode("utf-8", errors="replace")


def _scan_worktree() -> list[str]:
    issues: list[str] = []
    for current, directories, filenames in os.walk(ROOT):
        current_path = Path(current)
        retained_directories: list[str] = []
        for directory in directories:
            relative = (current_path / directory).relative_to(ROOT)
            if _excluded(relative):
                continue
            if _contains_prohibited_text(relative.as_posix()):
                issues.append(f"path: {relative.as_posix()}")
            retained_directories.append(directory)
        directories[:] = retained_directories

        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(ROOT)
            if _excluded(relative):
                continue
            relative_name = relative.as_posix()
            if _contains_prohibited_text(relative_name):
                issues.append(f"path: {relative_name}")
            try:
                text = _decode(path.read_bytes())
            except OSError as error:
                issues.append(f"unreadable file: {relative_name} ({error})")
                continue
            if text is not None:
                for line_number, line in enumerate(text.splitlines(), 1):
                    if _contains_prohibited_text(line):
                        issues.append(f"content: {relative_name}:{line_number}")
    return issues


def _git_output(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or "Git inspection failed.")
    return result.stdout


def _scan_staged() -> list[str]:
    issues: list[str] = []
    raw_paths = _git_output("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
    for raw_path in raw_paths.split(b"\x00"):
        if not raw_path:
            continue
        relative_name = os.fsdecode(raw_path)
        relative = Path(relative_name)
        if _excluded(relative):
            continue
        if _contains_prohibited_text(relative.as_posix()):
            issues.append(f"staged path: {relative.as_posix()}")
        try:
            staged = _git_output("show", f":{relative_name}")
        except RuntimeError as error:
            issues.append(f"cannot read staged file: {relative_name} ({error})")
            continue
        text = _decode(staged)
        if text is not None:
            for line_number, line in enumerate(text.splitlines(), 1):
                if _contains_prohibited_text(line):
                    issues.append(f"staged content: {relative_name}:{line_number}")
    return issues


def _scan_commit_message(path: Path) -> list[str]:
    text = _decode(path.read_bytes())
    if text is None:
        return ["commit message is not readable text"]
    return [f"commit message: {path}"] if _contains_prohibited_text(text) else []


def _scan_commit_range(revision_range: str) -> list[str]:
    if ".." in revision_range:
        base, head = revision_range.rsplit("..", 1)
        if base and set(base) == {"0"}:
            revisions = _git_output("rev-list", "--max-count=1", head)
        else:
            revisions = _git_output("rev-list", "--reverse", revision_range)
    else:
        revisions = _git_output("rev-list", "--max-count=1", revision_range)

    issues: list[str] = []
    for revision in revisions.decode("ascii", errors="replace").splitlines():
        message = _git_output("show", "-s", "--format=%B", revision).decode(
            "utf-8", errors="replace"
        )
        if _contains_prohibited_text(message):
            issues.append(f"commit message: {revision}")
    return issues


def _self_test() -> list[str]:
    examples = (
        _BASE,
        _BASE.upper(),
        _BASE + "s",
        _BASE + "-based",
        _BASE + " 5E",
        "prefix-" + _BASE + "_based",
    )
    if all(_contains_prohibited_text(example) for example in examples):
        return []
    return ["pattern self-check failed"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--all", action="store_true", help="scan repository paths and contents")
    modes.add_argument("--staged", action="store_true", help="scan staged paths and contents")
    modes.add_argument("--commit-message", type=Path, help="scan one commit-message file")
    modes.add_argument("--commit-range", help="scan commit messages in a Git revision range")
    modes.add_argument("--self-test", action="store_true", help="check pattern behavior")
    arguments = parser.parse_args()

    try:
        if arguments.staged:
            issues = _scan_staged()
        elif arguments.commit_message:
            issues = _scan_commit_message(arguments.commit_message)
        elif arguments.commit_range:
            issues = _scan_commit_range(arguments.commit_range)
        elif arguments.self_test:
            issues = _self_test()
        else:
            issues = _scan_worktree()
    except (OSError, RuntimeError) as error:
        print(f"Repository policy check could not complete: {error}", file=sys.stderr)
        return 2

    if issues:
        print(f"Repository policy check found {len(issues)} issue(s):", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("Repository policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
