"""The six explainable quality checks."""

import json

import pytest

from smart_inspector import DataInspector
from tests.helpers import column, findings


def test_missingness_uses_a_strict_threshold_and_scales_severity(inspect_file) -> None:
    at_threshold = inspect_file("exact.csv", 'value\n1\n2\n3\n4\n""\n')
    assert findings(at_threshold, "missingness") == []

    above = inspect_file("above.csv", 'value\n1\n2\n3\n""\n""\n')
    warning = findings(above, "missingness", "value")
    assert len(warning) == 1
    assert warning[0]["severity"] == "warning"
    assert warning[0]["affected_records"] == 2
    assert warning[0]["evidence"]["threshold"] == 0.2

    severe = inspect_file(
        "severe.csv",
        "value\n" + "\n".join(["1"] + ['""'] * 9) + "\n",
    )
    error = findings(severe, "missingness", "value")
    assert error[0]["severity"] == "error"
    assert error[0]["evidence"]["missing_fraction"] == 0.9


def test_all_missing_column_is_unknown_and_not_constant(inspect_file) -> None:
    report = inspect_file("blank.csv", "empty,kept\n,1\n,2\n,3\n")
    empty = column(report, "empty")
    assert empty["inferred_type"] == "unknown"
    assert empty["missing_percentage"] == 100
    assert findings(report, "constant_columns", "empty") == []
    assert findings(report, "missingness", "empty")[0]["severity"] == "error"
    assert column(report, "kept")["numeric_summary"]["mean"] == 2.0


def test_duplicates_are_warnings_and_can_be_disabled(inspect_file) -> None:
    text = "a,b\n1,x\n1,x\n2,y\n"
    report = inspect_file("dupes.csv", text)
    found = findings(report, "duplicates")
    assert found[0]["severity"] == "warning"
    assert found[0]["column"] is None
    assert found[0]["scope"] == "dataset"
    assert found[0]["affected_records"] == 1
    assert "does not by itself prove" in found[0]["explanation"]

    disabled = inspect_file("dupes2.csv", text, config={"enabled_checks": ["missingness"]})
    assert findings(disabled, "duplicates") == []
    assert disabled.to_dict()["duplicates"]["extra_duplicate_rows"] == 1


def test_mixed_types_are_errors_and_minority_mismatches_are_warnings(inspect_file) -> None:
    mixed = inspect_file("mixed.csv", "value\n1\n2\n3\nabc\n")
    mixed_finding = findings(mixed, "mixed_types", "value")[0]
    assert mixed_finding["severity"] == "error"
    assert column(mixed, "value")["inferred_type"] == "mixed"
    assert column(mixed, "value")["numeric_summary"] is None
    assert findings(mixed, "outliers") == []

    accepted = inspect_file("mostly.csv", "value\n" + "\n".join([*"12345678", "abc"]) + "\n")
    warning = findings(accepted, "mixed_types", "value")[0]
    assert warning["severity"] == "warning"
    assert warning["affected_records"] == 1
    profile = column(accepted, "value")
    assert profile["inferred_type"] == "integer"
    assert profile["numeric_summary"]["count"] == 8
    assert profile["numeric_summary"]["excluded_non_numeric"] == 1
    assert profile["numeric_summary"]["mean"] == 4.5

    lowered = inspect_file(
        "lowered.csv",
        "value\n1\n2\n3\nabc\n",
        config={"dominance_threshold": 0.7},
    )
    assert column(lowered, "value")["inferred_type"] == "integer"
    assert findings(lowered, "mixed_types", "value")[0]["severity"] == "warning"


def test_iqr_outliers_are_potential_anomalies(inspect_file) -> None:
    report = inspect_file("outliers.csv", "value\n" + "\n".join(["1", "2", "3", "4", "5", "6", "7", "8", "9", "100"]) + "\n")
    found = findings(report, "outliers", "value")
    assert len(found) == 1
    assert found[0]["severity"] == "info"
    evidence = found[0]["evidence"]
    assert evidence["method"] == "iqr"
    assert evidence["q1"] == pytest.approx(3.25)
    assert evidence["q3"] == pytest.approx(7.75)
    assert evidence["iqr"] == pytest.approx(4.5)
    assert evidence["lower_bound"] == pytest.approx(-3.5)
    assert evidence["upper_bound"] == pytest.approx(14.5)
    assert evidence["outlier_count"] == 1
    assert evidence["sample_values"][0]["row"] == 10
    assert evidence["sample_values"][0]["numeric_value"] == 100.0
    assert "not confirmed data errors" in found[0]["explanation"]
    assert "not confirmed" in found[0]["explanation"].lower()
    summary = column(report, "value")["numeric_summary"]
    assert summary["outlier_assessment"] == "completed"
    assert summary["minimum"] == 1
    assert summary["maximum"] == 100


