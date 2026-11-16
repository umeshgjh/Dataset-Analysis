"""Checks against the demonstration files and the assignment CSV.

These files live in the repository. The tests do not download data.
"""

from pathlib import Path

from smart_inspector import DataInspector
from tests.helpers import column, findings

ROOT = Path(__file__).resolve().parents[1]


def test_corrupted_observations_trigger_all_six_checks() -> None:
    report = DataInspector(ROOT / "examples" / "corrupted_observations.csv").inspect()
    payload = report.to_dict()
    assert payload["overview"]["row_count"] == 12
    assert payload["duplicates"]["extra_duplicate_rows"] == 1

    group_code = column(report, "group_code")
    assert group_code["inferred_type"] == "categorical"
    assert group_code["unexpected_count"] == 0
    assert group_code["numeric_summary"] is None
    assert group_code["categorical_summary"]["unique_count"] == 5

    missing = findings(report, "missingness", "notes")[0]
    assert missing["severity"] == "warning"
    assert missing["affected_records"] == 6
    assert missing["evidence"]["missing_count"] == 6

    duplicates = findings(report, "duplicates")[0]
    assert duplicates["severity"] == "warning"
    assert duplicates["column"] is None
    assert duplicates["affected_records"] == 1

    score = findings(report, "mixed_types", "score")[0]
    assert score["severity"] == "warning"
    assert score["affected_records"] == 1
    assert score["evidence"]["sample_values"][0]["value"] == "bad"

    batch = findings(report, "mixed_types", "batch")[0]
    assert batch["severity"] == "error"
    assert batch["affected_records"] == 3
    assert column(report, "batch")["inferred_type"] == "mixed"
    assert column(report, "batch")["numeric_summary"] is None

    outlier = findings(report, "outliers", "measurement")[0]
    assert outlier["severity"] == "info"
    assert outlier["affected_records"] == 1
    assert outlier["evidence"]["sample_values"][0]["numeric_value"] == 100
    assert "not confirmed data errors" in outlier["explanation"]

    constant = findings(report, "constant_columns", "site")[0]
    assert constant["severity"] == "warning"
    assert constant["affected_records"] == 12
    assert constant["evidence"]["constant_value"] == "north"
    assert findings(report, "constant_columns", "notes") == []
    assert findings(report, "high_cardinality", "notes") == []
    assert len(payload["findings"]) == 7

    cardinality = findings(report, "high_cardinality", "sample_id")[0]
    assert cardinality["severity"] == "info"
    assert cardinality["affected_records"] == 11
    assert cardinality["evidence"]["distinct_ratio"] == 11 / 12

    assert {item["rule_id"] for item in payload["findings"]} == {
        "missingness",
        "duplicates",
        "mixed_types",
        "outliers",
        "constant_columns",
        "high_cardinality",
    }


def test_lab_observations_are_a_clean_flat_json_table() -> None:
    report = DataInspector(ROOT / "examples" / "lab_observations.json").inspect()
    payload = report.to_dict()
    assert payload["overview"]["row_count"] == 8
    assert payload["overview"]["column_count"] == 6
    assert payload["duplicates"]["extra_duplicate_rows"] == 0
    assert payload["findings"] == []
    assert column(report, "temperature_c")["inferred_type"] == "float"
    assert column(report, "recorded_on")["inferred_type"] == "datetime"
    assert column(report, "passed")["inferred_type"] == "boolean"
    assert column(report, "subject")["categorical_summary"]["most_frequent_value"] == "alpha"


def test_assignment_csv_profile_and_point_group_codes() -> None:
    report = DataInspector(
        ROOT / "datasets" / "materials_piezoelectric_properties.csv"
    ).inspect()
    payload = report.to_dict()
    assert payload["overview"]["row_count"] == 3322
    assert payload["overview"]["column_count"] == 15
    assert payload["duplicates"]["extra_duplicate_rows"] == 0

    point_group = column(report, "point_group")
    assert point_group["inferred_type"] == "categorical"
    assert point_group["unexpected_count"] == 0
    assert point_group["numeric_summary"] is None
    assert point_group["type_counts"]["integer"] == 1313
    assert point_group["type_counts"]["string"] == 2009
    assert point_group["categorical_summary"]["unique_count"] == 21
    assert point_group["categorical_summary"]["most_frequent_value"] == "mm2"
    assert point_group["categorical_summary"]["most_frequent_count"] == 641

    expected_missing = {
        "band_gap": 6,
        "is_metal": 6,
        "formation_energy_per_atom": 6,
        "energy_above_hull": 6,
        "is_stable": 5,
        "theoretical": 5,
    }
    for name, count in expected_missing.items():
        profile = column(report, name)
        assert profile["missing_count"] == count
        assert profile["missing_token_counts"] == {"<empty>": count}

    assert column(report, "e_longitudinal_max")["inferred_type"] == "float"
    assert column(report, "num_atoms_in_cell")["inferred_type"] == "integer"
    assert column(report, "is_metal")["inferred_type"] == "boolean"
    assert column(report, "crystal_system")["inferred_type"] == "categorical"
    assert column(report, "e_longitudinal_max")["numeric_summary"]["minimum"] == 0.0

    rules = {item["rule_id"] for item in payload["findings"]}
    assert rules == {"outliers", "high_cardinality"}
    assert all(item["severity"] == "info" for item in payload["findings"])
    assert findings(report, "mixed_types") == []
    assert findings(report, "high_cardinality", "material_id")[0]["affected_records"] == 3322
    assert findings(report, "high_cardinality", "formula_pretty")[0]["evidence"]["unique_count"] == 2817
