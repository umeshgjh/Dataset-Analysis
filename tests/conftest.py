"""Fixtures for synthetic files. Tests do not use external datasets."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from smart_inspector import DataInspector, InspectionReport


@pytest.fixture
def write_text(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write a UTF-8 file under the test temporary directory."""

    def _write(name: str, content: str) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def inspect_file(write_text: Callable[[str, str], Path]) -> Callable[..., InspectionReport]:
    """Write a synthetic file and inspect it."""

    def _inspect(name: str, content: str, config: object | None = None) -> InspectionReport:
        path = write_text(name, content)
        return DataInspector(path, config=config).inspect()  # type: ignore[arg-type]

    return _inspect
