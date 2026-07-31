"""Knowli — human-in-the-loop knowledge capture over a hybrid RAG."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("knowli")
except PackageNotFoundError:
    __version__ = "0.2.0"
