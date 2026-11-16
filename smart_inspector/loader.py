"""Read a CSV or JSON file into an object-dtype table.

Parsing is deliberately strict and does not convert cells. Pandas is used to
hold the aligned table after each column has been stored as an object series.
A preservation check refuses to continue if that step changes a value or its
Python type, because a silent coercion would hide data-quality problems.
"""

from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from smart_inspector.exceptions import (
    EmptyDataError,
    FileInputError,
    ParseError,
    UnsupportedFormatError,
)
from smart_inspector.models import FileInformation
from smart_inspector.values import ABSENT

_FORMATS = {".csv": "csv", ".json": "json"}


@dataclass
class LoadedDataset:
    """A parsed table plus the file facts copied into the report."""

    frame: pd.DataFrame
    file_info: FileInformation


def load_dataset(source: str | Path) -> LoadedDataset:
    """Load a UTF-8 CSV or a JSON array of flat objects.

    Args:
        source: Path to the dataset. A leading ``~`` is expanded.

    Returns:
        The loaded table. Cell values are preserved: CSV cells are strings,
        and JSON scalars keep their JSON types. Missing JSON keys are marked
        so they can be counted separately from JSON null.

    Raises:
        FileInputError: The path is empty, missing, or not a file.
        UnsupportedFormatError: The extension is not ``.csv`` or ``.json``.
        ParseError: The file is binary, not UTF-8, malformed, nested, or has
            no usable column names.
        EmptyDataError: The file has no data rows.
    """
    if not isinstance(source, (str, Path)):
        raise FileInputError("File path must be a string or path.")
    supplied = str(source)
    if supplied.strip() == "":
        raise FileInputError("File path is empty.")
    path = Path(supplied).expanduser()
    if not path.exists():
        raise FileInputError(f"File not found: {supplied}")
    if not path.is_file():
        raise FileInputError(f"Path is a directory, not a file: {supplied}")
    extension = path.suffix.lower()
    if extension not in _FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported file extension '{path.suffix or '(none)'}'. "
            "Use a .csv file with a comma delimiter and a header, or a .json file "
            "containing a top-level array of flat objects."
        )
    try:
        size_bytes = path.stat().st_size
    except OSError as exc:
        raise FileInputError(f"Could not read {supplied}: {exc.strerror}.") from exc
    text = _read_text(path)
    info = FileInformation(
        path=supplied,
        absolute_path=str(path.resolve()),
        name=path.name,
        format=_FORMATS[extension],
        size_bytes=size_bytes,
        encoding="utf-8",
    )
    if text.strip() == "":
        raise EmptyDataError(f"{path.name} is empty.")
    if _FORMATS[extension] == "csv":
        return _load_csv(path, text, info)
    return _load_json(path, text, info)


def _read_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FileInputError(f"Could not read {path}: {exc.strerror}.") from exc
    if b"\x00" in data:
        raise ParseError(
            f"{path.name} contains binary data and cannot be inspected as text."
        )
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError(
            f"{path.name} is not valid UTF-8. A leading byte-order mark is accepted; "
            "other encodings are not."
        ) from exc


def _load_csv(path: Path, text: str, info: FileInformation) -> LoadedDataset:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=",", quotechar='"')
    try:
        header = next(reader)
    except StopIteration as exc:
        raise EmptyDataError(f"{path.name} is empty.") from exc
    except csv.Error as exc:
        raise ParseError(f"Malformed CSV in {path.name}: {exc}.") from exc

    _validate_header(path, header)
    rows: list[list[str]] = []
    try:
        for row in reader:
            if row == []:
                continue
            if len(row) != len(header):
                raise ParseError(
                    f"Malformed CSV in {path.name}: row {reader.line_num} has {len(row)} "
                    f"fields; expected {len(header)} to match the header."
                )
            rows.append(row)
    except csv.Error as exc:
        raise ParseError(f"Malformed CSV in {path.name}: {exc}.") from exc
    if not rows:
        raise EmptyDataError(
            f"{path.name} contains a header but no data rows. There is nothing to inspect."
        )
    columnar = {name: [row[index] for row in rows] for index, name in enumerate(header)}
    return LoadedDataset(frame=_build_frame(list(header), columnar), file_info=info)


def _validate_header(path: Path, header: list[str]) -> None:
    if not header:
        raise ParseError(f"{path.name} has no usable columns.")
    blanks = [str(index) for index, name in enumerate(header, start=1) if name.strip() == ""]
    if blanks:
        raise ParseError(
            f"{path.name} has no usable columns: blank column name at position(s) "
            + ", ".join(blanks)
            + "."
        )
    positions: dict[str, list[int]] = {}
    for index, name in enumerate(header, start=1):
        positions.setdefault(name, []).append(index)
    duplicates = {name: spots for name, spots in positions.items() if len(spots) > 1}
    if duplicates:
        details = "; ".join(
            f"'{name}' at positions {', '.join(str(spot) for spot in spots)}"
            for name, spots in duplicates.items()
        )
        raise ParseError(f"{path.name} has duplicate column names: {details}.")


