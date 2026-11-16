"""Type inference and descriptive summaries."""

import pytest

from tests.helpers import column, findings


def test_column_types_are_inferred_without_pandas_dtypes(inspect_file) -> None:
    essay = "This comment is definitely longer than forty characters"
    report = inspect_file(
        "types.csv",
        "\n".join(
            [
                "whole,fraction,flag,when,label,essay,zip,scientific,ambiguous,year,mixed",
                f"1,1.5,true,2024-01-02,red,{essay} aa,007,1.5e1,01/02/2024,2024,1",
                f"2,2.5,false,2024-03-04,blue,{essay} bb,008,2.5e1,03/04/2024,2025,2",
                f"3,3.5,yes,2024/01/09,red,{essay} cc,009,3.0e1,05/06/2024,2026,x",
            ]
        )
        + "\n",
    )
    assert column(report, "whole")["inferred_type"] == "integer"
    assert column(report, "fraction")["inferred_type"] == "float"
    assert column(report, "fraction")["unexpected_count"] == 0
    assert column(report, "flag")["inferred_type"] == "boolean"
    assert column(report, "when")["inferred_type"] == "datetime"
    assert "More than one datetime format" in column(report, "when")["classification_note"]
    assert column(report, "label")["inferred_type"] == "categorical"
    assert column(report, "essay")["inferred_type"] == "string"
    assert column(report, "zip")["inferred_type"] == "categorical"
    assert column(report, "zip")["type_counts"]["integer"] == 0
    assert column(report, "scientific")["inferred_type"] == "float"
    assert column(report, "ambiguous")["inferred_type"] != "datetime"
    assert column(report, "year")["inferred_type"] == "integer"
    mixed = column(report, "mixed")
    assert mixed["inferred_type"] == "mixed"
    assert mixed["dominant_type"] == "integer"
    assert mixed["numeric_summary"] is None
    assert mixed["unexpected_values"][0]["value"] == "x"


def test_numeric_summaries_ignore_missing_values(inspect_file) -> None:
    report = inspect_file("numbers.csv", 'value\n1\n""\n3\n')
    profile = column(report, "value")
    assert profile["inferred_type"] == "integer"
    assert profile["missing_count"] == 1
    assert profile["missing_fraction"] == pytest.approx(1 / 3)
    assert profile["missing_percentage"] == pytest.approx(100 / 3)
    summary = profile["numeric_summary"]
    assert summary["count"] == 2
    assert summary["minimum"] == 1
    assert summary["maximum"] == 3
    assert summary["mean"] == 2.0
    assert summary["excluded_non_numeric"] == 0


def test_float_summary_and_integer_float_mix(inspect_file) -> None:
    floats = inspect_file("floats.csv", "value\n1.5\n2.5\n")
    summary = column(floats, "value")["numeric_summary"]
    assert summary["minimum"] == 1.5
    assert summary["maximum"] == 2.5
    assert summary["mean"] == 2.0

    mixed = inspect_file("mix.csv", "value\n1\n2.5\n")
    profile = column(mixed, "value")
    assert profile["inferred_type"] == "float"
    assert profile["unexpected_count"] == 0
    assert profile["numeric_summary"]["minimum"] == 1.0
    assert profile["numeric_summary"]["maximum"] == 2.5
    assert profile["numeric_summary"]["mean"] == 1.75


def test_zero_false_and_bare_na_are_not_missing(inspect_file) -> None:
    report = inspect_file(
        "kept.csv",
        "count,flag,country,token\n0,false,NA,n/a\n1,true,US,N/A\n0,no,NA,US\n",
    )
    assert column(report, "count")["missing_count"] == 0
    assert column(report, "count")["numeric_summary"]["minimum"] == 0
    assert column(report, "flag")["missing_count"] == 0
    assert column(report, "flag")["inferred_type"] == "boolean"
    country = column(report, "country")
    assert country["missing_count"] == 0
    assert country["categorical_summary"]["most_frequent_value"] == "NA"
    token = column(report, "token")
    assert token["missing_count"] == 2
    assert token["missing_token_counts"] == {"n/a": 2}


def test_whitespace_and_padded_integers(inspect_file) -> None:
    report = inspect_file("padded.csv", "n\n1\n 1\n   \n")
    profile = column(report, "n")
    assert profile["inferred_type"] == "integer"
    assert profile["missing_count"] == 1
    assert profile["missing_token_counts"] == {"<empty>": 1}
    assert profile["unique_non_missing"] == 2
    assert profile["numeric_summary"]["minimum"] == 1
    assert profile["numeric_summary"]["maximum"] == 1
    assert findings(report, "constant_columns") == []


def test_categorical_mode_breaks_ties_by_first_seen_value(inspect_file) -> None:
    report = inspect_file("colors.csv", "label\nred\nblue\nred\nblue\nred\nblue\n")
    summary = column(report, "label")["categorical_summary"]
    assert summary["unique_count"] == 2
    assert summary["most_frequent_value"] == "red"
    assert summary["most_frequent_count"] == 3
    assert summary["most_frequent_percentage"] == 50.0

    swapped = inspect_file("swapped.csv", "label\nblue\nred\nblue\nred\n")
    assert column(swapped, "label")["categorical_summary"]["most_frequent_value"] == "blue"


