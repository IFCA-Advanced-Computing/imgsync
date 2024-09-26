"""Glance imgsync tool."""

from contextlib import suppress
import importlib.metadata
import pathlib


__version__ = "2.0.1"


def extract_version() -> str:
    """Return either the version of the package installed."""
    with suppress(FileNotFoundError, StopIteration):
        root_dir = pathlib.Path(__file__).parent.parent.parent
        with open(root_dir / "pyproject.toml", encoding="utf-8") as pyproject_toml:
            version = (
                next(line for line in pyproject_toml if line.startswith("version"))
                .split("=")[1]
                .strip("'\"\n ")
            )
            return f"{version}-dev (at {root_dir})"
    return importlib.metadata.version(__package__ or __name__.split(".", maxsplit=1)[0])