def _load_json(path: Path, text: str, info: FileInformation) -> LoadedDataset:
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_parse_constant,
        )
    except ParseError:
        raise
    except json.JSONDecodeError as exc:
        hint = ""
        if "Extra data" in exc.msg:
            hint = (
                " JSON Lines is not supported; provide one top-level JSON array of flat objects."
            )
        raise ParseError(
            f"Malformed JSON in {path.name}: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno}).{hint}"
        ) from exc

    if isinstance(payload, dict):
        raise ParseError(
            "Unsupported JSON structure: the root value is an object. "
            "Provide a top-level array of flat objects. Nested documents and JSON Lines "
            "are not supported."
        )
    if not isinstance(payload, list):
        raise ParseError(
            "Unsupported JSON structure: the root value is "
            f"{_json_type_name(payload)}. Provide a top-level array of flat objects."
        )
    if len(payload) == 0:
        raise EmptyDataError(
            f"{path.name} contains an empty JSON array. There are no rows to inspect."
        )

    columns: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            raise ParseError(
                f"Unsupported JSON structure at row {index}: expected an object, "
                f"got {_json_type_name(row)}."
            )
        for key, value in row.items():
            if not isinstance(key, str) or key.strip() == "":
                raise ParseError(
                    f"{path.name} has no usable columns: blank field name at row {index}."
                )
            _require_scalar(index, key, value)
            if key not in seen:
                seen.add(key)
                columns.append(key)
    if not columns:
        raise ParseError(
            f"{path.name} has no usable columns. The JSON objects did not contain any field names."
        )
    columnar = {
        column: [row[column] if column in row else ABSENT for row in payload]
        for column in columns
    }
    return LoadedDataset(frame=_build_frame(columns, columnar), file_info=info)


def _reject_duplicate_keys(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    keys = [key for key, _value in pairs]
    if len(keys) != len(set(keys)):
        seen: set[Any] = set()
        duplicates: list[Any] = []
        for key in keys:
            if key in seen and key not in duplicates:
                duplicates.append(key)
            seen.add(key)
        rendered = ", ".join(repr(key) for key in duplicates)
        raise ParseError(
            f"Duplicate key(s) {rendered} in a JSON object. Each object must have unique field names."
        )
    return dict(pairs)


def _parse_constant(name: str) -> None:
    if name == "NaN":
        return None
    raise ParseError(
        f"Unsupported JSON number '{name}'. Only finite numbers are supported. "
        "NaN is treated as missing; Infinity is rejected."
    )


def _require_scalar(row_number: int, key: str, value: Any) -> None:
    if isinstance(value, dict):
        raise ParseError(
            f"Unsupported JSON structure at row {row_number}, field {key!r}: "
            "nested objects are not supported. Each row must be a flat object of "
            "scalar values (string, number, boolean, or null)."
        )
    if isinstance(value, list):
        raise ParseError(
            f"Unsupported JSON structure at row {row_number}, field {key!r}: "
            "nested arrays are not supported. Each row must be a flat object of "
            "scalar values (string, number, boolean, or null)."
        )
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ParseError(
            f"Unsupported JSON number in row {row_number}, field {key!r}. "
            "Only finite numbers are supported."
        )
    raise ParseError(
        f"Unsupported JSON structure at row {row_number}, field {key!r}: "
        f"got {_json_type_name(value)}. Nested documents are not supported."
    )


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _build_frame(columns: list[str], columnar: dict[str, list[Any]]) -> pd.DataFrame:
    """Build an object dataframe and refuse any coercion of the stored cells."""
    series = {
        column: pd.Series(columnar[column], dtype=object) for column in columns
    }
    frame = pd.DataFrame(series).reindex(columns=columns)
    if bool(frame.columns.has_duplicates):
        raise ParseError("Duplicate column names were found while building the table.")
    for column in columns:
        actual = frame[column].tolist()
        if not _cells_preserved(columnar[column], actual):
            raise ParseError(
                "Internal error: the table builder changed values in column "
                f"{column!r}. Inspection stopped so those changes could not hide "
                "data-quality problems."
            )
    return frame


def _cells_preserved(original: list[Any], actual: list[Any]) -> bool:
    if len(original) != len(actual):
        return False
    for left, right in zip(original, actual):
        if type(left) is not type(right):
            return False
        if left != right:
            return False
    return True
