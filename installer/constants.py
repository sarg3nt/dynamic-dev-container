"""Constants used throughout the Dynamic Dev Container installer."""

from __future__ import annotations

import os

# Global debug flag - can be set via environment variable or command line
DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")

# Parallel processing configuration
DEFAULT_WORKER_COUNT = 8  # Optimal for I/O-bound API calls (GitHub, Homebrew, etc.)

# Tool parsing constants
TOOL_ASSIGNMENT_PARTS = 2  # Expected parts in tool = version assignment

# Constants
MIN_VERSION_PARTS = 2
VERSION_BUTTON_PARTS = 4
MAX_DEBUG_MESSAGES = 50  # Maximum number of debug messages to display at once

# Screen constants for command line navigation (internal 0-based)
SCREEN_WELCOME = 0
SCREEN_CONFIG = 1
SCREEN_TOOLS = 2
SCREEN_EXTENSIONS = 3
SCREEN_SUMMARY = 4
SCREEN_INSTALL = 5
MAX_SCREEN = SCREEN_INSTALL

# Extension item constants (internal 0-based)
MAX_EXTENSION_ITEM = 3  # 0=Github, 1=Markdown, 2=Shell/Bash, 3=PSI Header

# User-facing constants (1-based)
USER_SCREEN_MIN = 1
USER_SCREEN_MAX = 6  # 1=Welcome, 2=Config, 3=Tools, 4=Extensions, 5=Summary, 6=Install
USER_ITEM_MIN = 1
USER_ITEM_MAX = 4  # 1=Github, 2=Markdown, 3=Shell/Bash, 4=PSI Header
