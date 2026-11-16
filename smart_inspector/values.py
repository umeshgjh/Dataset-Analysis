"""Cell-level rules shared by loading, inference, duplicates, and summaries.

Keeping these decisions in one module stops the profiler and the quality checks
from drifting apart. Nothing here changes the caller's objects.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

REPORT_TEXT_LIMIT = 200
SAMPLE_LIMIT = 10

KIND_ORDER = ("boolean", "integer", "float", "datetime", "string")
DOMINANT_PRIORITY = ("boolean", "datetime", "integer", "float", "string")

_BOOL_WORDS = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
}
_INT_RE = re.compile(r"^[+-]?(0|[1-9]\d*)$")
_FLOAT_RE = re.compile(
    r"^[+-]?(?:(?:\d+\.\d*)|(?:\.\d+))(?:[eE][+-]?\d+)?$|^[+-]?\d+[eE][+-]?\d+$"
)
_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?)?"
    r"(?:Z|[+-]\d{2}:\d{2})?$"
)
_SLASH_RE = re.compile(r"^\d{4}/\d{2}/\d{2}(?: \d{2}:\d{2}:\d{2})?$")


class Absent:
    """Marker for a JSON object that did not contain a key seen on another row."""

    def __repr__(self) -> str:
        return "ABSENT"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Absent)

    def __hash__(self) -> int:
        return hash("smart_inspector.Absent")


ABSENT = Absent()


def is_missing(value: Any, tokens: set[str]) -> bool:
    """Return whether ``value`` counts as missing under ``tokens``.

    Zero, ``False``, and the strings ``"0"`` and ``"false"`` are real values
    unless the caller explicitly listed them in ``tokens``.
    """
    if value is None or isinstance(value, Absent):
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return True
        return stripped.lower() in tokens
    return False


def missing_label(value: Any) -> str:
    """Return a stable label for one missing representation."""
    if isinstance(value, Absent):
        return "<absent>"
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "<null>"
    if isinstance(value, str) and value.strip() == "":
        return "<empty>"
    if isinstance(value, str):
        return value.strip().lower()
    return display_value(value)


def value_kind(value: Any) -> str | None:
    """Classify one non-missing value.

    Returns one of ``boolean``, ``integer``, ``float``, ``datetime``, or
    ``string``. Returns ``None`` when ``value`` is missing for an empty token
    set; callers should skip missing values before asking for a kind.
    """
    if value is None or isinstance(value, Absent):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        if math.isfinite(value):
            return "float"
        return "string"
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered in _BOOL_WORDS:
            return "boolean"
        if _INT_RE.fullmatch(text):
            return "integer"
        if _FLOAT_RE.fullmatch(text):
            return "float"
        if _is_datetime(text):
            return "datetime"
        return "string"
    return "string"


def value_identity(value: Any, tokens: set[str]) -> tuple[Any, ...]:
    """Return a hashable identity that preserves type and exact text.

    Every missing representation shares one identity so duplicate detection
    treats ``""``, ``"n/a"``, JSON null, and an absent JSON key as the same.
    ``True`` and ``1`` stay different.
    """
    if is_missing(value, tokens):
        return ("missing",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value)
    if isinstance(value, str):
        return ("str", value)
    return ("other", repr(value))


def parse_numeric(value: Any) -> int | float | None:
    """Parse a value that ``value_kind`` would call integer or float.

    The original object is not modified. Leading or trailing spaces on text
    are ignored for the numeric parse only.
    """
    if isinstance(value, bool) or isinstance(value, Absent) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return None
    if isinstance(value, str):
        text = value.strip()
        if _INT_RE.fullmatch(text):
            return int(text)
        if _FLOAT_RE.fullmatch(text):
            try:
                return float(text)
            except OverflowError:
                return None
    return None


def compatible(dominant: str, kind: str) -> bool:
    """Return whether ``kind`` is allowed inside an accepted ``dominant`` type.

    Integer values belong in a float column. The reverse is not true: a
    fractional value is unexpected in an integer column.
    """
    if dominant == "float" and kind in {"integer", "float"}:
        return True
    return dominant == kind


def display_value(value: Any) -> str:
    """Return readable text for a stored cell without changing its meaning."""
    if isinstance(value, Absent):
        return "<absent>"
    if value is None:
        return "<null>"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    if isinstance(value, str):
        return value
    return str(value)


def clip_text(text: str, limit: int = REPORT_TEXT_LIMIT) -> tuple[str, bool]:
    """Clip ``text`` to ``limit`` characters and report whether it was clipped."""
    if len(text) <= limit:
        return text, False
    if limit <= 1:
        return "…", True
    return text[: limit - 1] + "…", True


def report_scalar(value: Any, limit: int = REPORT_TEXT_LIMIT) -> tuple[Any, bool]:
    """Return a JSON-safe scalar, clipping long text."""
    if isinstance(value, str):
        return clip_text(value, limit)
    if isinstance(value, bool) or isinstance(value, int) or value is None:
        return value, False
    if isinstance(value, float):
        if math.isfinite(value):
            return value, False
        return str(value), False
    if isinstance(value, Absent):
        return None, False
    text, truncated = clip_text(display_value(value), limit)
    return text, truncated


def datetime_pattern(value: str) -> str:
    """Return a short label for a value already known to be a datetime string."""
    text = value.strip()
    has_time = "T" in text or " " in text
    if "/" in text:
        return "slash date and time" if has_time else "slash date"
    return "ISO date and time" if has_time else "ISO date"


def _is_datetime(text: str) -> bool:
    if _ISO_RE.fullmatch(text):
        candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            datetime.fromisoformat(candidate)
        except ValueError:
            return False
        return True
    if _SLASH_RE.fullmatch(text):
        fmt = "%Y/%m/%d %H:%M:%S" if " " in text else "%Y/%m/%d"
        try:
            datetime.strptime(text, fmt)
        except ValueError:
            return False
        return True
    return False
