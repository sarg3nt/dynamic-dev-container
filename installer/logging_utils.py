"""Logging utilities for the Dynamic Dev Container installer.

This module provides TUI-aware logging capabilities including a custom handler
that captures log messages for display in the terminal user interface.
"""

from __future__ import annotations

import logging
import tempfile

from installer.constants import DEBUG_MODE


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

    # Always set root logger to DEBUG level so TUI handler can capture all messages
    root_logger.setLevel(logging.DEBUG)

    # Always add the TUI handler for capturing debug messages (even if not displayed)
    tui_log_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(tui_log_handler)

    if debug_mode:
        # In debug mode, also log to file
        file_handler = logging.FileHandler(tempfile.gettempdir() + "/install_debug.log")
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
    else:
        # In normal mode, only log warnings/errors to file
        file_handler = logging.FileHandler(tempfile.gettempdir() + "/install_debug.log")
        file_handler.setLevel(logging.WARNING)
        root_logger.addHandler(file_handler)

    # Set format for all handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Parameters
    ----------
    name : str
        The name for the logger

    Returns
    -------
    logging.Logger
        Configured logger instance

    """
    return logging.getLogger(name)


# Initialize logging based on debug mode
setup_logging(DEBUG_MODE)
