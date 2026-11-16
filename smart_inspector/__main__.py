"""Allow ``python -m smart_inspector`` to run the command-line interface."""

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
