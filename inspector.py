#!/usr/bin/env python3
"""Command-line entry point for the Smart Data Inspector.

The inspection engine lives in :mod:`smart_inspector`. This file only parses
the command and returns a process exit code.
"""

from __future__ import annotations

import sys


def _load_main():
    try:
        from smart_inspector.cli import main
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except ModuleNotFoundError as exc:
        print(
            "Error: missing dependency "
            f"{exc.name!r}. Install dependencies with "
            "'python -m pip install -r requirements.txt'.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    return main


if __name__ == "__main__":
    raise SystemExit(_load_main()())
