# depsig

Lightweight dependency tree signature and diff tool.

Source: https://github.com/noahalexandercampbell/depsig

## About

`depsig` scans a directory tree, computes normalized SHA-256 signatures for each text file, and emits a stable project fingerprint. It can also diff two snapshots to detect added, removed, or modified files.

It is designed for fast, deterministic drift detection in local repos, CI pipelines, and staging check workflows.

## Features

- Deterministic text-file signature hashing with content normalization
- Stable tree signature across runs for unchanged projects
- JSON machine-readable output for scripting and CI
- Diff mode against a prior snapshot with `--old`
- Git-agnostic: works on any directory tree

## Installation

```bash
python -m pip install -e .
```

## Usage

```bash
# Scan current directory and print per-file signatures
depsig

# Print only the tree signature
depsig --signature

# Save current snapshot to a JSON file
depsig --out baseline.json

# Diff against a previous snapshot
depsig --old baseline.json

# JSON output for scripting
depsig --old baseline.json --json
```

### Output format

Plain text:
```text
signature=<tree_signature>
<path>: <content_hash>|<size>|<mtime_ns>
```

Diff:
```text
added: <path> | NULL -> <new_signature>
removed: <path> | <old_signature> -> NULL
modified: <path> | <old_signature> -> <new_signature>
```

JSON diff:
```json
{
  "old_signature": "...",
  "signature": "...",
  "changes": [
    {"path": "...", "type": "modified", "old": "...", "new": "..."}
  ]
}
```

## Project structure

```text
.
├── README.md
├── pyproject.toml
├── src/depsig
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   └── core.py
└── tests
    └── test_depsig.py
```

## Tags / keywords

depsig, signature, diff, tree, drift, ci, snapshot, sha256, filesystem, developer-tools
