from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from depsig import diff_signatures, hash_path, hash_tree, tree_signature


def test_hash_path_consistent(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("a  b\nc d\n", encoding="utf-8")
    first = hash_path(str(target))
    second = hash_path(str(target))
    assert first == second
    assert target.stat().st_size > 0
    assert "|" in first


def test_hash_tree_is_stable(tmp_path):
    (tmp_path / "README.md").write_text("# hello\nworld\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    first = hash_tree(str(tmp_path))
    second = hash_tree(str(tmp_path))
    assert first == second
    assert ".git/HEAD" not in first
    assert "README.md" in first


def test_tree_signature_changes_with_content():
    entries_a = {"a.txt": "abc", "b.txt": "def"}
    entries_b = {"a.txt": "abc", "b.txt": "xyz"}
    assert tree_signature(entries_a) != tree_signature(entries_b)
    assert tree_signature({}) != tree_signature(entries_a)


def test_diff_signatures_added_removed_modified():
    old = {"a.txt": "111", "b.txt": "222"}
    new = {"b.txt": "222", "c.txt": "333"}
    changes = diff_signatures(old, new)
    paths = [change.path for change in changes]
    assert paths == ["a.txt", "c.txt"]
    assert changes[0].change_type == "removed"
    assert changes[0].old_value == "111"
    assert changes[0].new_value is None
    assert changes[1].change_type == "added"
    assert changes[1].old_value is None
    assert changes[1].new_value == "333"

    modified_old = {"x.txt": "111"}
    modified_new = {"x.txt": "222"}
    modified = diff_signatures(modified_old, modified_new)
    assert len(modified) == 1
    assert modified[0].change_type == "modified"
    assert modified[0].old_value == "111"
    assert modified[0].new_value == "222"


def test_diff_signatures_empty_when_identical():
    entries = {"a.txt": "111"}
    assert diff_signatures(entries, entries) == []


def test_hash_path_error_fallback(tmp_path):
    target = tmp_path / "missing.txt"
    expected = hash_path(str(target))
    assert "error" in expected
