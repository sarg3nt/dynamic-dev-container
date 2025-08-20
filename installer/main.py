"""Entry point for the Dynamic Dev Container installer.

This module provides the main() function and command-line interface
for the Dynamic Dev Container TUI installer application.
"""

from __future__ import annotations

import argparse
import sys

from installer import utils
from installer.app import DynamicDevContainerApp
from installer.utils import check_and_install_dependencies, logger, setup_logging


def main() -> None:
    """Main entry point for the Dynamic Dev Container TUI application.

    Parses command line arguments, sets up debugging if requested,
    and launches the Textual TUI application for configuring and
    generating development container configurations.

    Raises
    ------
    KeyboardInterrupt
        When user cancels operation with Ctrl+C
    FileNotFoundError
        When script is not run from dynamic-dev-container directory
    SystemExit
        On unexpected errors or dependency installation failures

    """
    parser = argparse.ArgumentParser(
        description="Dynamic Dev Container TUI Setup - Python Version",
        epilog="This script creates a development container configuration with a Terminal User Interface.",
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        help="Path where the dev container will be created",
    )
    parser.add_argument(
        "--help-extended",
        action="store_true",
        help="Show extended help and examples",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging and debug panel",
    )

    args = parser.parse_args()

    # Update debug mode based on command line argument
    if args.debug:
        utils.DEBUG_MODE = True
        # Reconfigure logging for debug mode
        setup_logging(True)

    if args.help_extended:
        print("""
Dynamic Dev Container TUI Setup

This app creates a new dev container implementation for the tooling environment you select during setup.

Usage: python install.py [project_path] [--debug]

Arguments:
  project_path    Path where the dev container will be created
                  If not provided, you'll be prompted to enter it

Options:
  --debug         Enable debug mode with verbose logging and debug panel
                  Press Ctrl+D in the tool selection screen to toggle debug output

Examples:
  python install.py ~/my-project
  python install.py /workspace/new-project --debug
  python install.py  # Will prompt for path
  DEBUG=true python install.py  # Enable debug via environment variable

Requirements:
  - Python 3.9 or higher
  - Dependencies will be auto-installed: textual, rich, toml

The script must be run from the root of the dynamic-dev-container project
directory where the template files (.devcontainer/devcontainer.json, .mise.toml)
are located.
        """)
        return

    project_path = args.project_path or ""

    try:
        # Check and install dependencies first
        check_and_install_dependencies()

        app = DynamicDevContainerApp(project_path)
        logger.debug("Application starting - Debug functionality available (Ctrl+D)")
        app.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("This script must be run from the root of the dynamic-dev-container project directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