def test_duplicate_rows_use_exact_typed_comparison(inspect_file) -> None:
    repeated = inspect_file("dupes.csv", "a,b\n1,x\n1,x\n1,x\n2,y\n")
    duplicates = repeated.to_dict()["duplicates"]
    assert duplicates["extra_duplicate_rows"] == 2
    assert duplicates["rows_in_duplicate_groups"] == 3
    assert duplicates["duplicate_group_count"] == 1

    missing = inspect_file("missing_dupes.csv", "a,b\n1,\n1,n/a\n")
    assert missing.to_dict()["duplicates"]["extra_duplicate_rows"] == 1

    typed = inspect_file(
        "typed.json",
        '[{"a": true}, {"a": 1}, {"a": "one"}, {"a": 1.0}]',
    )
    assert typed.to_dict()["duplicates"]["extra_duplicate_rows"] == 0
    counts = column(typed, "a")["type_counts"]
    assert [counts[kind] for kind in ("boolean", "integer", "float", "string")] == [1, 1, 1, 1]


def test_custom_missing_token_replaces_the_default_list(inspect_file) -> None:
    text = "status\nmissing\nnull\n"
    default = inspect_file("default.csv", text)
    assert column(default, "status")["missing_count"] == 1
    custom = inspect_file(
        "custom.csv",
        text,
        config={"missing_tokens": ["missing"]},
    )
    assert column(custom, "status")["missing_count"] == 1
    assert column(custom, "status")["missing_token_counts"] == {"missing": 1}
    assert column(custom, "status")["non_missing_count"] == 1


def test_iso_timestamp_with_z_is_datetime(inspect_file) -> None:
    report = inspect_file(
        "times.csv",
        "when\n2024-01-01T00:00:00Z\n2024-01-02T15:04:05+00:00\n",
    )
    assert column(report, "when")["inferred_type"] == "datetime"


def test_mixed_integer_and_letter_digit_codes_are_categorical(inspect_file) -> None:
    report = inspect_file(
        "codes.csv",
        "group_code\n1\n2\n3\nmm2\n-42m\nA1\n",
    )
    profile = column(report, "group_code")
    assert profile["inferred_type"] == "categorical"
    assert profile["dominant_type"] == "integer"
    assert profile["unexpected_count"] == 0
    assert profile["numeric_summary"] is None
    assert profile["type_counts"]["integer"] == 3
    assert profile["type_counts"]["string"] == 3
    summary = profile["categorical_summary"]
    assert summary["unique_count"] == 6
    assert "short codes rather than measurements" in profile["classification_note"]
    assert "categorical rather than mixed" in profile["classification_note"]
    assert findings(report, "mixed_types") == []
    assert findings(report, "outliers") == []

    native = inspect_file(
        "codes.json",
        '[{"group_code": 1}, {"group_code": 2}, {"group_code": "mm2"}, {"group_code": "-42m"}]',
    )
    native_profile = column(native, "group_code")
    assert native_profile["inferred_type"] == "categorical"
    assert native_profile["unexpected_count"] == 0
    assert native_profile["numeric_summary"] is None


def test_one_alphabetic_pattern_stays_mixed(inspect_file) -> None:
    report = inspect_file(
        "series.csv",
        "value\n1\n2\n3\nbad0\nbad1\n",
    )
    profile = column(report, "value")
    assert profile["inferred_type"] == "mixed"
    assert profile["dominant_type"] == "integer"
    assert profile["numeric_summary"] is None
    assert profile["unexpected_count"] == 2
    assert findings(report, "mixed_types", "value")[0]["severity"] == "error"


def test_accepted_numeric_column_keeps_stray_code_tokens(inspect_file) -> None:
    rows = ["1", "2", "3", "4", "5", "6", "7", "8", "mm2", "-42m"]
    report = inspect_file("measures.csv", "value\n" + "\n".join(rows) + "\n")
    profile = column(report, "value")
    assert profile["inferred_type"] == "integer"
    assert profile["unexpected_count"] == 2
    assert profile["numeric_summary"]["count"] == 8
    assert profile["numeric_summary"]["mean"] == 4.5
    assert findings(report, "mixed_types", "value")[0]["severity"] == "warning"


def test_decimal_measurements_are_not_reclassified_as_codes(inspect_file) -> None:
    report = inspect_file(
        "decimals.csv",
        "value\n1.5\n2.5\n3.5\nmm2\n-42m\n",
    )
    profile = column(report, "value")
    assert profile["inferred_type"] == "mixed"
    assert profile["dominant_type"] == "float"
    assert profile["numeric_summary"] is None


def test_text_majority_code_column_does_not_flag_integer_labels(inspect_file) -> None:
    rows = ["mm2", "mm2", "mm2", "mm2", "-42m", "-42m", "-42m", "-42m", "1", "2"]
    report = inspect_file("labels.csv", "group_code\n" + "\n".join(rows) + "\n")
    profile = column(report, "group_code")
    assert profile["inferred_type"] == "categorical"
    assert profile["dominant_type"] == "string"
    assert profile["unexpected_count"] == 0
    assert profile["categorical_summary"]["most_frequent_value"] == "mm2"
    assert findings(report, "mixed_types") == []


def test_underscore_numbers_stay_text(inspect_file) -> None:
    report = inspect_file("codes.csv", "code\n1_000\n2_000\n")
    assert column(report, "code")["inferred_type"] == "categorical"
    assert column(report, "code")["type_counts"]["integer"] == 0
