from __future__ import annotations

import argparse
import json
import os
import sys

from depsig import Change, diff_signatures, hash_tree, tree_signature
from depsig.core import _change_to_payload, _render_change


class _HelpArgs:
    help_requested = True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute and compare dependency tree signatures."
    )
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
