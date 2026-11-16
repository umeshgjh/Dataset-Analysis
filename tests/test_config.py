"""Configuration validation."""

import pytest

from smart_inspector import (
    ALL_CHECKS,
    DEFAULT_MISSING_TOKENS,
    ConfigError,
    InspectionConfig,
)


def test_defaults_are_conservative() -> None:
    config = InspectionConfig()
    assert config.missingness_threshold == 0.2
    assert config.outlier_method == "iqr"
    assert config.outlier_multiplier == 1.5
    assert config.outlier_min_samples == 4
    assert config.high_cardinality_threshold == 0.5
    assert config.dominance_threshold == 0.8
    assert config.enabled_checks == ALL_CHECKS
    assert "na" not in config.missing_tokens
    assert "0" not in config.missing_tokens
    assert "false" not in config.missing_tokens
    assert config.missing_tokens == DEFAULT_MISSING_TOKENS


def test_thresholds_accept_boundaries() -> None:
    config = InspectionConfig(
        missingness_threshold=0,
        high_cardinality_threshold=1,
        dominance_threshold=1,
        outlier_multiplier=0.1,
    )
    assert config.missingness_threshold == 0.0
    assert config.high_cardinality_threshold == 1.0
    assert config.dominance_threshold == 1.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"missingness_threshold": 1.5}, "at most 1"),
        ({"missingness_threshold": -0.01}, "at least 0"),
        ({"missingness_threshold": True}, "must be a number"),
        ({"missingness_threshold": "0.2"}, "must be a number"),
        ({"dominance_threshold": 0.5}, "greater than 0.5"),
        ({"outlier_multiplier": 0}, "greater than 0"),
        ({"outlier_multiplier": -1}, "greater than 0"),
        ({"outlier_method": "zscore"}, "iqr"),
        ({"outlier_method": "IQR"}, None),
        ({"high_cardinality_threshold": 0}, "greater than 0"),
        ({"categorical_max_length": 0}, "at least 1"),
        ({"outlier_min_samples": 1.5}, "integer"),
        ({"outlier_min_samples": True}, "integer"),
        ({"enabled_checks": "missingness"}, "list of check names"),
        ({"enabled_checks": ["not_a_check"]}, "Unknown quality check"),
        ({"missing_tokens": "null"}, "list of strings"),
        ({"missing_tokens": ["null", ""]}, "non-empty"),
        ({"missing_tokens": [1]}, "string"),
    ],
)
def test_invalid_values_are_rejected(kwargs: dict, match: str | None) -> None:
    if match is None:
        config = InspectionConfig(**kwargs)
        assert config.outlier_method == "iqr"
        return
    with pytest.raises(ConfigError, match=match):
        InspectionConfig(**kwargs)


def test_enabled_checks_are_canonicalized() -> None:
    config = InspectionConfig(enabled_checks=["outliers", "missingness", "outliers"])
    assert config.enabled_checks == ("missingness", "outliers")
    assert config.to_dict()["disabled_checks"] == [
        "duplicates",
        "mixed_types",
        "constant_columns",
        "high_cardinality",
    ]


def test_missing_tokens_replace_defaults_and_are_normalized() -> None:
    config = InspectionConfig(missing_tokens=[" NA ", "Missing", "na"])
    assert config.missing_tokens == ("missing", "na")
    assert "null" not in config.missing_tokens


def test_unknown_option_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Unknown configuration option"):
        InspectionConfig.from_mapping({"threshold": 0.1})


def test_mapping_must_be_an_object() -> None:
    with pytest.raises(ConfigError, match="mapping"):
        InspectionConfig.from_mapping(["missingness_threshold"])  # type: ignore[arg-type]


def test_non_finite_threshold_is_rejected() -> None:
    with pytest.raises(ConfigError, match="finite"):
        InspectionConfig(outlier_multiplier=float("inf"))
