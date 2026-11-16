"""Smart Data Inspector: profile a table and explain data-quality findings."""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    raise RuntimeError(
        "Smart Data Inspector requires Python 3.11 or newer. "
        f"This interpreter is Python {sys.version.split()[0]}."
    )

from smart_inspector.config import ALL_CHECKS, DEFAULT_MISSING_TOKENS, InspectionConfig
from smart_inspector.exceptions import (
    ConfigError,
    EmptyDataError,
    FileInputError,
    InspectionError,
    ParseError,
    UnsupportedFormatError,
)
from smart_inspector.inspector import DataInspector, inspect
from smart_inspector.models import InspectionReport
from smart_inspector.version import __version__

__all__ = [
    "ALL_CHECKS",
    "DEFAULT_MISSING_TOKENS",
    "ConfigError",
    "DataInspector",
    "EmptyDataError",
    "FileInputError",
    "InspectionConfig",
    "InspectionError",
    "InspectionReport",
    "ParseError",
    "UnsupportedFormatError",
    "__version__",
    "inspect",
]