def test_zero_iqr_flags_only_values_outside_the_collapsed_fence(inspect_file) -> None:
    report = inspect_file("flat.csv", "value\n5\n5\n5\n5\n5\n9\n")
    evidence = findings(report, "outliers", "value")[0]["evidence"]
    assert evidence["iqr"] == 0
    assert evidence["outlier_count"] == 1
    assert evidence["sample_values"][0]["numeric_value"] == 9.0
    assert "interquartile range is 0" in findings(report, "outliers", "value")[0]["explanation"]


def test_outlier_check_skips_small_samples_and_respects_multiplier(inspect_file) -> None:
    small = inspect_file("small.csv", "value\n1\n2\n100\n")
    assert findings(small, "outliers") == []
    note = column(small, "value")["numeric_summary"]
    assert note["outlier_assessment"] == "skipped_too_few_values"
    assert note["maximum"] == 100

    wide = inspect_file(
        "wide.csv",
        "value\n" + "\n".join(["1", "2", "3", "4", "5", "6", "7", "8", "9", "100"]) + "\n",
        config={"outlier_multiplier": 100},
    )
    assert findings(wide, "outliers") == []
    assert column(wide, "value")["numeric_summary"]["outlier_assessment"] == "completed"


def test_constant_and_high_cardinality_checks(inspect_file) -> None:
    report = inspect_file(
        "labels.csv",
        "source,label,code\n"
        "lab,red,a\n"
        "lab,blue,b\n"
        "lab,red,c\n"
        "lab,blue,d\n"
        "lab,red,e\n"
        "lab,blue,f\n",
    )
    constant = findings(report, "constant_columns", "source")[0]
    assert constant["severity"] == "warning"
    assert constant["evidence"]["constant_value"] == "lab"
    assert constant["affected_records"] == 6
    assert column(report, "label")["categorical_summary"]["most_frequent_value"] == "red"
    assert findings(report, "high_cardinality", "label") == []
    high = findings(report, "high_cardinality", "code")[0]
    assert high["severity"] == "info"
    assert high["affected_records"] == 6
    assert high["evidence"]["distinct_ratio"] == 1
    assert "not evidence that the values are incorrect" in high["explanation"]

    quiet = inspect_file(
        "quiet.csv",
        "code\na\nb\nc\nd\ne\na\n",
        config={"high_cardinality_threshold": 0.9},
    )
    assert column(quiet, "code")["inferred_type"] == "categorical"
    assert findings(quiet, "high_cardinality") == []


def test_long_text_is_not_a_high_cardinality_category(inspect_file) -> None:
    sentence = "This comment is definitely longer than forty characters"
    rows = "\n".join(f"{sentence} {index}" for index in range(6))
    report = inspect_file("text.csv", f"comment\n{rows}\n")
    assert column(report, "comment")["inferred_type"] == "string"
    assert findings(report, "high_cardinality") == []


def test_constant_column_with_missing_values(inspect_file) -> None:
    report = inspect_file("partial.csv", 'flag\nlab\n""\nlab\n')
    found = findings(report, "constant_columns", "flag")[0]
    assert found["evidence"]["non_missing_count"] == 2
    assert found["evidence"]["missing_count"] == 1


def test_disabling_outliers_keeps_the_numeric_summary(inspect_file) -> None:
    text = "value\n" + "\n".join(["1", "2", "3", "4", "5", "6", "7", "8", "9", "100"]) + "\n"
    report = inspect_file("values.csv", text, config={"enabled_checks": ["missingness"]})
    assert findings(report) == []
    summary = column(report, "value")["numeric_summary"]
    assert summary["maximum"] == 100
    assert summary["outlier_assessment"] == "disabled"


def test_huge_integers_do_not_crash(write_text) -> None:
    payload = [{"n": 10**1000}, {"n": 10**1000}, {"n": 10**1000}, {"n": 10**1000 + 1}]
    path = write_text("huge.json", json.dumps(payload))
    report = DataInspector(path).inspect()
    summary = column(report, "n")["numeric_summary"]
    assert summary["minimum"] == 10**1000
    assert summary["maximum"] == 10**1000 + 1
    assert summary["mean"] is None
    assert summary["outlier_assessment"] == "skipped_non_finite"
    json.loads(report.to_json())


def test_unexpected_samples_are_capped(inspect_file) -> None:
    rows = ["1"] * 20 + [f"bad{index}" for index in range(12)]
    report = inspect_file("many.csv", "value\n" + "\n".join(rows) + "\n")
    profile = column(report, "value")
    assert profile["inferred_type"] == "mixed"
    assert profile["unexpected_count"] == 12
    assert profile["unexpected_distinct_count"] == 12
    assert len(profile["unexpected_values"]) == 10
    evidence = findings(report, "mixed_types", "value")[0]["evidence"]
    assert evidence["sample_truncated"] is True


def test_long_unexpected_text_is_truncated(inspect_file) -> None:
    report = inspect_file("long.csv", f"value\n1\n2\n3\n{'z' * 500}\n")
    sample = column(report, "value")["unexpected_values"][0]
    assert sample["truncated"] is True
    assert len(sample["value"]) <= 200
    assert findings(report, "mixed_types", "value")[0]["evidence"]["sample_truncated"] is True
