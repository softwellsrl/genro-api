"""Genro API - API utilities and FastAPI integration for Genro framework."""

from .decorators import apiready
from .publisher import Publisher

__version__ = "0.1.0"

__all__ = ["apiready", "Publisher"]
