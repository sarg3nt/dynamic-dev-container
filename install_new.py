#!/usr/bin/env python3
"""Dynamic Dev Container TUI Setup - Entry Point.

This is the main entry point for the Dynamic Dev Container installer.
The functionality has been refactored into modular components in the
installer package for better maintainability.
"""

from __future__ import annotations

# Import the main function from the installer package
from installer.main import main

if __name__ == "__main__":
    main()
