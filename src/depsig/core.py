from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Change:
    path: str
    change_type: str
    old_value: str | None
    new_value: str | None


def _normalize_line(line: str) -> str:
    return line.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_text_files(root: str) -> Iterable[str]:
    ignored_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist", "build", ".venv"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in ignored_dirs and not os.path.islink(os.path.join(dirpath, d))
        )
        for filename in sorted(filenames):
            path = os.path.join(dirpath, filename)
            if os.path.islink(path):
                continue
            yield path


def _read_lines(path: str) -> tuple[list[str], str | None]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            lines = file.readlines()
    except OSError as exc:
        return [], str(exc)
    return [line.rstrip("\n\r") for line in lines], None


def hash_path(path: str) -> str:
    rel = os.path.relpath(path, os.getcwd())
    try:
        stat = os.stat(path)
        size = stat.st_size
        mtime = stat.st_mtime_ns
    except OSError as exc:
        return _sha256(f"{rel}\x00".encode("utf-8")) + f"|error:{exc}"

    lines, _ = _read_lines(path)
    normalized = "\n".join(_normalize_line(line) for line in lines)
    content_hash = _sha256(normalized.encode("utf-8"))
    return f"{content_hash}|{size}|{mtime}"


def hash_tree(root: str) -> dict[str, str]:
    root = os.path.abspath(root)
    entries = {}
    for path in _iter_text_files(root):
        rel = os.path.relpath(path, root)
        entries[rel] = hash_path(path)
    return entries


def tree_signature(entries: dict[str, str]) -> str:
    joined = "\n".join(f"{path}:{entries[path]}" for path in sorted(entries))
    return _sha256(joined.encode("utf-8"))


def diff_signatures(old: dict[str, str], new: dict[str, str]) -> list[Change]:
    changes: list[Change] = []
    for path in sorted(set(old) | set(new)):
        old_value = old.get(path)
        new_value = new.get(path)
        if old_value == new_value:
            continue
        change_type = "added" if old_value is None else "removed" if new_value is None else "modified"
        changes.append(Change(path=path, change_type=change_type, old_value=old_value, new_value=new_value))
    return changes


class _HelpArgs:
    help_requested = True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute and compare dependency tree signatures.")
    parser.add_argument("root", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--signature", action="store_true", help="Print the current tree signature")
    parser.add_argument("--json", action="store_true", help="Emit JSON machine-readable output")
    parser.add_argument("--old", metavar="PATH", help="Previous tree signature JSON file for diff")
    parser.add_argument("--out", metavar="PATH", help="Write current tree entries to a JSON file")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace | _HelpArgs | None:
    parser = _build_parser()
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return _HelpArgs()
        raise


def _render_change(change: Change) -> str:
    old = change.old_value or "NULL"
    new = change.new_value or "NULL"
    return f"{change.change_type}: {change.path} | {old} -> {new}"


def _change_to_payload(change: Change) -> dict[str, str | None]:
    return {
        "path": change.path,
        "type": change.change_type,
        "old": change.old_value,
        "new": change.new_value,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if isinstance(args, _HelpArgs) or args is None:
        return 0

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    entries = hash_tree(root)
    signature = tree_signature(entries)

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as file:
                json.dump({"signature": signature, "entries": entries}, file, indent=2, sort_keys=True)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    if args.old:
        if not os.path.isfile(args.old):
            print(f"error: {args.old} does not exist", file=sys.stderr)
            return 1
        try:
            with open(args.old, "r", encoding="utf-8") as file:
                old_payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        old_entries = old_payload.get("entries", {})
        if not isinstance(old_entries, dict):
            old_entries = {}
        changes = diff_signatures(old_entries, entries)
        if args.json:
            payload = {
                "old_signature": old_payload.get("signature"),
                "signature": signature,
                "changes": [_change_to_payload(change) for change in changes],
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for change in changes:
                print(_render_change(change))
        return 0

    if args.signature:
        print(signature)
        return 0

    print(f"signature={signature}")
    for path in sorted(entries):
        print(f"{path}: {entries[path]}")
    return 0
