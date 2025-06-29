"""Domain Drop Tracker - A Python CLI tool for monitoring domain availability."""

__version__ = "0.1.0"

from domain_tracker.core import DomainCheckService
from domain_tracker.settings import Settings

__all__ = ["DomainCheckService", "Settings", "__version__"]
