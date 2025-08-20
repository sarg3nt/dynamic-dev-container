"""Dynamic Dev Container installer package.

A modular TUI application for configuring and generating development
container configurations with dynamic tool selection and management.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Dynamic Dev Container Project"

# Import main classes for external use
from .app import DynamicDevContainerApp
from .config import ProjectConfig
from .main import main

__all__ = [
    "DynamicDevContainerApp",
    "ProjectConfig",
    "main",
]
