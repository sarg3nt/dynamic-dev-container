"""Dependency management utilities for the Dynamic Dev Container installer.

This module handles checking and installing required Python packages
for the installer application.
"""

from __future__ import annotations

import subprocess
import sys


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
