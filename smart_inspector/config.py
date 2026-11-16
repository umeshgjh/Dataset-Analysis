"""Validated inspection settings.

The defaults are meant for a first look at an unfamiliar table. Every value
that can change a finding is checked here and copied into the report.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from smart_inspector.exceptions import ConfigError

ALL_CHECKS = (
    "missingness",
    "duplicates",
    "mixed_types",
    "outliers",
    "constant_columns",
    "high_cardinality",
)

# Bare "na" is intentionally absent: it is a common real code, not only a null.
DEFAULT_MISSING_TOKENS = (
    "#n/a",
    "#na",
    "<na>",
    "n/a",
    "nan",
    "nat",
    "none",
    "null",
)

ALLOWED_KEYS = frozenset(
    {
        "missingness_threshold",
        "outlier_method",
        "outlier_multiplier",
        "outlier_min_samples",
        "high_cardinality_threshold",
        "categorical_max_length",
        "dominance_threshold",
        "enabled_checks",
        "missing_tokens",
    }
)


def _as_float(
    name: str,
    value: Any,
    *,
    low: float,
    high: float | None,
    low_inclusive: bool,
    high_inclusive: bool,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number. Got {value!r}.")
    number = float(value)
    if not math.isfinite(number):
        raise ConfigError(f"{name} must be a finite number. Got {value!r}.")
    if low_inclusive:
        if number < low:
            raise ConfigError(f"{name} must be at least {low}. Got {value!r}.")
    elif number <= low:
        raise ConfigError(f"{name} must be greater than {low}. Got {value!r}.")
    if high is not None:
        if high_inclusive:
            if number > high:
                raise ConfigError(f"{name} must be at most {high}. Got {value!r}.")
        elif number >= high:
            raise ConfigError(f"{name} must be less than {high}. Got {value!r}.")
    return number


def _as_int(name: str, value: Any, *, minimum: int) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be an integer. Got {value!r}.")
    if isinstance(value, float):
        if not value.is_integer():
            raise ConfigError(f"{name} must be an integer. Got {value!r}.")
        value = int(value)
    if not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer. Got {value!r}.")
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}. Got {value}.")
    return value


def _normalize_checks(value: Any) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ConfigError(
            "enabled_checks must be a list of check names. "
            f"Valid checks: {', '.join(ALL_CHECKS)}."
        )
    unknown: list[str] = []
    selected: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"Each quality check name must be a string. Got {item!r}.")
        if item not in ALL_CHECKS:
            unknown.append(item)
        else:
            selected.add(item)
    if unknown:
        raise ConfigError(
            "Unknown quality check(s): "
            + ", ".join(unknown)
            + f". Valid checks: {', '.join(ALL_CHECKS)}."
        )
    return tuple(check for check in ALL_CHECKS if check in selected)


def _normalize_tokens(value: Any) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise ConfigError("missing_tokens must be a list of strings.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"Each missing token must be a string. Got {item!r}.")
        token = item.strip().lower()
        if token == "":
            raise ConfigError("A missing token must be a non-empty string.")
        normalized.append(token)
    return tuple(sorted(set(normalized)))


@dataclass(frozen=True)
class InspectionConfig:
    """Settings that control thresholds and which quality checks run.

    ``enabled_checks`` replaces the full set. A custom ``missing_tokens`` list
    also replaces the defaults; it does not append to them. Descriptive
    statistics are still computed when a check is turned off.
    """

    missingness_threshold: float = 0.2
    outlier_method: str = "iqr"
    outlier_multiplier: float = 1.5
    outlier_min_samples: int = 4
    high_cardinality_threshold: float = 0.5
    categorical_max_length: int = 40
    dominance_threshold: float = 0.8
    enabled_checks: tuple[str, ...] = field(default_factory=lambda: ALL_CHECKS)
    missing_tokens: tuple[str, ...] = field(default_factory=lambda: DEFAULT_MISSING_TOKENS)

    def __post_init__(self) -> None:
        missingness = _as_float(
            "missingness_threshold",
            self.missingness_threshold,
            low=0.0,
            high=1.0,
            low_inclusive=True,
            high_inclusive=True,
        )
        if isinstance(self.outlier_method, bool) or not isinstance(self.outlier_method, str):
            raise ConfigError(
                f"outlier_method must be a string. Got {self.outlier_method!r}."
            )
        method = self.outlier_method.strip().lower()
        if method != "iqr":
            raise ConfigError(
                "outlier_method must be 'iqr'. "
                f"Got {self.outlier_method!r}. No other method is implemented."
            )
        multiplier = _as_float(
            "outlier_multiplier",
            self.outlier_multiplier,
            low=0.0,
            high=None,
            low_inclusive=False,
            high_inclusive=True,
        )
        min_samples = _as_int(
            "outlier_min_samples", self.outlier_min_samples, minimum=1
        )
        cardinality = _as_float(
            "high_cardinality_threshold",
            self.high_cardinality_threshold,
            low=0.0,
            high=1.0,
            low_inclusive=False,
            high_inclusive=True,
        )
        max_length = _as_int(
            "categorical_max_length", self.categorical_max_length, minimum=1
        )
        dominance = _as_float(
            "dominance_threshold",
            self.dominance_threshold,
            low=0.5,
            high=1.0,
            low_inclusive=False,
            high_inclusive=True,
        )
        checks = _normalize_checks(self.enabled_checks)
        tokens = _normalize_tokens(self.missing_tokens)
        object.__setattr__(self, "missingness_threshold", missingness)
        object.__setattr__(self, "outlier_method", method)
        object.__setattr__(self, "outlier_multiplier", multiplier)
        object.__setattr__(self, "outlier_min_samples", min_samples)
        object.__setattr__(self, "high_cardinality_threshold", cardinality)
        object.__setattr__(self, "categorical_max_length", max_length)
        object.__setattr__(self, "dominance_threshold", dominance)
        object.__setattr__(self, "enabled_checks", checks)
        object.__setattr__(self, "missing_tokens", tokens)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "InspectionConfig":
        """Build a config from a mapping, rejecting unknown option names."""
        if not isinstance(data, Mapping):
            raise ConfigError("Configuration must be a mapping of option names to values.")
        unknown = sorted(set(data) - ALLOWED_KEYS)
        if unknown:
            raise ConfigError(
                "Unknown configuration option(s): "
                + ", ".join(unknown)
                + ". Valid options: "
                + ", ".join(sorted(ALLOWED_KEYS))
                + "."
            )
        return cls(**{key: data[key] for key in data})

    def to_dict(self) -> dict[str, Any]:
        """Return the validated settings in a JSON-ready form."""
        enabled = list(self.enabled_checks)
        disabled = [check for check in ALL_CHECKS if check not in self.enabled_checks]
        return {
            "missingness_threshold": self.missingness_threshold,
            "outlier_method": self.outlier_method,
            "outlier_multiplier": self.outlier_multiplier,
            "outlier_min_samples": self.outlier_min_samples,
            "high_cardinality_threshold": self.high_cardinality_threshold,
            "categorical_max_length": self.categorical_max_length,
            "dominance_threshold": self.dominance_threshold,
            "enabled_checks": enabled,
            "disabled_checks": disabled,
            "missing_tokens": list(self.missing_tokens),
        }
