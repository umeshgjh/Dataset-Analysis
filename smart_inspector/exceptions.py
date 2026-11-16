"""User-facing inspection errors.

These exceptions carry a message that is safe to show on the command line.
The original cause is chained for developers who re-run with ``--debug``.
"""


class InspectionError(Exception):
    """Base class for errors an ordinary user should see without a traceback."""


class ConfigError(InspectionError):
    """The inspection configuration is missing, unknown, or out of range."""


class FileInputError(InspectionError):
    """The input path cannot be opened as a dataset file."""


class UnsupportedFormatError(FileInputError):
    """The file extension is not a supported dataset format."""


class ParseError(InspectionError):
    """The file exists but is not a usable CSV or JSON dataset."""


class EmptyDataError(InspectionError):
    """The file parsed, but it does not contain any rows to inspect."""
