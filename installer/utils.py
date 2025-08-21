"""Utility functions and logging setup for the Dynamic Dev Container installer.

This module contains logging handlers, setup functions, and utility classes
used throughout the installer application.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from typing import Protocol

# Global debug flag - can be set via environment variable or command line
DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")

# Parallel processing configuration
DEFAULT_WORKER_COUNT = 8  # Optimal for I/O-bound API calls (GitHub, Homebrew, etc.)

# Constants for screen debugging
MAX_DEBUG_MESSAGES = 50  # Maximum number of debug messages to display at once


# Define a protocol for our app interface
class DevContainerApp(Protocol):
    """Protocol defining the interface needed by screens."""

    def after_welcome(self, result: None = None) -> None:
        """Handle completion of the welcome screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_project_config(self, result: None = None) -> None:
        """Handle completion of the project config screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_tool_selection(self, result: None = None) -> None:
        """Handle completion of the tool selection screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_python_repository(self, result: None = None) -> None:
        """Handle completion of the Python repository screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_python_project(self, result: None = None) -> None:
        """Handle completion of the Python project screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_tool_versions(self, result: None = None) -> None:
        """Handle completion of the tool versions screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_psi_header(self, result: None = None) -> None:
        """Handle completion of the PSI header screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_summary(self, result: None = None) -> None:
        """Handle completion of the summary screen.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...


class TUILogHandler(logging.Handler):
    """Custom logging handler that captures messages for TUI display."""

    def __init__(self) -> None:
        """Initialize the TUI log handler.

        Initializes the logging handler with an empty message list and sets
        the maximum number of stored messages to prevent memory growth.

        """
        super().__init__()
        self.messages: list[str] = []
        self.max_messages = 100  # Keep only the last 100 messages

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by storing it for TUI display.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to emit

        """
        try:
            msg = self.format(record)
            self.messages.append(msg)
            # Keep only the most recent messages
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)
        except Exception:
            self.handleError(record)

    def get_messages(self) -> list[str]:
        """Get all captured log messages.

        Returns
        -------
        list[str]
            A copy of all captured log messages

        """
        return self.messages.copy()

    def clear_messages(self) -> None:
        """Clear all captured messages.

        Removes all stored log messages from the handler's message list.

        """
        self.messages.clear()


# Global TUI log handler for debug output
tui_log_handler = TUILogHandler()


def setup_logging(debug_mode: bool = False) -> None:
    """Set up logging configuration based on debug mode.

    Parameters
    ----------
    debug_mode : bool, optional
        Whether to enable debug mode with file logging, by default False

    """
    # Clear any existing handlers to prevent duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    if debug_mode:
        # In debug mode, set root logger to DEBUG level for all messages
        root_logger.setLevel(logging.DEBUG)

        # Add console handler for debug output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

        # Add the TUI handler for capturing all debug messages
        tui_log_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(tui_log_handler)

        # Also log to file in debug mode
        file_handler = logging.FileHandler(tempfile.gettempdir() + "/install_debug.log")
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    else:
        # In normal mode, set root logger to WARNING level to suppress debug/info messages
        root_logger.setLevel(logging.WARNING)

        # Set our app logger to INFO level - NO debug messages generated at all
        app_logger = logging.getLogger("installer")
        app_logger.setLevel(logging.INFO)
        app_logger.handlers.clear()
        app_logger.propagate = True  # Let messages go to root logger

        # Add TUI handler to capture INFO+ messages for debug panel (not debug level!)
        tui_log_handler.setLevel(logging.INFO)
        app_logger.addHandler(tui_log_handler)

        # Only log warnings/errors to file in normal mode
        file_handler = logging.FileHandler(tempfile.gettempdir() + "/install_debug.log")
        file_handler.setLevel(logging.WARNING)
        root_logger.addHandler(file_handler)

    # Set format for all handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    # Also format the TUI handler if it's attached to our app logger
    if not debug_mode:
        app_logger = logging.getLogger("installer")
        for handler in app_logger.handlers:
            handler.setFormatter(formatter)


def check_and_install_dependencies() -> None:
    """Check for required dependencies and install them if needed.

    Raises
    ------
    SystemExit
        If dependencies cannot be installed after multiple attempts

    """
    required_packages = [
        ("textual", "textual[dev]>=0.41.0"),
        ("rich", "rich>=13.0.0"),
        ("toml", "toml>=0.10.0"),
        ("pyperclip", "pyperclip>=1.9.0"),
        ("types-pyperclip", "types-pyperclip>=1.9.0"),
    ]

    missing_packages = []

    for package_name, package_spec in required_packages:
        try:
            __import__(package_name)
        except ImportError:
            missing_packages.append(package_spec)

    if missing_packages:
        print("Installing required dependencies...")
        print(f"Missing packages: {', '.join(missing_packages)}")

        # Try to install using pip
        cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            print("Please install manually:")
            for package in missing_packages:
                print(f"  python -m pip install {package}")
            sys.exit(1)


# Initialize logging based on debug mode
setup_logging(DEBUG_MODE)
logger = logging.getLogger(__name__)
