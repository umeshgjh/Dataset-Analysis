"""JSON serialization that accepts the report's Python and NumPy values."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

from smart_inspector.exceptions import InspectionError

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is a required dependency
    np = None


def to_jsonable(value: Any) -> Any:
    """Convert report values to objects ``json.dumps`` can emit.

    ``NaN`` and infinity become ``None`` so the file is strict JSON.
    NumPy scalars become Python numbers. Tuples become lists.
    """
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if np is not None and isinstance(value, np.integer):
        return int(value)
    if np is not None and isinstance(value, np.floating):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    if np is not None and isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return [to_jsonable(item) for item in sorted(value, key=repr)]
    type_name = type(value).__name__
    if type_name in {"NAType", "NaTType", "Absent"}:
        return None
    return str(value)


def dump_report(payload: Any) -> str:
    """Serialize a report payload, raising a user-facing error on failure."""
    try:
        return json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise InspectionError(
            f"Could not serialize the inspection report to JSON: {exc}"
        ) from exc


def write_output(path: str | Path, text: str) -> None:
    """Write UTF-8 text, creating parent directories when needed."""
    destination = Path(path)
    if destination.exists() and destination.is_dir():
        raise InspectionError(
            f"Cannot write the report to {destination}: the path is a directory."
        )
    try:
        if destination.parent != Path("."):
            destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise InspectionError(
            f"Could not write the report to {destination}: {exc.strerror}."
        ) from exc
