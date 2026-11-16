"""File loading, parsing, and input errors."""

import json
from pathlib import Path

import pytest

from smart_inspector import (
    DataInspector,
    EmptyDataError,
    FileInputError,
    ParseError,
    UnsupportedFormatError,
)
from tests.helpers import column


def test_csv_parses_quotes_and_keeps_text(inspect_file) -> None:
    report = inspect_file(
        "people.csv",
        'name,note\n"Doe, Jane","said ""hi"""\n',
    )
    payload = report.to_dict()
    assert payload["overview"]["row_count"] == 1
    assert payload["overview"]["column_names"] == ["name", "note"]
    assert payload["input_file"]["format"] == "csv"
    assert column(report, "name")["categorical_summary"]["most_frequent_value"] == "Doe, Jane"
    assert column(report, "note")["categorical_summary"]["most_frequent_value"] == 'said "hi"'


def test_csv_keeps_embedded_newline_as_text(inspect_file) -> None:
    report = inspect_file("notes.csv", 'note\n"line1\nline2"\n')
    profile = column(report, "note")
    assert profile["inferred_type"] == "string"
    assert "newline" in profile["classification_note"]
    assert profile["categorical_summary"] is None


def test_utf8_names_and_bom(write_text) -> None:
    path = write_text("cities.csv", "cité\né\n")
    report = DataInspector(path).inspect()
    assert column(report, "cité")["categorical_summary"]["most_frequent_value"] == "é"

    bom = write_text("bom.csv", "ignored")
    bom.write_bytes("a,b\n1,2\n".encode("utf-8-sig"))
    bom_report = DataInspector(bom).inspect()
    assert bom_report.to_dict()["overview"]["column_names"] == ["a", "b"]


def test_crlf_csv_duplicates_rows(write_text) -> None:
    path = write_text("crlf.csv", "placeholder")
    path.write_bytes(b"a,b\r\n1,2\r\n1,2\r\n")
    payload = DataInspector(path).inspect().to_dict()
    assert payload["duplicates"]["extra_duplicate_rows"] == 1


def test_json_missing_keys_nulls_zero_and_false(inspect_file) -> None:
    report = inspect_file(
        "rows.json",
        json.dumps(
            [
                {"a": 1, "b": 2, "flag": False, "count": 0},
                {"a": 3, "flag": True, "count": 0, "b": None},
            ]
        ),
    )
    payload = report.to_dict()
    assert payload["overview"]["column_names"] == ["a", "b", "flag", "count"]
    b_column = column(report, "b")
    assert b_column["missing_count"] == 1
    assert b_column["missing_token_counts"] == {"<null>": 1}
    flag = column(report, "flag")
    count = column(report, "count")
    assert flag["missing_count"] == 0
    assert flag["inferred_type"] == "boolean"
    assert count["missing_count"] == 0
    assert count["inferred_type"] == "integer"
    assert count["numeric_summary"]["minimum"] == 0


def test_json_absent_key_is_missing_and_matches_null_for_duplicates(inspect_file) -> None:
    report = inspect_file(
        "absent.json",
        json.dumps(
            [
                {"a": 1, "note": None},
                {"a": 1},
            ]
        ),
    )
    note = column(report, "note")
    assert note["missing_count"] == 2
    assert note["missing_token_counts"] == {"<absent>": 1, "<null>": 1}
    assert report.to_dict()["duplicates"]["extra_duplicate_rows"] == 1


def test_json_nan_is_missing_and_infinity_is_rejected(write_text) -> None:
    nan_path = write_text("nan.json", '[{"a": NaN}]')
    nan_column = column(DataInspector(nan_path).inspect(), "a")
    assert nan_column["inferred_type"] == "unknown"
    assert nan_column["missing_token_counts"] == {"<null>": 1}

    infinity = write_text("infinity.json", '[{"a": Infinity}]')
    with pytest.raises(ParseError, match="Infinity"):
        DataInspector(infinity).inspect()


@pytest.mark.parametrize(
    ("name", "content", "match"),
    [
        ("nested_object.json", '[{"a": {"b": 1}}]', "nested objects"),
        ("nested_array.json", '[{"a": [1, 2]}]', "nested arrays"),
        ("root_object.json", '{"a": 1}', "root value is an object"),
        ("numbers.json", "[1, 2, 3]", "expected an object"),
        ("lines.json", '{"a": 1}\n{"a": 2}\n', "JSON Lines"),
        ("broken.json", "{", "Malformed JSON"),
        ("dupes.json", '[{"a": 1, "a": 2}]', "Duplicate key"),
        ("empty_objects.json", "[{}, {}]", "no usable columns"),
    ],
)
def test_unsupported_or_malformed_json(write_text, name: str, content: str, match: str) -> None:
    path = write_text(name, content)
    with pytest.raises(ParseError, match=match):
        DataInspector(path).inspect()


def test_malformed_csv_field_count_and_quote(write_text) -> None:
    extra = write_text("extra.csv", "a,b\n1,2,3\n")
    with pytest.raises(ParseError, match="expected 2"):
        DataInspector(extra).inspect()
    quote = write_text("quote.csv", 'name,age\n"Alice,30\n')
    with pytest.raises(ParseError, match="Malformed CSV"):
        DataInspector(quote).inspect()


@pytest.mark.parametrize(
    ("name", "content", "error", "match"),
    [
        ("empty.csv", "", EmptyDataError, "empty"),
        ("blank.csv", " \n\n", EmptyDataError, "empty"),
        ("header.csv", "a,b\n", EmptyDataError, "no data rows"),
        ("only.json", "[]", EmptyDataError, "empty JSON array"),
    ],
)
def test_empty_inputs(write_text, name, content, error, match) -> None:
    path = write_text(name, content)
    with pytest.raises(error, match=match):
        DataInspector(path).inspect()


def test_blank_and_duplicate_column_names(write_text) -> None:
    blank = write_text("blank.csv", "a,\n1,2\n")
    with pytest.raises(ParseError, match="no usable columns"):
        DataInspector(blank).inspect()
    duplicate = write_text("dup.csv", "a,a\n1,2\n")
    with pytest.raises(ParseError, match="duplicate column names"):
        DataInspector(duplicate).inspect()


def test_invalid_paths(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(FileInputError, match="File not found"):
        DataInspector(missing).inspect()
    with pytest.raises(FileInputError, match="directory"):
        DataInspector(tmp_path).inspect()
    with pytest.raises(FileInputError, match="empty"):
        DataInspector("  ").inspect()
    text = tmp_path / "notes.txt"
    text.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError, match="Unsupported file extension"):
        DataInspector(text).inspect()
    binary = tmp_path / "binary.csv"
    binary.write_bytes(b"a,b\n1,\x00 2\n")
    with pytest.raises(ParseError, match="binary"):
        DataInspector(binary).inspect()
    invalid = tmp_path / "bad.csv"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(ParseError, match="UTF-8"):
        DataInspector(invalid).inspect()


def test_blank_csv_lines_are_not_rows(inspect_file) -> None:
    report = inspect_file("blank_lines.csv", "a\n1\n\n2\n")
    assert report.to_dict()["overview"]["row_count"] == 2


def test_inspection_does_not_modify_the_file(write_text) -> None:
    path = write_text("kept.csv", "a,b\n1,2\n1,2\n")
    before = path.read_bytes()
    DataInspector(path).inspect()
    assert path.read_bytes() == before
