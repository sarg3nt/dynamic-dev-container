#!/usr/bin/env python3
# cspell:ignore gitui cmctl jdxcode sles noconfirm, nerdctl, openbao kubectx kubens krew pybuild tcss kubebench distros
"""Dynamic Dev Container TUI Setup.

A Python Terminal User Interface (TUI) for installing .devcontainer and other files
into a project directory to use the dev container in a new project.

This is a Python conversion of the original install.sh script with enhanced TUI capabilities.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from textual.events import Focus, Key

# Global debug flag - can be set via environment variable or command line
DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")


# Define a protocol for our app interface
class DevContainerApp(Protocol):
    """Protocol defining the interface needed by screens."""

    def after_welcome(self, result: None = None) -> None:
        """Called after welcome screen completes."""

    def after_project_config(self, result: None = None) -> None:
        """Called after project config screen completes."""

    def after_tool_selection(self, result: None = None) -> None:
        """Called after tool selection screen completes."""

    def after_python_repository(self, result: None = None) -> None:
        """Called after Python repository screen completes."""

    def after_python_project(self, result: None = None) -> None:
        """Called after Python project screen completes."""

    def after_tool_versions(self, result: None = None) -> None:
        """Called after tool versions screen completes."""

    def after_psi_header(self, result: None = None) -> None:
        """Called after PSI header screen completes."""

    def after_summary(self, result: None = None) -> None:
        """Called after summary screen completes."""


class TUILogHandler(logging.Handler):
    """Custom logging handler that captures messages for TUI display."""

    def __init__(self) -> None:
        """Initialize the TUI log handler."""
        super().__init__()
        self.messages: list[str] = []
        self.max_messages = 100  # Keep only the last 100 messages

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record by storing it for TUI display."""
        try:
            msg = self.format(record)
            self.messages.append(msg)
            # Keep only the most recent messages
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)
        except Exception:
            self.handleError(record)

    def get_messages(self) -> list[str]:
        """Get all captured log messages."""
        return self.messages.copy()

    def clear_messages(self) -> None:
        """Clear all captured messages."""
        self.messages.clear()


# Global TUI log handler for debug output
tui_log_handler = TUILogHandler()


# Configure logging for debugging
def setup_logging(debug_mode: bool = False) -> None:
    """Set up logging configuration based on debug mode."""
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


# Initialize logging based on debug mode
setup_logging(DEBUG_MODE)
logger = logging.getLogger(__name__)


# Check if required dependencies are available
def check_and_install_dependencies() -> None:
    """Check for required dependencies and install them if needed."""
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


# Install dependencies first
check_and_install_dependencies()

# Now import the required packages
try:
    import pyperclip
    from rich.console import Console
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.css.query import NoMatches
    from textual.screen import ModalScreen, Screen
    from textual.widgets import (
        Button,
        Checkbox,
        Footer,
        Header,
        Input,
        Label,
        Markdown,
        ProgressBar,
        RadioButton,
        RadioSet,
        RichLog,
    )
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    sys.exit(1)


# Constants
MIN_VERSION_PARTS = 2
VERSION_BUTTON_PARTS = 4
MAX_DEBUG_MESSAGES = 50  # Maximum number of debug messages to display at once


class ProjectConfig:
    """Container for project configuration data."""

    def __init__(self) -> None:
        """Initialize the ProjectConfig with default values for project, tool, and extension settings."""
        # Project information
        self.project_path: str = ""
        self.project_name: str = ""
        self.display_name: str = ""
        self.container_name: str = ""
        self.docker_exec_command: str = ""

        # Tool selection
        self.install_sections: list[str] = []
        self.tool_selected: dict[str, bool] = {}
        self.tool_version_configurable: dict[str, bool] = {}
        self.tool_version_value: dict[str, str] = {}

        # Extension flags
        self.include_python_extensions: bool = False
        self.include_markdown_extensions: bool = False
        self.include_shell_extensions: bool = False
        self.include_js_extensions: bool = False

        # Python configuration
        self.install_python_tools: bool = False
        self.install_python_repository: bool = False
        self.python_publish_url: str = "https://upload.pypi.org/legacy/"
        self.python_index_url: str = "https://pypi.org/simple/"
        self.python_extra_index_url: str = ""
        self.python_dev_suffix: str = "dev"
        self.python_prod_suffix: str = "prod"
        self.python_repository_type: str = "PyPI"

        # Python project metadata
        self.python_project_name: str = ""
        self.python_project_description: str = ""
        self.python_author_name: str = ""
        self.python_author_email: str = ""
        self.python_github_username: str = ""
        self.python_github_project: str = ""
        self.python_license: str = ""
        self.python_keywords: str = ""

        # Additional pyproject.toml configuration
        self.python_requires_python: str = ">=3.12"
        self.python_homepage_url: str = ""
        self.python_source_url: str = ""
        self.python_documentation_url: str = ""
        self.python_packages_path: str = ""

        # PSI Header configuration
        self.install_psi_header: bool = False
        self.psi_header_company: str = ""
        self.psi_header_templates: list[tuple[str, str]] = []


class ToolManager:
    """Manages development tools and their versions."""

    @staticmethod
    def detect_container_runtime() -> tuple[str, str] | None:
        """Detect available container runtime."""

        # Check for available container runtimes in order of preference
        if shutil.which("docker"):
            return ("docker", "docker")
        if shutil.which("podman"):
            return ("podman", "podman")
        if shutil.which("nerdctl"):
            return ("nerdctl", "nerdctl")
        return None

    @staticmethod
    def run_container_command(image: str, *args: str) -> str:
        """Run a command in a container using available runtime.

        Parameters
        ----------
        image : str
            Container image to run
        args : str
            Additional command arguments

        Returns
        -------
        str
            Command output or empty string if failed

        """
        runtime_info = ToolManager.detect_container_runtime()
        if not runtime_info:
            return ""

        container_cmd, runtime_type = runtime_info

        try:
            cmd = [container_cmd, "run", "--rm", "--quiet", image] + list(args)
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            if DEBUG_MODE:
                logger.debug("Container command failed for %s: %s", container_cmd, e)

        return ""

    @staticmethod
    def get_tool_versions(tool_name: str) -> list[str]:
        """Get available versions for a tool using mise ls-remote.

        Parameters
        ----------
        tool_name : str
            Name of the tool to get versions for

        Returns
        -------
        list[str]
            List of available versions

        """
        versions_output = ""

        # First try to use mise if installed locally
        if shutil.which("mise"):
            try:
                result = subprocess.run(
                    ["mise", "ls-remote", tool_name],  # noqa: S607
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    versions_output = result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
                if DEBUG_MODE:
                    logger.debug("Local mise command failed for tool %s: %s", tool_name, e)

        # If mise not available or failed, try using container
        if not versions_output:
            versions_output = ToolManager.run_container_command("jdxcode/mise", "mise", "ls-remote", tool_name)

        # Parse versions from output
        lines = versions_output.split("\n")
        versions = []

        for line in lines:
            stripped_line = line.strip()
            # Filter out pre-release versions and non-version lines
            if (
                stripped_line
                and not any(x in stripped_line.lower() for x in ["rc", "alpha", "beta", "dev", "pre"])
                and re.match(r"^\d+\.\d+(\.\d+)?", stripped_line)
            ):
                versions.append(stripped_line)

        return versions

    @staticmethod
    def get_version_list(tool_name: str) -> list[str]:
        """Get latest major versions for a tool, similar to install.sh logic."""
        versions = ToolManager.get_tool_versions(tool_name)

        if not versions:
            return ["latest"]

        # Special handling for Python - get major.minor versions
        if tool_name == "python":
            # Extract major.minor versions (e.g., 3.13, 3.12, 3.11)
            major_minor_versions = set()
            for version in versions:
                parts = version.split(".")
                if len(parts) >= MIN_VERSION_PARTS:
                    major_minor = f"{parts[0]}.{parts[1]}"
                    major_minor_versions.add(major_minor)

            # Sort in reverse order and take top 5
            sorted_versions = sorted(major_minor_versions, key=lambda x: [int(i) for i in x.split(".")], reverse=True)
            return ["latest"] + sorted_versions[:4]  # latest + top 4 versions

        # For tools that use major.minor versioning
        if tool_name in ["kubectl", "go", "golang", "opentofu", "openbao", "packer"]:
            # For versions like 1.31.2, major is 1.31
            major_minor_versions = set()
            for version in versions:
                parts = version.split(".")
                if len(parts) >= MIN_VERSION_PARTS:
                    major_minor = f"{parts[0]}.{parts[1]}"
                    major_minor_versions.add(major_minor)

            # Sort in reverse order and take top 5
            sorted_versions = sorted(major_minor_versions, key=lambda x: [int(i) for i in x.split(".")], reverse=True)
            return ["latest"] + sorted_versions[:4]  # latest + top 4 versions

        # For versions like 22.10.0, major is 22
        major_versions = set()
        for version in versions:
            parts = version.split(".")
            if len(parts) >= 1:
                major_versions.add(parts[0])

        # Sort in reverse order and take top 5
        try:
            sorted_versions = sorted(major_versions, key=int, reverse=True)
        except ValueError:
            # If major versions aren't pure numbers, sort as strings
            sorted_versions = sorted(major_versions, reverse=True)
        return ["latest"] + sorted_versions[:4]  # latest + top 4 versions

    @staticmethod
    def get_latest_major_versions(tool_name: str) -> str:
        """Get latest major versions for a tool (legacy method for compatibility)."""
        versions = ToolManager.get_version_list(tool_name)
        if len(versions) > 1:
            return f"(e.g., {', '.join(versions[1:])})"  # Skip 'latest' for display
        return "(latest version available)"

    @staticmethod
    def get_tool_description(tool: str) -> str:
        """Get description for a development tool."""
        descriptions = {
            "opentofu": "OpenTofu - Open-source Terraform alternative",
            "openbao": "OpenBao - Open-source Vault alternative",
            "packer": "Packer - HashiCorp image builder",
            "gitui": "gitui - Fast terminal UI for git repositories",
            "tealdeer": "tealdeer - Fast implementation of tldr man pages",
            "micro": "micro - Modern terminal-based text editor",
            "powershell": "powershell - Microsoft PowerShell",
            "cosign": "cosign - Container signing tool",
            "kubectl": "kubectl - Kubernetes command-line tool",
            "kubectx": "kubectx - Fast way to switch between clusters",
            "kubens": "kubens - Fast way to switch between namespaces",
            "k9s": "k9s - Terminal UI for Kubernetes clusters",
            "helm": "Helm - The package manager for Kubernetes",
            "krew": "krew - kubectl plugin manager",
            "dive": "dive - Explore Docker image layers and optimize size",
            "kubebench": "kubebench - CIS Kubernetes security benchmark",
            "popeye": "popeye - Kubernetes cluster resource sanitizer",
            "trivy": "trivy - Vulnerability scanner for containers & code",
            "cmctl": "cmctl - CLI for cert-manager certificate management",
            "k3d": "k3d - Lightweight Kubernetes for local development",
            "golang": "golang - Go programming language",
            "golangci-lint": "golangci-lint - Fast Go linters runner",
            "goreleaser": "goreleaser - Release automation tool for Go projects",
            "dotnet": "dotnet - .NET SDK",
            "node": "node - Node.js JavaScript runtime",
            "pnpm": "pnpm - Fast, disk space efficient package manager",
            "yarn": "yarn - Popular alternative package manager",
            "deno": "deno - Secure TypeScript/JavaScript runtime",
            "bun": "bun - Fast all-in-one JavaScript runtime",
            "python": "python - Python programming language",
            "shellcheck": "shellcheck - Shell script static analysis tool",
        }
        return descriptions.get(tool, f"{tool} - Development tool")


class MiseParser:
    """Parser for .mise.toml files."""

    @staticmethod
    def parse_mise_sections(mise_file: Path) -> tuple[list[str], dict[str, bool], dict[str, str], dict[str, bool]]:
        """Parse tool sections from .mise.toml file."""
        if not mise_file.exists():
            return [], {}, {}, {}

        with open(mise_file) as f:
            content = f.read()

        sections = []
        tool_selected = {}
        tool_version_value = {}
        tool_version_configurable = {}

        # Parse sections between markers
        in_tools_section = False
        current_section = None
        lines = content.split("\n")
        previous_line = ""

        for line in lines:
            stripped_line = line.strip()

            if stripped_line == "[tools]":
                in_tools_section = True
                continue

            if in_tools_section and stripped_line.startswith("[") and stripped_line != "[tools]":
                break

            if in_tools_section:
                # Check for section markers (these start with ####)
                begin_match = re.match(r"^#### Begin (.+)$", stripped_line)
                if begin_match:
                    current_section = begin_match.group(1)
                    if current_section not in sections:
                        sections.append(current_section)
                    continue

                end_match = re.match(r"^#### End (.+)$", stripped_line)
                if end_match:
                    current_section = None
                    continue

                # Check for tool definitions (only when we're in a section)
                if current_section:
                    tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", stripped_line)
                    if tool_match:
                        tool_name = tool_match.group(1)
                        tool_selected[tool_name] = False  # Default to not selected
                        tool_version_value[tool_name] = "latest"

                        # Check if previous line had version marker
                        tool_version_configurable[tool_name] = previous_line.strip() == "#version#"

            previous_line = line

        return sections, tool_selected, tool_version_value, tool_version_configurable

    @staticmethod
    def get_section_tools(mise_file: Path, section_name: str) -> list[str]:
        """Get all tools in a specific section."""
        if not mise_file.exists():
            return []

        with open(mise_file) as f:
            content = f.read()

        tools = []
        in_section = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            if stripped_line == f"#### Begin {section_name}":
                in_section = True
                continue

            if stripped_line == f"#### End {section_name}":
                break

            if in_section:
                tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", stripped_line)
                if tool_match:
                    tools.append(tool_match.group(1))

        return tools


class DevContainerParser:
    """Parser for devcontainer.json files to extract extension and settings sections."""

    @staticmethod
    def parse_extension_sections(devcontainer_file: Path) -> list[str]:
        """Parse extension sections from devcontainer.json file."""
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        sections = []
        in_extensions = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for the extensions array
            if '"extensions":' in stripped_line:
                in_extensions = True
                continue

            # Stop when we exit the extensions array
            if in_extensions and stripped_line.startswith('"settings":'):
                break

            if in_extensions:
                # Look for section markers
                begin_match = re.match(r"^//\s*#### Begin (.+) ####", stripped_line)
                if begin_match:
                    section_name = begin_match.group(1)
                    if section_name not in sections and section_name not in ["Github", "Core Extensions", "PSI Header"]:
                        sections.append(section_name)

        return sections

    @staticmethod
    def parse_settings_sections(devcontainer_file: Path) -> list[str]:
        """Parse settings sections from devcontainer.json file."""
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        sections = []
        in_settings = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for the settings object
            if '"settings":' in stripped_line:
                in_settings = True
                continue

            # Stop when we exit the settings object (look for closing brace at same level)
            if (
                in_settings
                and stripped_line == "}"
                and "customizations" in content[content.find('"settings"') : content.find(stripped_line)]
            ):
                break

            if in_settings:
                # Look for section markers that end with "Settings"
                begin_match = re.match(r"^//\s*#### Begin (.+) Settings ####", stripped_line)
                if begin_match:
                    section_name = begin_match.group(1)
                    # Remove "Settings" suffix to match with extension section names
                    base_section_name = section_name
                    if base_section_name not in sections and base_section_name not in [
                        "Core VS Code",
                        "Mise",
                        "Spell Checker",
                        "TODO Tree",
                        "PSI Header",
                    ]:
                        sections.append(base_section_name)

        return sections

    @staticmethod
    def create_section_tool_mapping(mise_file: Path, devcontainer_file: Path) -> dict[str, list[str]]:
        """Create a mapping of sections to tools based on .mise.toml sections."""
        mise_sections, _, _, _ = MiseParser.parse_mise_sections(mise_file)
        _extension_sections = DevContainerParser.parse_extension_sections(devcontainer_file)
        _settings_sections = DevContainerParser.parse_settings_sections(devcontainer_file)

        # Create mapping of section to tools
        section_tool_mapping = {}

        for section in mise_sections:
            tools = MiseParser.get_section_tools(mise_file, section)
            if tools:
                section_tool_mapping[section] = tools

        return section_tool_mapping

    @staticmethod
    def parse_psi_header_languages(devcontainer_file: Path) -> list[tuple[str, str]]:
        """Parse available PSI header languages from devcontainer.json template."""
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        languages = []
        in_psi_templates = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for PSI header templates array
            if '"psi-header.templates":' in stripped_line:
                in_psi_templates = True
                continue

            # Stop when we exit the templates array
            if in_psi_templates and stripped_line == "]":
                break

            if in_psi_templates and '"language":' in stripped_line:
                # Look for language entries
                # Extract language ID (e.g., "python", "javascript")
                match = re.search(r'"language":\s*"([^"]+)"', stripped_line)
                if match:
                    lang_id = match.group(1)
                    # Convert to display name
                    display_names = {
                        "python": "Python (.py)",
                        "javascript": "JavaScript (.js)",
                        "typescript": "TypeScript (.ts)",
                        "go": "Go (.go)",
                        "shellscript": "Shell (.sh)",
                        "powershell": "PowerShell (.ps1)",
                        "csharp": "C# (.cs)",
                        "terraform": "Terraform (.tf)",
                        "yaml": "YAML (.yml)",
                        "json": "JSON (.json)",
                        "markdown": "Markdown (.md)",
                        "dockerfile": "Dockerfile",
                        "env": "Environment (.env)",
                        "*": "Default (all languages)",
                    }
                    display_name = display_names.get(lang_id, f"{lang_id.title()} (.{lang_id})")
                    if lang_id != "*":  # Skip wildcard for selection list
                        languages.append((lang_id, display_name))

        return languages


class FileManager:
    """Manages file operations for the installer."""

    # Files and directories to copy
    FILES_TO_COPY = [
        ".gitignore",
        ".krew_plugins",
        ".packages",
        "cspell.json",
        "dev.sh",
        "package.json",
        "run.sh",
        ".mise.toml",
    ]

    PYTHON_FILES_TO_COPY = [
        "pyproject.toml",
        "requirements.txt",
        "pybuild.py",
    ]

    DIRECTORIES_TO_COPY = [".devcontainer"]

    @staticmethod
    def copy_files_and_directories(source_dir: Path, target_dir: Path, include_python: bool = False) -> None:
        """Copy required files and directories to target."""
        # Copy directories
        for dir_name in FileManager.DIRECTORIES_TO_COPY:
            source_path = source_dir / dir_name
            target_path = target_dir / dir_name

            if source_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)

        # Copy files
        files_to_copy = FileManager.FILES_TO_COPY[:]
        if include_python:
            files_to_copy.extend(FileManager.PYTHON_FILES_TO_COPY)

        for file_name in files_to_copy:
            source_path = source_dir / file_name
            target_path = target_dir / file_name

            if source_path.exists() and not target_path.exists():
                shutil.copy2(source_path, target_path)


class DebugMixin:
    """Mixin class to add debug functionality to screens.

    This mixin should be used with classes that inherit from Screen.
    """

    def get_debug_widget(self) -> Container:
        """Create a debug output widget for the screen."""
        debug_log = RichLog(
            max_lines=50,
            wrap=True,
            highlight=True,
            markup=True,
            id="debug_log",
        )

        # Populate with existing debug messages immediately
        self._populate_debug_log(debug_log)

        return Container(
            Label("Debug Output:", classes="debug-title"),
            debug_log,
            id="debug_container",
            classes="debug-panel",
        )

    def _populate_debug_log(self, debug_log: RichLog) -> None:
        """Populate debug log with current messages."""
        messages = tui_log_handler.get_messages()

        if not messages:
            debug_log.write("[dim]No debug messages available yet. Perform some operations to see debug output.[/dim]")
        else:
            # Show recent messages (last MAX_DEBUG_MESSAGES or all if fewer)
            recent_messages = messages[-MAX_DEBUG_MESSAGES:] if len(messages) > MAX_DEBUG_MESSAGES else messages
            for msg in recent_messages:
                # Ensure message is properly formatted for display
                try:
                    debug_log.write(msg)
                except Exception as e:
                    # If there's an issue with the message, show a safe version
                    debug_log.write(f"[red]Error displaying message: {e}[/red]")

    def update_debug_output(self) -> None:
        """Update the debug output with new messages."""
        try:
            # Use cast to tell mypy this mixin is used with Screen classes
            debug_log = cast("Screen[None]", self).query_one("#debug_log", RichLog)

            # Clear and repopulate to ensure fresh content
            debug_log.clear()
            self._populate_debug_log(debug_log)

            # Force a refresh to ensure content is displayed
            debug_log.refresh()

        except NoMatches:
            # Debug widget not found - this is normal when debug panel isn't shown
            pass
        except Exception as e:
            # Log any other errors for debugging
            logger.debug("Failed to update debug output: %s", e)

    def _rebuild_with_debug_panel(self) -> None:
        """Standard debug panel creation for all screens."""
        try:
            # Try to find a main container with common IDs
            main_container = None
            container_ids = [
                "#welcome-container",
                "#project-container",
                "#summary-container",
                "#install-container",
                "#tools-container",
                "#main-content",
                "#psi-header-container",
            ]

            for container_id in container_ids:
                try:
                    main_container = cast("Screen[None]", self).query_one(container_id)
                    break
                except NoMatches:
                    continue

            if not main_container:
                logger.debug("DebugMixin: Could not find any main container for debug panel")
                return

            # Remove any existing debug container first
            try:
                existing_debug = cast("Screen[None]", self).query_one("#debug_container")
                existing_debug.remove()
                logger.debug("DebugMixin: Removed existing debug container")
            except NoMatches:
                pass  # No existing debug container, which is fine

            # Create the standardized debug panel
            debug_log = RichLog(
                max_lines=50,
                wrap=True,
                highlight=True,
                markup=True,
                id="debug_log",
            )

            # Populate immediately with current messages
            self._populate_debug_log(debug_log)

            debug_container = Container(
                Horizontal(
                    Label("Debug Output (Ctrl+D to toggle):", classes="debug-title"),
                    Button("Copy Debug", id="copy_debug_btn", classes="debug-copy-btn"),
                    id="debug-header",
                ),
                debug_log,
                id="debug_container",
                classes="debug-panel",
            )

            # Mount the debug container
            main_container.mount(debug_container)
            logger.debug("DebugMixin: Debug panel created and mounted successfully")

        except Exception as e:
            logger.debug("DebugMixin: Error creating debug panel: %s", e)

    def _copy_debug_output(self) -> None:
        """Standard debug copy functionality for all screens."""
        try:
            messages = tui_log_handler.get_messages()
            debug_text = "\n".join(messages)
            pyperclip.copy(debug_text)
            cast("Screen[None]", self).notify("Debug output copied to clipboard!", timeout=2, severity="information")
        except Exception as e:
            cast("Screen[None]", self).notify(f"Failed to copy debug output: {e}", timeout=3, severity="error")


class DebugModal(ModalScreen[None]):
    """Modal screen for showing debug output."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+d", "dismiss", "Close"),
        Binding("ctrl+c", "copy_debug", "Copy"),
    ]

    def compose(self) -> ComposeResult:
        """Create the debug modal layout."""
        debug_log = RichLog(
            max_lines=100,
            wrap=True,
            highlight=True,
            markup=True,
            id="modal_debug_log",  # Different ID to avoid conflicts
        )

        # Populate with existing debug messages
        messages = tui_log_handler.get_messages()
        for msg in messages[-50:]:  # Show last 50 messages
            debug_log.write(msg)

        yield Container(
            Container(
                Horizontal(
                    Label("Debug Output (Ctrl+D to close, Ctrl+C to copy)", classes="debug-title"),
                    Button("Copy", id="copy_debug_btn", classes="debug-copy-btn"),
                    Button("Close", id="close_debug_btn", variant="primary"),
                    id="debug-header",
                ),
                debug_log,
                id="debug_content",
                classes="debug-modal-content",
            ),
            id="debug_modal",
            classes="debug-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the debug modal."""
        if event.button.id == "copy_debug_btn":
            self.action_copy_debug()
        elif event.button.id == "close_debug_btn":
            self.dismiss()

    def action_copy_debug(self) -> None:
        """Copy debug output to clipboard."""
        try:
            # Get all debug messages
            messages = tui_log_handler.get_messages()
            debug_text = "\n".join(messages)

            # Try to copy to clipboard
            pyperclip.copy(debug_text)
            self.notify("Debug output copied to clipboard!", timeout=2, severity="information")
        except ImportError:
            self.notify("pyperclip not available - cannot copy to clipboard", timeout=3, severity="warning")
        except Exception as e:
            self.notify(f"Failed to copy debug output: {e}", timeout=3, severity="error")

    async def action_dismiss(self, result: None = None) -> None:
        """Close the debug modal."""
        self.dismiss(result)


class WelcomeScreen(Screen[None], DebugMixin):
    """Welcome screen for the installer."""

    BINDINGS = [
        Binding("enter", "continue", "Continue"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Markdown("""
# Dynamic Dev Container Setup

Welcome to the Dynamic Dev Container TUI Setup!

This wizard will guide you through configuring your development container with the tools and extensions you need.

## Navigation:
- Use **TAB/SHIFT+TAB** to navigate between elements
- Use **SPACE** to select/deselect checkboxes
- Use **ENTER** to confirm selections
- Use **Q** to quit at any time
- Press **Ctrl+D** to view debug output

Press **ENTER** to continue...
            """),
            id="welcome-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("WelcomeScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def action_continue(self) -> None:
        """Continue to the next screen."""
        """Continue to the next screen."""
        # Call the next step directly
        self.app.call_later(self.app.after_welcome)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        """Quit the application."""
        self.app.exit()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
            logger.debug("WelcomeScreen: Removed existing debug panel")
        except NoMatches:
            # Debug panel doesn't exist, create it
            logger.debug("WelcomeScreen: Creating new debug panel")
            self._rebuild_with_debug_panel()
        except Exception as e:
            logger.debug("WelcomeScreen: Error toggling debug panel: %s", e)
            self._rebuild_with_debug_panel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "copy_debug_btn":
            self._copy_debug_output()


class PythonRepositoryScreen(Screen[None]):
    """Screen for configuring Python repository settings."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Python Repository screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Label("Python Project Configuration", classes="title"),
            Label("Configure your Python project settings and repository:"),
            # Project Metadata Section
            Label("Project Metadata:", classes="section-header"),
            Label("Package Name:"),
            Input(
                value=self.config.python_project_name or "my-awesome-project",
                placeholder="Enter package name (lowercase, no spaces)",
                id="project_name",
            ),
            Label("Description:"),
            Input(
                value=self.config.python_project_description or "A brief description of your project",
                placeholder="Enter project description",
                id="project_description",
            ),
            Label("Required Python Version:"),
            Input(
                value=self.config.python_requires_python or ">=3.12",
                placeholder="e.g., >=3.12",
                id="requires_python",
            ),
            Label("Author Name:"),
            Input(
                value=self.config.python_author_name or "Your Name",
                placeholder="Enter author name",
                id="author_name",
            ),
            Label("Author Email:"),
            Input(
                value=self.config.python_author_email or "your.email@example.com",
                placeholder="Enter author email",
                id="author_email",
            ),
            # Project URLs Section
            Label("Project URLs:", classes="section-header"),
            Label("Homepage URL:"),
            Input(
                value=self.config.python_homepage_url or "https://github.com/yourusername/my-awesome-project",
                placeholder="Enter homepage URL",
                id="homepage_url",
            ),
            Label("Source URL:"),
            Input(
                value=self.config.python_source_url or "https://github.com/yourusername/my-awesome-project",
                placeholder="Enter source repository URL",
                id="source_url",
            ),
            # Build Configuration Section
            Label("Build Configuration:", classes="section-header"),
            Label("Package Path:"),
            Input(
                value=self.config.python_packages_path or "src/my_awesome_project",
                placeholder="Enter package path (e.g., src/package_name)",
                id="packages_path",
            ),
            # Repository Configuration Section
            Label("Repository Publishing:", classes="section-header"),
            Label("Repository Type:"),
            Container(
                Checkbox("PyPI (default)", id="repo_pypi", value=True),
                Checkbox("Artifactory", id="repo_artifactory"),
                Checkbox("Nexus", id="repo_nexus"),
                Checkbox("Custom", id="repo_custom"),
                id="repo_types",
            ),
            Label("Package Index URL:"),
            Input(value="https://pypi.org/simple/", id="index_url"),
            Label("Publishing URL:"),
            Input(value="https://upload.pypi.org/legacy/", id="publish_url"),
            Label("Extra Index URL (optional):"),
            Input(placeholder="Additional package index", id="extra_index_url"),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="python-repo-container",
        )
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        """Handle repository type selection - only one can be selected."""
        if event.value:  # If checking this box
            repo_types = ["repo_pypi", "repo_artifactory", "repo_nexus", "repo_custom"]
            for repo_id in repo_types:
                if repo_id != event.checkbox.id:
                    checkbox = self.query_one(f"#{repo_id}", Checkbox)
                    checkbox.value = False

            # Update URLs based on selected repository type
            publish_input = self.query_one("#publish_url", Input)
            index_input = self.query_one("#index_url", Input)

            if event.checkbox.id == "repo_pypi":
                publish_input.value = "https://upload.pypi.org/legacy/"
                index_input.value = "https://pypi.org/simple/"
            elif event.checkbox.id == "repo_artifactory":
                publish_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi-local"
                index_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi/simple"
            elif event.checkbox.id == "repo_nexus":
                publish_input.value = "https://nexus.your-company.com/repository/pypi-hosted/"
                index_input.value = "https://nexus.your-company.com/repository/pypi-group/simple"
            elif event.checkbox.id == "repo_custom":
                publish_input.value = "https://your-custom-repo.com/upload/"
                index_input.value = "https://your-custom-repo.com/simple/"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save Python repository configuration."""
        # Save project metadata
        self.config.python_project_name = self.query_one("#project_name", Input).value or "my-awesome-project"
        self.config.python_project_description = (
            self.query_one("#project_description", Input).value or "A brief description of your project"
        )
        self.config.python_requires_python = self.query_one("#requires_python", Input).value or ">=3.12"
        self.config.python_author_name = self.query_one("#author_name", Input).value or "Your Name"
        self.config.python_author_email = self.query_one("#author_email", Input).value or "your.email@example.com"
        self.config.python_homepage_url = (
            self.query_one("#homepage_url", Input).value or "https://github.com/yourusername/my-awesome-project"
        )
        self.config.python_source_url = (
            self.query_one("#source_url", Input).value or "https://github.com/yourusername/my-awesome-project"
        )
        self.config.python_packages_path = self.query_one("#packages_path", Input).value or "src/my_awesome_project"

        # Determine repository type
        if self.query_one("#repo_pypi", Checkbox).value:
            self.config.python_repository_type = "PyPI"
        elif self.query_one("#repo_artifactory", Checkbox).value:
            self.config.python_repository_type = "Artifactory"
        elif self.query_one("#repo_nexus", Checkbox).value:
            self.config.python_repository_type = "Nexus"
        elif self.query_one("#repo_custom", Checkbox).value:
            self.config.python_repository_type = "Custom"
        else:
            self.config.python_repository_type = "PyPI"  # Default

        # Save URLs and settings
        self.config.python_publish_url = (
            self.query_one("#publish_url", Input).value or "https://upload.pypi.org/legacy/"
        )
        self.config.python_index_url = self.query_one("#index_url", Input).value or "https://pypi.org/simple/"
        self.config.python_extra_index_url = self.query_one("#extra_index_url", Input).value

        self.app.call_later(self.app.after_python_repository)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class PythonProjectScreen(Screen[None]):
    """Screen for Python project metadata configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Python Project screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        # Generate defaults from project name
        default_description = f"A Python project: {self.config.project_name}"
        default_github_project = self.config.project_name.lower().replace(" ", "-")

        yield Header()
        yield Container(
            Label("Python Project Metadata", classes="title"),
            Label("Configure Python project details:"),
            Label("Python Project Name:"),
            Input(value=self.config.project_name, id="python_project_name"),
            Label("Project Description:"),
            Input(value=default_description, id="project_description"),
            Label("Author Name:"),
            Input(placeholder="Your Name", id="author_name"),
            Label("Author Email:"),
            Input(placeholder="your.email@example.com", id="author_email"),
            Label("GitHub Username:"),
            Input(placeholder="your-github-username", id="github_username"),
            Label("GitHub Project Name:"),
            Input(value=default_github_project, id="github_project"),
            Label("License:"),
            Container(
                Checkbox("MIT", id="license_mit", value=True),
                Checkbox("Apache-2.0", id="license_apache"),
                Checkbox("GPL-3.0", id="license_gpl"),
                Checkbox("BSD-3-Clause", id="license_bsd"),
                Checkbox("Other", id="license_other"),
                id="license_types",
            ),
            Label("Keywords (comma-separated):"),
            Input(placeholder="python, package, development", id="keywords"),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="python-project-container",
        )
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        """Handle license selection - only one can be selected."""
        if event.value:  # If checking this box
            license_types = ["license_mit", "license_apache", "license_gpl", "license_bsd", "license_other"]
            for license_id in license_types:
                if license_id != event.checkbox.id:
                    checkbox = self.query_one(f"#{license_id}", Checkbox)
                    checkbox.value = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save Python project metadata."""
        self.config.python_project_name = self.query_one("#python_project_name", Input).value
        self.config.python_project_description = self.query_one("#project_description", Input).value
        self.config.python_author_name = self.query_one("#author_name", Input).value
        self.config.python_author_email = self.query_one("#author_email", Input).value
        self.config.python_github_username = self.query_one("#github_username", Input).value
        self.config.python_github_project = self.query_one("#github_project", Input).value
        self.config.python_keywords = self.query_one("#keywords", Input).value

        # Determine license
        # Determine license
        if self.query_one("#license_mit", Checkbox).value:
            self.config.python_license = "MIT"
        elif self.query_one("#license_apache", Checkbox).value:
            self.config.python_license = "Apache-2.0"
        elif self.query_one("#license_gpl", Checkbox).value:
            self.config.python_license = "GPL-3.0"
        elif self.query_one("#license_bsd", Checkbox).value:
            self.config.python_license = "BSD-3-Clause"
        elif self.query_one("#license_other", Checkbox).value:
            self.config.python_license = "Other"
        else:
            self.config.python_license = "MIT"  # Default

        self.app.call_later(self.app.after_python_project)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class PSIHeaderScreen(Screen[None], DebugMixin):
    """Screen for PSI Header configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig, source_dir: Path) -> None:
        """Initialize the PSI Header screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data
        source_dir : Path
            Source directory for template files

        """
        super().__init__()
        self.config = config
        self.source_dir = source_dir

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        # Get available languages from devcontainer.json template
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        available_languages = DevContainerParser.parse_psi_header_languages(devcontainer_file)

        # Determine which languages should be auto-selected based on selected tools
        auto_selected_languages = self._get_auto_selected_languages()

        yield Header()
        yield Container(
            Label("PSI Header Configuration", classes="title"),
            Label("Configure PSI Header extension for file templates:"),
            Checkbox("Install PSI Header Extension", id="install_psi", value=self.config.install_psi_header),
            Label("Company Name:"),
            Input(placeholder="Your Company Name", id="company_name", value=self.config.psi_header_company),
            Label("Language Templates:"),
            Label("Select languages for custom headers (auto-selected based on your tools):"),
            ScrollableContainer(
                *self._create_language_checkboxes(available_languages, auto_selected_languages),
                id="language-scroll",
            ),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="psi-header-container",
        )
        yield Footer()

    def _get_auto_selected_languages(self) -> set[str]:
        """Get languages that should be auto-selected based on selected tools."""
        auto_selected = set()

        # Mapping of tools to their primary languages
        tool_language_mapping = {
            "python": "python",
            "golang": "go",
            "golangci-lint": "go",
            "goreleaser": "go",
            "node": "javascript",
            "pnpm": "javascript",
            "yarn": "javascript",
            "bun": "javascript",
            "deno": "typescript",
            "dotnet": "csharp",
            "powershell": "powershell",
            "opentofu": "terraform",
            "openbao": "terraform",
            "packer": "terraform",
            "shellcheck": "shellscript",
        }

        # Add languages for selected tools
        for tool, selected in self.config.tool_selected.items():
            if selected and tool in tool_language_mapping:
                auto_selected.add(tool_language_mapping[tool])

        # Always include common languages if any development tools are selected
        if any(self.config.tool_selected.values()):
            auto_selected.update(["shellscript", "markdown"])

        return auto_selected

    def _create_language_checkboxes(
        self,
        available_languages: list[tuple[str, str]],
        auto_selected: set[str],
    ) -> list[Checkbox]:
        """Create checkboxes for available languages with auto-selection."""
        checkboxes = []

        for lang_id, display_name in available_languages:
            # Check if this language should be auto-selected
            is_selected = lang_id in auto_selected

            # Create a checkbox ID
            checkbox_id = f"lang_{lang_id}"

            # Create the checkbox
            checkbox = Checkbox(display_name, id=checkbox_id, value=is_selected)
            checkboxes.append(checkbox)

        return checkboxes

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def save_config(self) -> None:
        """Save PSI Header configuration."""
        self.config.install_psi_header = self.query_one("#install_psi", Checkbox).value
        self.config.psi_header_company = self.query_one("#company_name", Input).value

        # Collect selected language templates from dynamic checkboxes
        self.config.psi_header_templates = []

        # Get available languages from devcontainer.json template
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        available_languages = DevContainerParser.parse_psi_header_languages(devcontainer_file)

        # Check each available language checkbox
        for lang_id, display_name in available_languages:
            checkbox_id = f"lang_{lang_id}"
            try:
                checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                if checkbox.value:
                    # Extract just the language name from display name (e.g., "Python" from "Python (.py)")
                    lang_name = display_name.split(" (")[0] if " (" in display_name else display_name
                    self.config.psi_header_templates.append((lang_id, lang_name))
            except NoMatches:
                # Skip if checkbox doesn't exist
                continue

        self.app.call_later(self.app.after_psi_header)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self._rebuild_with_debug_panel()


class ToolVersionScreen(Screen[None], DebugMixin):
    """Screen for configuring specific tool versions."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Tool Version screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config
        # Get tools that have version configuration enabled
        self.configurable_tools = [
            tool
            for tool, configurable in config.tool_version_configurable.items()
            if configurable and config.tool_selected.get(tool, False)
        ]

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        if not self.configurable_tools:
            yield Container(
                Label("Tool Version Configuration", classes="title"),
                Label("No tools require version configuration."),
                Button("Next", id="next_btn", variant="primary"),
                id="version-container",
            )
        else:
            yield Container(
                Label("Tool Version Configuration", classes="title"),
                Label("Configure specific versions for selected tools:"),
                ScrollableContainer(id="version-scroll"),
                Horizontal(
                    Button("Back", id="back_btn"),
                    Button("Next", id="next_btn", variant="primary"),
                    id="button-row",
                ),
                id="version-container",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Populate version inputs when screen mounts."""
        logger.debug("PSIHeaderScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        if not self.configurable_tools:
            return

        scroll_container = self.query_one("#version-scroll", ScrollableContainer)

        for tool in self.configurable_tools:
            description = ToolManager.get_tool_description(tool)
            version_info = ToolManager.get_latest_major_versions(tool)
            current_version = self.config.tool_version_value.get(tool, "latest")

            scroll_container.mount(Label(f"{tool} - {description}"))
            scroll_container.mount(Label(f"Available versions: {version_info}"))
            scroll_container.mount(
                Input(
                    value=current_version,
                    placeholder="Enter version or 'latest'",
                    id=f"version_{tool}",
                    classes="version-input",  # Add a CSS class for width control
                ),
            )
            scroll_container.mount(Label(""))  # Spacing

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save tool version configurations."""
        for tool in self.configurable_tools:
            version_input = self.query_one(f"#version_{tool}", Input)
            version = version_input.value.strip() or "latest"
            self.config.tool_version_value[tool] = version

        self.app.call_later(self.app.after_tool_versions)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class ProjectConfigScreen(Screen[None], DebugMixin):
    """Screen for project configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Project Config screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        # Generate defaults - handle empty or problematic project paths gracefully
        try:
            if self.config.project_path and self.config.project_path.strip():
                default_name = Path(self.config.project_path).name
            else:
                default_name = "my-project"
        except Exception as e:
            logger.debug("Error parsing project path '%s': %s", self.config.project_path, e)
            default_name = "my-project"

        if not default_name or default_name in [".", ".."]:
            default_name = "my-project"

        default_display = default_name.replace("-", " ").replace("_", " ").title()
        default_container = f"{default_name}-container"

        # Generate docker exec command from display name
        words = default_display.split()
        default_exec = "".join(word[0].lower() for word in words if word) if words else "mp"  # fallback

        yield Header()
        yield ScrollableContainer(
            Label("Project Configuration", classes="title"),
            Label("Enter your project configuration details:"),
            Label("Project Path:"),
            Input(value=self.config.project_path or str(Path.home() / default_name), id="project_path"),
            Label("Project Name:"),
            Input(value=default_name, id="project_name"),
            Label("Display Name:"),
            Input(value=default_display, id="display_name"),
            Label("Container Name:"),
            Input(value=default_container, id="container_name"),
            Label("Docker Exec Command:"),
            Input(value=default_exec, id="docker_command"),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="project-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("ProjectConfigScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_next(self) -> None:
        """Go to next step."""
        """Save configuration and continue."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.push_screen(WelcomeScreen())

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self._rebuild_with_debug_panel()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save the configuration and continue."""
        # Get values from inputs
        self.config.project_path = self.query_one("#project_path", Input).value
        self.config.project_name = self.query_one("#project_name", Input).value
        self.config.display_name = self.query_one("#display_name", Input).value
        self.config.container_name = self.query_one("#container_name", Input).value
        self.config.docker_exec_command = self.query_one("#docker_command", Input).value

        # Validate required fields
        if not self.config.project_name:
            self.notify("Project name is required!", severity="error")
            return

        if not self.config.project_path:
            self.notify("Project path is required!", severity="error")
            return

        # Use project name for display name if empty
        if not self.config.display_name:
            self.config.display_name = self.config.project_name

        # Use default container name if empty
        if not self.config.container_name:
            self.config.container_name = f"{self.config.project_name}-container"

        # Schedule the callback and pop the screen
        self.app.call_later(self.app.after_project_config)  # type: ignore[attr-defined]
        self.app.pop_screen()


class ToolSelectionScreen(Screen[None], DebugMixin):
    """Screen for selecting development tools."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(
        self,
        config: ProjectConfig,
        sections: list[str],
        tool_selected: dict[str, bool],
        tool_version_configurable: dict[str, bool],
        tool_version_value: dict[str, str],
    ) -> None:
        """Initialize the Tool Selection screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data
        sections : list[str]
            List of tool sections from .mise.toml
        tool_selected : dict[str, bool]
            Dictionary tracking which tools are selected
        tool_version_configurable : dict[str, bool]
            Dictionary tracking which tools have configurable versions
        tool_version_value : dict[str, str]
            Dictionary storing version values for tools

        """
        super().__init__()
        self.config = config
        self.sections = sections
        self.tool_selected = tool_selected
        self.tool_version_configurable = tool_version_configurable
        self.tool_version_value = tool_version_value
        self.current_section = 0
        self.show_python_config = False
        self.show_other_config: dict[str, Any] = {}  # Track which tools are being configured
        self._refreshing_config = False  # Flag to prevent concurrent refresh calls
        self._widget_generation = 0  # Track widget generation to prevent ID conflicts
        self._active_version_inputs: set[str] = set()  # Track currently active version input IDs
        self._username_propagated = False  # Track if username has been propagated already
        self._last_focused_input: str = ""  # Track the last focused input for focus loss detection

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        if not self.sections:
            yield Container(
                Label("No tool sections found in .mise.toml", classes="title"),
                Horizontal(
                    Button("Back", id="back_btn"),
                    Button("Next", id="next_btn", variant="primary"),
                    id="button-row",
                ),
                id="tools-container",
            )
        else:
            # Create main layout container with debug panel at bottom if enabled
            layout_components = []

            # Main content area
            main_content = Container(
                Label(
                    f"Development Tools - {self.sections[self.current_section]} - Section {self.current_section + 1} of {len(self.sections)}",
                    classes="title",
                ),
                Horizontal(
                    # Left column for tool selection
                    Container(
                        Label("Available Tools:", classes="column-title"),
                        ScrollableContainer(id="tools-scroll", classes="tools-list"),
                        id="tools-column",
                        classes="left-column",
                    ),
                    # Right column for configuration
                    Container(
                        Label("Configuration:", classes="column-title"),
                        ScrollableContainer(id="config-scroll", classes="config-area"),
                        id="config-column",
                        classes="right-column",
                    ),
                    id="main-layout",
                ),
                Horizontal(
                    Button("Back", id="back_btn"),
                    Button("Previous Section", id="prev_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Section",
                        id="next_section_btn",
                        disabled=self.current_section >= len(self.sections) - 1,
                    ),
                    Button("Finish Tool Selection", id="next_btn", variant="primary"),
                    id="button-row",
                ),
                id="main-content",
            )
            layout_components.append(main_content)

            # Create vertical container with all components
            main_container = Container(*layout_components, id="tools-container")
            yield main_container

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Called when the screen is mounted."""
        logger.debug("ToolSelectionScreen mounted - Debug functionality available (Ctrl+D)")
        self.refresh_tools()
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def refresh_tools(self) -> None:
        """Refresh the tools display for current section."""
        if not self.sections:
            return

        tools_container = self.query_one("#tools-scroll", ScrollableContainer)

        # Only remove children if we need to rebuild (avoid duplicate IDs)
        needs_rebuild = True
        current_section = self.sections[self.current_section]
        tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

        # Check if we can just update existing widgets instead of rebuilding
        try:
            existing_checkboxes = {}
            for widget in tools_container.children:
                if hasattr(widget, "id") and widget.id and widget.id.startswith("tool_"):
                    tool_name = widget.id[5:]  # Remove "tool_" prefix
                    existing_checkboxes[tool_name] = widget

            # If the tools match exactly, we can just update states
            if set(existing_checkboxes.keys()) == set(tools):
                needs_rebuild = False
                # Update existing checkbox states
                for tool in tools:
                    checkbox = existing_checkboxes[tool]
                    cast("Checkbox", checkbox).value = self.tool_selected.get(tool, False)
        except Exception:
            # If anything goes wrong with the check, fall back to rebuild
            needs_rebuild = True

        if needs_rebuild:
            tools_container.remove_children()

        if not tools:
            if needs_rebuild:
                no_tools_label = Label("No tools found in this section", classes="compact")
                tools_container.mount(no_tools_label)
            return

        if needs_rebuild:
            for tool in tools:
                description = ToolManager.get_tool_description(tool)

                # Add checkbox for the tool (no version buttons in left panel anymore)
                checkbox = Checkbox(description, id=f"tool_{tool}", classes="compact")
                checkbox.value = self.tool_selected.get(tool, False)

                tools_container.mount(checkbox)

        # Always handle Python repository configuration if Python is selected
        if "python" in tools and self.tool_selected.get("python", False):
            # Check if repository checkbox already exists
            try:
                tools_container.query_one("#py_repo_enabled")
                repo_checkbox_exists = True
            except Exception:
                repo_checkbox_exists = False

            if not repo_checkbox_exists:
                # Add pyproject.toml configuration checkbox
                repo_checkbox = Checkbox(
                    "Configure pyproject.toml",
                    id="py_repo_enabled",
                    value=self.config.install_python_repository,
                    classes="compact repo-checkbox",
                )
                tools_container.mount(repo_checkbox)

        # Update configuration panel
        self.refresh_configuration()

    def _create_version_buttons(
        self, tool: str, parent_container: Horizontal, version_limit: int | None = None
    ) -> None:
        """Create version buttons for a tool.

        Parameters
        ----------
        tool : str
            The tool name
        parent_container : Container
            The container to mount the buttons to
        version_limit : int | None
            Maximum number of versions to show, None for all

        """
        versions = ToolManager.get_version_list(tool)
        if version_limit:
            versions = versions[:version_limit]

        for version in versions:
            # Replace dots with underscores for valid CSS identifiers
            safe_version = version.replace(".", "_")
            version_btn = Button(
                version,
                id=f"version_btn_{tool}_{safe_version}",
                classes="version-btn-small",
            )
            parent_container.mount(version_btn)

    def _refresh_python_repository_settings(self) -> None:
        """Refresh just the Python repository settings in the left column."""
        # Simply refresh the entire tools display, but with better duplicate prevention
        self.refresh_tools()

    def refresh_configuration(self) -> None:
        """Refresh the configuration panel based on selected tools."""
        # Prevent concurrent calls
        if self._refreshing_config:
            return

        self._refreshing_config = True

        try:
            # Increment generation counter to make IDs unique
            self._widget_generation += 1
            # Clear active version inputs tracking
            self._active_version_inputs.clear()

            config_container = self.query_one("#config-scroll", ScrollableContainer)

            # Clear all children first - this ensures no duplicate IDs
            config_container.remove_children()

            # Force a refresh cycle to ensure widgets are completely removed
            self.call_after_refresh(self._complete_refresh_configuration)
        except Exception as e:
            logger.error("Error in refresh_configuration: %s", e)
            self._refreshing_config = False

    def _complete_refresh_configuration(self) -> None:
        """Complete the configuration refresh after widgets are cleared."""
        try:
            config_container = self.query_one("#config-scroll", ScrollableContainer)

            # Check which tools are selected and need configuration
            if not self.sections:
                config_container.mount(Label("No tools available", classes="compact muted"))
                return

            current_section = self.sections[self.current_section]
            tools_in_current_section = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            # Only show tools that are BOTH selected AND in the current section
            selected_tools_in_section = [
                tool for tool in tools_in_current_section if self.tool_selected.get(tool, False)
            ]

            # Also show summary of ALL selected tools across all sections
            all_selected_tools = [tool for tool, selected in self.tool_selected.items() if selected]

            if not selected_tools_in_section and not all_selected_tools:
                config_container.mount(Label("Select tools to see configuration options", classes="compact muted"))
                return

            # Show current section configuration first
            if selected_tools_in_section and "python" in selected_tools_in_section:
                # Python version configuration (moved to top)
                config_container.mount(Label("Python Version:", classes="compact section-header"))
                python_version = self.tool_version_value.get("python", "latest")

                # Create a horizontal container for Python version
                python_version_container = Horizontal(classes="tool-version-row")
                config_container.mount(python_version_container)

                # Tool name label
                python_version_container.mount(Label("python:", classes="compact tool-label"))

                # Version buttons for Python
                self._create_version_buttons("python", python_version_container, 4)

                # Version input field
                version_id = f"version_python_gen_{self._widget_generation}"
                self._active_version_inputs.add(version_id)
                config_container.mount(
                    Input(
                        value=python_version,
                        placeholder="version or 'latest'",
                        id=version_id,
                        classes="version-input",
                    ),
                )

                # Add pyproject.toml configuration if enabled
                if self.config.install_python_repository:
                    config_container.mount(Label("PyProject.toml Configuration:", classes="compact section-header"))

                    # Project metadata section
                    config_container.mount(Label("Project Metadata:", classes="compact subsection-header"))

                    # Project name
                    config_container.mount(Label("Package Name:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_project_name or "my-awesome-project",
                            placeholder="Enter package name (lowercase, no spaces)",
                            id="pyproject_name",
                            classes="compact-input",
                        ),
                    )

                    # Project description
                    config_container.mount(Label("Description:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_project_description or "A brief description of your project",
                            placeholder="Enter project description",
                            id="pyproject_description",
                            classes="compact-input",
                        ),
                    )

                    # Required Python version
                    config_container.mount(Label("Required Python Version:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_requires_python or ">=3.12",
                            placeholder="e.g., >=3.12",
                            id="pyproject_requires_python",
                            classes="compact-input",
                        ),
                    )

                    # Author name
                    config_container.mount(Label("Author Name:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_author_name or "Your Name",
                            placeholder="Enter author name",
                            id="pyproject_author_name",
                            classes="compact-input",
                        ),
                    )

                    # Author email
                    config_container.mount(Label("Author Email:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_author_email or "your.email@example.com",
                            placeholder="Enter author email",
                            id="pyproject_author_email",
                            classes="compact-input",
                        ),
                    )

                    # Project URLs section
                    config_container.mount(Label("Project URLs:", classes="compact subsection-header"))

                    # Homepage URL
                    config_container.mount(Label("Homepage URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_homepage_url or self._get_default_homepage_url(),
                            placeholder="Enter homepage URL",
                            id="pyproject_homepage",
                            classes="compact-input",
                        ),
                    )

                    # Source URL
                    config_container.mount(Label("Source URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_source_url or self._get_default_source_url(),
                            placeholder="Enter source repository URL",
                            id="pyproject_source",
                            classes="compact-input",
                        ),
                    )

                    # Documentation URL
                    config_container.mount(Label("Documentation URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_documentation_url or self._get_default_documentation_url(),
                            placeholder="Enter documentation URL",
                            id="pyproject_documentation",
                            classes="compact-input",
                        ),
                    )

                    # Build configuration section
                    config_container.mount(Label("Build Configuration:", classes="compact subsection-header"))

                    # Package path
                    config_container.mount(Label("Package Path:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_packages_path or self._get_default_package_path(),
                            placeholder="Enter package path (e.g., src/package_name)",
                            id="pyproject_packages",
                            classes="compact-input",
                        ),
                    )

                    # Repository publishing section
                    config_container.mount(Label("Repository Publishing:", classes="compact subsection-header"))

                    # Repository type selection (improved order: Type -> Index URL -> Publish URL)
                    config_container.mount(Label("Repository Type:", classes="compact"))
                    current_repo_type = self.config.python_repository_type or "PyPI"
                    python_repo_container = Container(
                        RadioSet(
                            RadioButton(
                                "PyPI",
                                id="py_repo_pypi",
                                value=(current_repo_type == "PyPI"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Artifactory",
                                id="py_repo_artifactory",
                                value=(current_repo_type == "Artifactory"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Nexus",
                                id="py_repo_nexus",
                                value=(current_repo_type == "Nexus"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Custom",
                                id="py_repo_custom",
                                value=(current_repo_type == "Custom"),
                                classes="compact",
                            ),
                            id="py_repo_radioset",
                        ),
                        classes="compact-group",
                    )
                    config_container.mount(python_repo_container)

                    # Package index URL (moved up to be right after Repository Type)
                    config_container.mount(Label("Package Index URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_index_url or "https://pypi.org/simple/",
                            placeholder="Enter package index URL",
                            id="pyproject_index_url",
                            classes="compact-input",
                        ),
                    )

                    # Publish URL (moved down to be after Index URL)
                    config_container.mount(Label("Publish URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_publish_url or "https://upload.pypi.org/legacy/",
                            placeholder="Enter publish URL",
                            id="py_publish_url",
                            classes="compact-input",
                        ),
                    )

            # Clean up any existing version inputs before creating new ones
            self._cleanup_version_inputs()

            # Show version configuration ONLY for configurable tools selected in the CURRENT section
            # (not all sections) to keep the interface section-specific
            # Exclude Python since it's handled separately above
            configurable_tools_in_current_section = [
                tool
                for tool in selected_tools_in_section
                if self.tool_version_configurable.get(tool, False) and tool != "python"
            ]

            if configurable_tools_in_current_section:
                config_container.mount(Label("Tool Versions:", classes="compact"))
                for tool in configurable_tools_in_current_section:
                    current_version = self.tool_version_value.get(tool, "latest")

                    # Create a horizontal container for tool name and version buttons
                    tool_version_container = Horizontal(classes="tool-version-row")

                    # Mount the tool version container to config FIRST
                    config_container.mount(tool_version_container)

                    # Now mount child widgets to the mounted container
                    # Tool name label
                    tool_version_container.mount(Label(f"{tool}:", classes="compact tool-label"))

                    # Version buttons - get available versions for this tool dynamically
                    self._create_version_buttons(tool, tool_version_container)

                    # Use generation-based ID to ensure uniqueness
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    self._active_version_inputs.add(version_id)
                    config_container.mount(
                        Input(
                            value=current_version,
                            placeholder="version or 'latest'",
                            id=version_id,
                            classes="version-input",
                        ),
                    )  # Show summary of ALL selected tools across sections

        except Exception as e:
            logger.error("Error in _complete_refresh_configuration: %s", e)
        finally:
            self._refreshing_config = False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes.

        Parameters
        ----------
        event : Checkbox.Changed
            The checkbox change event

        """
        if not event.checkbox.id:
            return

        # Extract tool name from checkbox ID
        if event.checkbox.id.startswith("tool_"):
            tool = event.checkbox.id[5:]  # Remove "tool_" prefix
            self.tool_selected[tool] = event.value

            # If Python tool was toggled, refresh tools display to show/hide repository config
            if tool == "python":
                self.refresh_tools()
            else:
                # Update configuration panel when selections change
                self.refresh_configuration()
        elif event.checkbox.id == "py_repo_enabled":
            # Handle Python repository configuration enable/disable
            self.config.install_python_repository = event.value
            # Refresh repository settings without recreating all tools
            self._refresh_python_repository_settings()
        elif event.checkbox.id.startswith("py_repo_"):
            # Handle Python repository type selection
            if event.value:
                # Uncheck other repository types
                for repo_type in ["py_repo_pypi", "py_repo_artifactory", "py_repo_custom"]:
                    if repo_type != event.checkbox.id:
                        try:
                            checkbox = self.query_one(f"#{repo_type}", Checkbox)
                            checkbox.value = False
                        except Exception as e:
                            # Only log checkbox errors in debug mode
                            logger.debug(
                                "Checkbox '%s' not found during repository type selection: %s",
                                repo_type,
                                e,
                            )

                # Update URL fields based on repository type
                try:
                    publish_input = self.query_one("#py_publish_url", Input)
                    index_input = self.query_one("#py_index_url", Input)

                    if event.checkbox.id == "py_repo_pypi":
                        publish_input.value = "https://upload.pypi.org/legacy/"
                        index_input.value = "https://pypi.org/simple/"
                    elif event.checkbox.id == "py_repo_artifactory":
                        publish_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi-local"
                        index_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi/simple"
                    elif event.checkbox.id == "py_repo_custom":
                        publish_input.value = "https://your-custom-repo.com/upload/"
                        index_input.value = "https://your-custom-repo.com/simple/"

                    # Update the config immediately
                    self.config.python_publish_url = publish_input.value
                    self.config.python_index_url = index_input.value

                except Exception as e:
                    logger.debug("Could not update Python URL fields: %s", e)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio set changes for Python repository type.

        Parameters
        ----------
        event : RadioSet.Changed
            The radio set change event

        """
        if event.radio_set.id == "py_repo_radioset":
            try:
                publish_input = self.query_one("#py_publish_url", Input)
                index_input = self.query_one("#pyproject_index_url", Input)

                if event.pressed.id == "py_repo_pypi":
                    publish_input.value = "https://upload.pypi.org/legacy/"
                    index_input.value = "https://pypi.org/simple/"
                elif event.pressed.id == "py_repo_artifactory":
                    publish_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi-local"
                    index_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi/simple"
                elif event.pressed.id == "py_repo_nexus":
                    publish_input.value = "https://nexus.your-company.com/repository/pypi-hosted/"
                    index_input.value = "https://nexus.your-company.com/repository/pypi-group/simple"
                elif event.pressed.id == "py_repo_custom":
                    publish_input.value = "https://your-custom-repo.com/upload/"
                    index_input.value = "https://your-custom-repo.com/simple/"

                # Update the config immediately
                self.config.python_publish_url = publish_input.value
                self.config.python_index_url = index_input.value

            except Exception as e:
                logger.debug("Could not update Python URL fields: %s", e)

    def _cleanup_version_inputs(self) -> None:
        """Remove any existing version input widgets to prevent duplicates."""
        # Silently clean up version inputs - only log if in debug mode
        if DEBUG_MODE:
            logger.debug("Cleaning up version input widgets")

        try:
            # Find and remove all version input widgets
            for tool in list(self.tool_version_configurable.keys()):
                try:
                    version_widget = self.query_one(f"#version_{tool}", Input)
                    version_widget.remove()
                    if DEBUG_MODE:
                        logger.debug("Removed version widget for tool: %s", tool)
                except Exception as e:
                    # Don't log missing widgets - this is expected behavior
                    if DEBUG_MODE:
                        logger.debug("Version widget for tool %s not found during cleanup: %s", tool, e)
        except Exception as e:
            if DEBUG_MODE:
                logger.debug("Error during version input cleanup: %s", e)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes.

        Parameters
        ----------
        event : Input.Changed
            The input change event

        """
        if not event.input.id:
            return

        if event.input.id.startswith("version_"):
            # Parse generation-based format: version_{tool}_gen_{generation}
            tool = (
                event.input.id.split("_gen_")[0][8:] if "_gen_" in event.input.id else event.input.id[8:]
            )  # Remove "version_" prefix
            self.tool_version_value[tool] = event.value
        elif event.input.id == "py_index_url":
            self.config.python_index_url = event.value
        elif event.input.id == "py_publish_url":
            self.config.python_publish_url = event.value
        elif event.input.id == "pyproject_name":
            # Update package name and related fields when package name changes
            logger.debug("Package name input changed to: %s", event.value)
            self.config.python_project_name = event.value
            # Use call_later to ensure all widgets are mounted before updating
            self.call_later(self._update_package_related_fields, event.value)
        elif event.input.id == "github_username":
            # Handle GitHub username changes - update URL fields immediately on focus loss
            logger.debug("GitHub username input changed to: %s", event.value)
            self.config.python_github_username = event.value
            # Update related URL fields immediately when GitHub username changes
            self.call_later(self._update_github_related_fields, event.value)
        elif event.input.id == "pyproject_homepage":
            # Handle Homepage URL changes - rely on focus-loss detection for immediate processing
            # Store the value but don't set timer - let focus loss handle the propagation
            logger.debug("Homepage URL input changed to: %s", event.value)
            # The actual username propagation will happen on focus loss via _process_input_on_focus_loss()

    def on_focus(self, event: Focus) -> None:
        """Handle focus events to track input focus changes."""
        # Track the currently focused input
        if event.control and hasattr(event.control, "id") and event.control.id:
            self._last_focused_input = event.control.id
            logger.debug("Input gained focus: %s", event.control.id)

    def on_descendant_focus(self, event: Focus) -> None:
        """Handle when focus moves to track focus loss from inputs."""
        # When focus moves from one input to another, process the previous input
        if hasattr(self, "_last_focused_input") and event.control and hasattr(event.control, "id"):
            previous_input_id = self._last_focused_input
            current_input_id = event.control.id if event.control.id else None

            # If focus moved from a tracked input to something else, process the previous input
            if previous_input_id and previous_input_id != current_input_id:
                self._process_input_on_focus_loss(previous_input_id)

            # Update tracked input
            if current_input_id:
                self._last_focused_input = current_input_id

    def _process_input_on_focus_loss(self, input_id: str) -> None:
        """Process specific inputs when they lose focus.

        Parameters
        ----------
        input_id : str
            The ID of the input that lost focus

        """
        try:
            if input_id == "github_username":
                # Process GitHub username immediately on focus loss
                github_input = self.query_one("#github_username", Input)
                github_value = github_input.value.strip()
                if github_value:
                    logger.debug("Processing GitHub username on focus loss: %s", github_value)
                    self.config.python_github_username = github_value
                    self._update_github_related_fields(github_value)

            elif input_id == "pyproject_homepage":
                # Process homepage URL immediately on focus loss (instead of timer)
                if not self._username_propagated:
                    homepage_input = self.query_one("#pyproject_homepage", Input)
                    homepage_value = homepage_input.value.strip()
                    if homepage_value:
                        logger.debug("Processing homepage URL on focus loss: %s", homepage_value)
                        # Cancel any existing timer since we're processing immediately
                        if hasattr(self, "_username_timer"):
                            self._username_timer.stop()
                        self._check_and_propagate_username(homepage_value)

        except Exception as e:
            logger.debug("Error processing input on focus loss (%s): %s", input_id, e)

    def on_key(self, event: Key) -> None:
        """Handle key events for immediate processing."""
        # Check if Enter was pressed in Homepage URL field
        if (
            event.key == "enter"
            and hasattr(self, "app")
            and self.app.focused
            and hasattr(self.app.focused, "id")
            and self.app.focused.id == "pyproject_homepage"
        ):
            # Process Homepage URL immediately when Enter is pressed
            try:
                homepage_input = self.query_one("#pyproject_homepage", Input)
                homepage_value = homepage_input.value.strip()
                if homepage_value and not self._username_propagated:
                    logger.debug("Processing homepage URL on Enter key: %s", homepage_value)
                    self._check_and_propagate_username(homepage_value)
            except Exception as e:
                logger.debug("Error processing homepage URL on Enter: %s", e)

    def _check_and_propagate_username(self, homepage_url: str) -> None:
        """Check if homepage URL contains a valid username and propagate it."""
        logger.debug("Checking homepage URL for username propagation: %s", homepage_url)

        # Only propagate if the URL looks complete (contains github.com and has a slash after username)
        if not homepage_url or "github.com/" not in homepage_url:
            logger.debug("URL not complete enough for propagation")
            return

        try:
            # Extract username from the homepage URL
            username = self._extract_username_from_url(homepage_url)
            if not username or username == "yourusername":
                # No valid username found or still using template
                logger.debug("No valid username found or still using template: %s", username)
                return

            # Check if the URL has a repo name too (should have at least two parts after github.com)
            url_match = re.search(r"github\.com/([^/]+)/(.+)", homepage_url)
            if not url_match:
                logger.debug("URL doesn't have repo name yet, waiting for complete URL")
                return

            logger.debug("Valid username found: %s, propagating to other fields", username)

            # Get other URL fields
            source_input = self.query_one("#pyproject_source", Input)
            documentation_input = self.query_one("#pyproject_documentation", Input)

            # Update source URL if it still uses template username
            if "yourusername" in source_input.value:
                repo_name = url_match.group(2)
                new_source = f"https://github.com/{username}/{repo_name}"
                source_input.value = new_source
                logger.debug("Updated source URL to: %s", new_source)

            # Update documentation URL
            if (
                not documentation_input.value.strip()
                or "yourusername" in documentation_input.value
                or documentation_input.value == self._get_default_documentation_url()
            ):
                repo_name = url_match.group(2)
                new_documentation = f"https://github.com/{username}/{repo_name}/README.md"
                documentation_input.value = new_documentation
                logger.debug("Updated documentation URL to: %s", new_documentation)

            # Mark that username propagation has happened
            self._username_propagated = True
            logger.debug("Username propagation completed, future changes will not propagate")

        except Exception as e:
            logger.debug("Could not check/propagate username: %s", e)
            logger.debug("Traceback: %s", traceback.format_exc())

    def _update_package_related_fields(self, package_name: str) -> None:
        """Update fields that depend on the package name.

        Parameters
        ----------
        package_name : str
            The new package name

        """
        # Always try to update, even for empty package names (to show defaults)
        logger.debug("Updating package-related fields for package name: %s", package_name)

        try:
            # Convert package name to valid formats
            if package_name and package_name.strip():
                package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
                package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            else:
                # Use defaults for empty package name
                package_name_clean = "my_awesome_project"
                package_name_url = "my-awesome-project"

            # Update Homepage URL if it still has the default value
            homepage_input = self.query_one("#pyproject_homepage", Input)
            logger.debug("Current homepage URL: %s", homepage_input.value)

            # Update if it's empty, has the exact default, or looks like a generated URL
            should_update_homepage = (
                not homepage_input.value
                or homepage_input.value == "https://github.com/yourusername/my-awesome-project"
                or "my-awesome-project" in homepage_input.value
                or "yourusername" in homepage_input.value  # Also update if it has the template username
                or homepage_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
            )

            if should_update_homepage:
                new_url = f"https://github.com/yourusername/{package_name_url}"
                homepage_input.value = new_url
                logger.debug("Updated homepage URL to: %s", new_url)

            # Update Source URL if it still has the default value
            source_input = self.query_one("#pyproject_source", Input)
            logger.debug("Current source URL: %s", source_input.value)

            # Update if it's empty, has the exact default, or looks like a generated URL
            should_update_source = (
                not source_input.value
                or source_input.value == "https://github.com/yourusername/my-awesome-project"
                or "my-awesome-project" in source_input.value
                or "yourusername" in source_input.value  # Also update if it has the template username
                or source_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
            )

            if should_update_source:
                new_url = f"https://github.com/yourusername/{package_name_url}"
                source_input.value = new_url
                logger.debug("Updated source URL to: %s", new_url)

            # Update Documentation URL if it still has the default value
            documentation_input = self.query_one("#pyproject_documentation", Input)
            logger.debug("Current documentation URL: %s", documentation_input.value)

            # Update if it's empty, has the exact default, or looks like a generated URL
            should_update_documentation = (
                not documentation_input.value
                or documentation_input.value == "https://github.com/yourusername/my-awesome-project/README.md"
                or "my-awesome-project" in documentation_input.value
                or "yourusername" in documentation_input.value  # Also update if it has the template username
                or documentation_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
            )

            if should_update_documentation:
                new_url = f"https://github.com/yourusername/{package_name_url}/README.md"
                documentation_input.value = new_url
                logger.debug("Updated documentation URL to: %s", new_url)

            # Update Package Path if it still has the default value
            packages_input = self.query_one("#pyproject_packages", Input)
            logger.debug("Current package path: %s", packages_input.value)

            # Update if it's empty, has the exact default, or looks like a generated path
            should_update_path = (
                not packages_input.value
                or packages_input.value == "src/my_awesome_project"
                or "my_awesome_project" in packages_input.value
                or packages_input.value.startswith("src/")  # Any src/ path
            )

            if should_update_path:
                new_path = f"src/{package_name_clean}"
                packages_input.value = new_path
                logger.debug("Updated package path to: %s", new_path)

        except Exception as e:
            # Log errors for debugging
            logger.debug("Could not update package-related fields: %s", e)
            logger.debug("Traceback: %s", traceback.format_exc())

    def _get_default_homepage_url(self) -> str:
        """Get default homepage URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def _get_default_source_url(self) -> str:
        """Get default source URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def _get_default_documentation_url(self) -> str:
        """Get default documentation URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}/README.md"
        return "https://github.com/yourusername/my-awesome-project/README.md"

    def _update_github_related_fields(self, github_username: str) -> None:
        """Update URL fields when GitHub username changes.

        Parameters
        ----------
        github_username : str
            The new GitHub username

        """
        if not github_username or github_username.strip() == "":
            logger.debug("GitHub username is empty, skipping URL updates")
            return

        username = github_username.strip()
        logger.debug("Updating URL fields for GitHub username: %s", username)

        try:
            # Get the current project name for URL construction
            project_name = self.config.python_project_name
            if not project_name or project_name == "my-awesome-project":
                project_name = "my-awesome-project"  # Fallback

            # Clean project name for URL
            project_name_url = project_name.lower().replace("_", "-").replace(" ", "-")

            # Get URL input fields
            try:
                homepage_input = self.query_one("#pyproject_homepage", Input)
            except NoMatches:
                homepage_input = None

            try:
                source_input = self.query_one("#pyproject_source", Input)
            except NoMatches:
                source_input = None

            try:
                documentation_input = self.query_one("#pyproject_documentation", Input)
            except NoMatches:
                documentation_input = None

            # Update Homepage URL if it still has default/template values
            if homepage_input:
                current_homepage = homepage_input.value
                if (
                    not current_homepage.strip()
                    or "yourusername" in current_homepage
                    or current_homepage == "https://github.com/yourusername/my-awesome-project"
                    or current_homepage.startswith("https://github.com/yourusername/")
                ):
                    new_homepage = f"https://github.com/{username}/{project_name_url}"
                    homepage_input.value = new_homepage
                    logger.debug("Updated homepage URL to: %s", new_homepage)

            # Update Source URL if it still has default/template values
            if source_input:
                current_source = source_input.value
                if (
                    not current_source.strip()
                    or "yourusername" in current_source
                    or current_source == "https://github.com/yourusername/my-awesome-project"
                    or current_source.startswith("https://github.com/yourusername/")
                ):
                    new_source = f"https://github.com/{username}/{project_name_url}"
                    source_input.value = new_source
                    logger.debug("Updated source URL to: %s", new_source)

            # Update Documentation URL if it still has default/template values
            if documentation_input:
                current_docs = documentation_input.value
                if (
                    not current_docs.strip()
                    or "yourusername" in current_docs
                    or current_docs == "https://github.com/yourusername/my-awesome-project/README.md"
                    or current_docs.startswith("https://github.com/yourusername/")
                ):
                    new_docs = f"https://github.com/{username}/{project_name_url}/README.md"
                    documentation_input.value = new_docs
                    logger.debug("Updated documentation URL to: %s", new_docs)

        except Exception as e:
            logger.debug("Error updating GitHub-related fields: %s", e)

    def _extract_username_from_url(self, url: str) -> str:
        """Extract username from a GitHub URL.

        Parameters
        ----------
        url : str
            The URL to extract username from

        Returns
        -------
        str
            The extracted username, or empty string if not found

        """
        if not url:
            return ""

        # Match GitHub URLs: https://github.com/username/repo
        github_match = re.search(r"github\.com/([^/]+)", url)
        if github_match:
            return github_match.group(1)

        return ""

    def _get_default_package_path(self) -> str:
        """Get default package path based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
            return f"src/{package_name_clean}"
        return "src/my_awesome_project"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Parameters
        ----------
        event : Button.Pressed
            The button press event

        """
        if not event.button.id:
            return

        button_id = event.button.id

        # Handle version button clicks
        if button_id.startswith("version_btn_"):
            # Extract tool and version from button ID: "version_btn_{tool}_{safe_version}"
            parts = button_id.split("_")
            if len(parts) >= VERSION_BUTTON_PARTS:
                tool = parts[2]
                safe_version = "_".join(parts[3:])  # Handle safe versions that have underscores
                # Convert safe version back to original version (replace underscores with dots)
                version = safe_version.replace("_", ".")

                # Update the tool version value
                self.tool_version_value[tool] = version

                # Update the version input field if it exists
                try:
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    if version_id in self._active_version_inputs:
                        version_input = self.query_one(f"#{version_id}", Input)
                        version_input.value = version
                except Exception as e:
                    logger.debug("Version input widget '%s' not found for tool '%s': %s", version_id, tool, e)
            return

        if button_id == "back_btn":
            self.action_back()
        elif button_id == "prev_btn":
            self.save_current_section()
            self.current_section = max(0, self.current_section - 1)
            self.refresh_controls()
            self.refresh_tools()
        elif button_id == "next_section_btn":
            self.save_current_section()
            self.current_section = min(len(self.sections) - 1, self.current_section + 1)
            self.refresh_controls()
            self.refresh_tools()
        elif button_id == "next_btn":
            self.save_current_section()
            self.finalize_selection()
        elif button_id == "copy_debug_btn":
            self._copy_debug_output()

    def refresh_controls(self) -> None:
        """Refresh button states."""
        prev_btn = self.query_one("#prev_btn", Button)
        next_section_btn = self.query_one("#next_section_btn", Button)

        prev_btn.disabled = self.current_section == 0
        next_section_btn.disabled = self.current_section >= len(self.sections) - 1

        # Update title and subtitle
        title_label = self.query_one("Label", Label)
        title_label.update(f"Development Tools - {self.sections[self.current_section]}")

        # Update subtitle showing section progress
        try:
            subtitle_label = self.query_one("Label.subtitle", Label)
            subtitle_label.update(f"Section {self.current_section + 1} of {len(self.sections)}")
        except Exception as e:
            logger.debug("Subtitle label not found during section update: %s", e)

    def save_current_section(self) -> None:
        """Save selections for current section."""
        if not self.sections:
            return

        current_section = self.sections[self.current_section]
        tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

        for tool in tools:
            try:
                checkbox = self.query_one(f"#tool_{tool}", Checkbox)
                self.tool_selected[tool] = checkbox.value
            except Exception as e:
                logger.debug("Checkbox for tool '%s' not found during save: %s", tool, e)

        # Save any configuration values
        self.save_configuration_values()

    def save_configuration_values(self) -> None:
        """Save current configuration values from input fields."""
        # Save Python repository configuration enable/disable
        try:
            py_repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
            self.config.install_python_repository = py_repo_checkbox.value
        except Exception as e:
            logger.debug("Python repository enabled checkbox not found during save: %s", e)

        # Save Python configuration
        try:
            radio_set = self.query_one("#py_repo_radioset", RadioSet)
            if radio_set.pressed_button:
                if radio_set.pressed_button.id == "py_repo_pypi":
                    self.config.python_repository_type = "PyPI"
                elif radio_set.pressed_button.id == "py_repo_artifactory":
                    self.config.python_repository_type = "Artifactory"
                elif radio_set.pressed_button.id == "py_repo_nexus":
                    self.config.python_repository_type = "Nexus"
                elif radio_set.pressed_button.id == "py_repo_custom":
                    self.config.python_repository_type = "Custom"
        except Exception as e:
            logger.debug("Python repository type radioset not found during save: %s", e)

        try:
            self.config.python_index_url = self.query_one("#pyproject_index_url", Input).value
        except Exception as e:
            logger.debug("Python index URL input not found during save: %s", e)

        try:
            self.config.python_publish_url = self.query_one("#py_publish_url", Input).value
        except Exception as e:
            logger.debug("Python publish URL input not found during save: %s", e)

        # Save additional pyproject.toml configuration
        try:
            self.config.python_project_name = self.query_one("#pyproject_name", Input).value
        except Exception as e:
            logger.debug("Project name input not found during save: %s", e)

        try:
            self.config.python_project_description = self.query_one("#pyproject_description", Input).value
        except Exception as e:
            logger.debug("Project description input not found during save: %s", e)

        try:
            self.config.python_requires_python = self.query_one("#pyproject_requires_python", Input).value
        except Exception as e:
            logger.debug("Required Python version input not found during save: %s", e)

        try:
            self.config.python_author_name = self.query_one("#pyproject_author_name", Input).value
        except Exception as e:
            logger.debug("Author name input not found during save: %s", e)

        try:
            self.config.python_author_email = self.query_one("#pyproject_author_email", Input).value
        except Exception as e:
            logger.debug("Author email input not found during save: %s", e)

        try:
            self.config.python_homepage_url = self.query_one("#pyproject_homepage", Input).value
        except Exception as e:
            logger.debug("Homepage URL input not found during save: %s", e)

        try:
            self.config.python_source_url = self.query_one("#pyproject_source", Input).value
        except Exception as e:
            logger.debug("Source URL input not found during save: %s", e)

        try:
            self.config.python_documentation_url = self.query_one("#pyproject_documentation", Input).value
        except Exception as e:
            logger.debug("Documentation URL input not found during save: %s", e)

        try:
            self.config.python_packages_path = self.query_one("#pyproject_packages", Input).value
        except Exception as e:
            logger.debug("Packages path input not found during save: %s", e)

        # Save version configurations - only for configurable tools in the current section
        # since version inputs are only shown for the current section
        current_section_name = self.sections[self.current_section] if self.sections else None
        if current_section_name:
            current_section_tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section_name)
            configurable_tools_in_current_section = [
                tool
                for tool in current_section_tools
                if (self.tool_version_configurable.get(tool, False) and self.tool_selected.get(tool, False))
            ]

            for tool in configurable_tools_in_current_section:
                try:
                    # Try generation-based ID first
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    version_input = self.query_one(f"#{version_id}", Input)
                    self.tool_version_value[tool] = version_input.value or "latest"
                except Exception as e:
                    logger.debug("Generation-based version input for tool '%s' not found: %s", tool, e)
                    try:
                        # Fallback to simple ID format
                        version_input = self.query_one(f"#version_{tool}", Input)
                        self.tool_version_value[tool] = version_input.value or "latest"
                    except Exception as e:
                        logger.debug("Version input for tool '%s' not found during save: %s", tool, e)

    def finalize_selection(self) -> None:
        """Finalize tool selection and continue."""
        # Save current section before finalizing
        self.save_current_section()

        # Update config with selections
        self.config.tool_selected = self.tool_selected
        self.config.tool_version_configurable = self.tool_version_configurable
        self.config.tool_version_value = self.tool_version_value

        # Set extension flags based on selected tools
        for tool, selected in self.tool_selected.items():
            if selected:
                if tool == "python":
                    self.config.install_python_tools = True
                    self.config.include_python_extensions = True
                elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                    self.config.include_js_extensions = True

        # Always include markdown and shell extensions by default
        self.config.include_markdown_extensions = True
        self.config.include_shell_extensions = True

        # Go directly to tool version configuration or next step
        self.app.call_later(self.app.after_tool_selection)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self._rebuild_with_debug_panel()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_current_section()
        self.finalize_selection()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.push_screen(ProjectConfigScreen(self.config))


class SummaryScreen(Screen[None], DebugMixin):
    """Summary screen showing final configuration."""

    BINDINGS = [
        Binding("enter", "install", "Install"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Summary screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("SummaryScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        summary_text = self.generate_summary()

        yield Header()
        yield Container(
            Label("Configuration Summary", classes="title"),
            ScrollableContainer(
                Markdown(summary_text),
                id="summary-scroll",
            ),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Install", id="install_btn", variant="primary"),
                id="button-row",
            ),
            id="summary-container",
        )
        yield Footer()

    def generate_summary(self) -> str:
        """Generate summary markdown text."""
        summary = "## Project Settings\n\n"
        summary += f"- **Name:** {self.config.project_name}\n"
        summary += f"- **Display Name:** {self.config.display_name}\n"
        summary += f"- **Container:** {self.config.container_name}\n"

        if self.config.docker_exec_command:
            summary += f"- **Exec Command:** {self.config.docker_exec_command}\n"

        # Count selected tools
        selected_tools = [tool for tool, selected in self.config.tool_selected.items() if selected]

        if selected_tools:
            summary += f"\n## Development Tools ({len(selected_tools)} selected)\n\n"
            for tool in selected_tools:
                version = self.config.tool_version_value.get(tool, "latest")
                if version and version != "latest":
                    summary += f"- **{tool}** ({version})\n"
                else:
                    summary += f"- **{tool}** (latest)\n"
        else:
            summary += "\n## Development Tools\nNone selected\n"

        # Extensions
        extensions = []
        if self.config.include_python_extensions:
            extensions.append("Python")
        if self.config.include_markdown_extensions:
            extensions.append("Markdown")
        if self.config.include_shell_extensions:
            extensions.append("Shell/Bash")
        if self.config.include_js_extensions:
            extensions.append("JavaScript/Node.js")
        if self.config.install_psi_header:
            extensions.append("PSI Header")

        summary += f"\n## VS Code Extensions\n\nGitHub + Core + {', '.join(extensions)}\n"

        # Python Configuration
        if self.config.install_python_tools:
            summary += "\n## Python Configuration\n\n"
            summary += f"- **Repository Type:** {self.config.python_repository_type}\n"
            summary += f"- **Publish URL:** {self.config.python_publish_url}\n"
            if self.config.python_index_url:
                summary += f"- **Index URL:** {self.config.python_index_url}\n"
            if self.config.python_extra_index_url:
                summary += f"- **Extra Index URL:** {self.config.python_extra_index_url}\n"

            # Python project metadata
            if self.config.python_project_name:
                summary += "\n### Python Project Details\n"
                summary += f"- **Project Name:** {self.config.python_project_name}\n"
                if self.config.python_project_description:
                    summary += f"- **Description:** {self.config.python_project_description}\n"
                if self.config.python_author_name:
                    summary += f"- **Author:** {self.config.python_author_name}\n"
                if self.config.python_author_email:
                    summary += f"- **Email:** {self.config.python_author_email}\n"
                if self.config.python_github_username:
                    summary += f"- **GitHub User:** {self.config.python_github_username}\n"
                if self.config.python_github_project:
                    summary += f"- **GitHub Project:** {self.config.python_github_project}\n"
                if self.config.python_license:
                    summary += f"- **License:** {self.config.python_license}\n"
                if self.config.python_keywords:
                    summary += f"- **Keywords:** {self.config.python_keywords}\n"

        # PSI Header Configuration
        if self.config.install_psi_header:
            summary += "\n## PSI Header Configuration\n\n"
            if self.config.psi_header_company:
                summary += f"- **Company:** {self.config.psi_header_company}\n"
            if self.config.psi_header_templates:
                template_names = [name for _, name in self.config.psi_header_templates]
                summary += f"- **Language Templates:** {', '.join(template_names)}\n"

        summary += "\n---\n\n**Proceed with installation?**"

        return summary

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "install_btn":
            self.action_install()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_install(self) -> None:
        """Start the installation process."""
        self.app.call_later(self.app.after_summary)  # type: ignore[attr-defined]
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        # Access the main app's parsed data for ToolSelectionScreen

        app = cast("DynamicDevContainerApp", self.app)
        self.app.push_screen(
            ToolSelectionScreen(
                self.config,
                app.sections,
                app.tool_selected,
                app.tool_version_configurable,
                app.tool_version_value,
            ),
        )

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self._rebuild_with_debug_panel()


class InstallationScreen(Screen[None]):
    """Screen showing installation progress."""

    def __init__(self, config: ProjectConfig, source_dir: Path) -> None:
        """Initialize the installation screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data
        source_dir : Path
            Source directory for template files

        """
        super().__init__()
        self.config = config
        self.source_dir = source_dir
        self.progress_step = 0
        self.total_steps = 6

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Label("Installing Dev Container Configuration...", classes="title"),
            ProgressBar(total=self.total_steps, id="progress"),
            Label("Initializing...", id="status"),
            id="install-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Start installation when screen is mounted."""
        self.call_after_refresh(self.start_installation)

    def start_installation(self) -> None:
        """Start the installation process."""
        try:
            self.update_progress("Creating project directory...")
            self.create_project_directory()

            self.update_progress("Copying files and directories...")
            self.copy_files()

            self.update_progress("Generating .mise.toml...")
            self.generate_mise_toml()

            self.update_progress("Generating devcontainer.json...")
            self.generate_devcontainer_json()

            self.update_progress("Updating dev.sh...")
            self.update_dev_sh()

            self.update_progress("Configuring project settings...")
            if self.config.install_python_tools:
                self.update_pyproject_toml()
                self.configure_python_repository_settings()

            if self.config.install_psi_header:
                self.configure_psi_header()

            self.update_progress("Installation completed successfully!")
            self.show_completion()

        except Exception as e:
            self.query_one("#status", Label).update(f"Error: {str(e)}")
            self.notify(f"Installation failed: {str(e)}", severity="error")

    def update_progress(self, status: str) -> None:
        """Update progress bar and status.

        Parameters
        ----------
        status : str
            Progress status message

        """
        self.progress_step += 1
        progress_bar = self.query_one("#progress", ProgressBar)
        status_label = self.query_one("#status", Label)

        progress_bar.update(progress=self.progress_step)
        status_label.update(status)

    def create_project_directory(self) -> None:
        """Create project directory if it doesn't exist."""
        project_path = Path(self.config.project_path)
        project_path.mkdir(parents=True, exist_ok=True)

    def copy_files(self) -> None:
        """Copy files and directories to target."""
        source_dir = self.source_dir
        target_dir = Path(self.config.project_path)

        FileManager.copy_files_and_directories(
            source_dir,
            target_dir,
            include_python=self.config.install_python_tools,
        )

    def generate_mise_toml(self) -> None:
        """Generate custom .mise.toml based on selected tools."""
        source_file = self.source_dir / ".mise.toml"
        target_file = Path(self.config.project_path) / ".mise.toml"

        if not source_file.exists():
            return

        # Read original file
        with open(source_file) as f:
            content = f.read()

        # Generate new content
        lines = []
        lines.append("# Generated by Dynamic Dev Container Setup")
        lines.append("")

        # Add environment section
        in_env = False
        for line in content.split("\n"):
            if line.strip() == "#### Begin Environment":
                in_env = True
                continue
            if line.strip() == "#### End Environment":
                in_env = False
                continue
            if in_env:
                lines.append(line)

        lines.append("")
        lines.append("[tools]")
        lines.append("")

        # Add selected tools by section
        sections, _, _, _ = MiseParser.parse_mise_sections(source_file)

        for section in sections:
            section_tools = MiseParser.get_section_tools(source_file, section)
            selected_tools = [tool for tool in section_tools if self.config.tool_selected.get(tool, False)]

            if selected_tools:
                lines.append(f"#### Begin {section} ####")
                for tool in selected_tools:
                    version = self.config.tool_version_value.get(tool, "latest")
                    lines.append(f"{tool} = '{version}'")
                lines.append(f"#### End {section} ####")
                lines.append("")

        # Add alias and settings sections from original
        in_alias = False
        in_settings = False

        for line in content.split("\n"):
            if line.strip() == "[alias]":
                in_alias = True
                lines.append("")
                lines.append(line)
                continue
            if line.strip() == "[settings]":
                in_settings = True
                lines.append("")
                lines.append(line)
                continue
            if line.strip().startswith("[") and (in_alias or in_settings):
                in_alias = False
                in_settings = False
                continue
            if in_alias or in_settings:
                lines.append(line)

        # Write new file
        with open(target_file, "w") as f:
            f.write("\n".join(lines))

    def generate_devcontainer_json(self) -> None:
        """Generate the devcontainer.json file using manual section-based approach."""
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        target_file = Path(self.config.project_path) / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            msg = f"Source devcontainer.json not found at {source_file}"
            raise Exception(msg)

        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Read the source file as text (preserving all comments and formatting)
        with open(source_file, encoding="utf-8") as f:
            content = f.read()

        # Step 1: Update container references (name, runArgs, mounts) ONLY
        content = self._update_container_references_only(content)

        # Step 2: Remove sections for tools that are NOT selected
        content = self._remove_unselected_tool_sections(content)

        # Step 3: Add PSI Header extension if selected
        if self.config.install_psi_header:
            content = self._ensure_psi_header_section(content)
        else:
            content = self._remove_psi_header_section(content)

        # Step 4: Update containerEnv with Hatch environment variables if Python repository is configured
        if self.config.install_python_repository:
            content = self._update_container_env_hatch_vars(content)

        # Write the result
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _update_container_references_only(self, content: str) -> str:
        """Update ONLY container references, preserving everything else exactly."""

        # Update display name
        content = re.sub(
            r'"name":\s*"[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r'"runArgs":\s*\[\s*"--name=[^"]*"\s*\]',
            f'"runArgs": ["--name={self.config.container_name}"]',
            content,
        )

        # Update mount sources in mounts array
        content = re.sub(
            r'"source":\s*"[^"]*-shellhistory"',
            f'"source": "{self.config.container_name}-shellhistory"',
            content,
        )
        return re.sub(
            r'"source":\s*"[^"]*-plugins"',
            f'"source": "{self.config.container_name}-plugins"',
            content,
        )

    def _remove_unselected_tool_sections(self, content: str) -> str:
        """Remove entire sections for tools that are NOT selected."""

        # Create dynamic section-tool mapping
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        mise_file = self.source_dir / ".mise.toml"
        section_tool_mapping = DevContainerParser.create_section_tool_mapping(mise_file, devcontainer_file)

        # Get extension and settings sections from devcontainer.json
        extension_sections = DevContainerParser.parse_extension_sections(devcontainer_file)
        settings_sections = DevContainerParser.parse_settings_sections(devcontainer_file)

        # Check which sections should be included based on tool selections
        for section_name in extension_sections:
            tools_in_section = section_tool_mapping.get(section_name, [])

            # Check if any tools in this section are selected
            section_selected = False
            for tool in tools_in_section:
                if self.config.tool_selected.get(tool, False):
                    section_selected = True
                    break

            # Special handling for conditional sections
            if section_name == "Node Development":
                section_selected = section_selected and self.config.include_js_extensions
            elif section_name == "Markdown":
                section_selected = self.config.include_markdown_extensions
            elif section_name == "Shell/Bash":
                section_selected = self.config.include_shell_extensions

            # Remove section if not selected
            if not section_selected:
                content = self._remove_section(content, section_name, "extensions")

        # Check settings sections
        for section_name in settings_sections:
            tools_in_section = section_tool_mapping.get(section_name, [])

            # Check if any tools in this section are selected
            section_selected = False
            for tool in tools_in_section:
                if self.config.tool_selected.get(tool, False):
                    section_selected = True
                    break

            # Special handling for conditional sections
            if section_name == "Node Development":
                section_selected = section_selected and self.config.include_js_extensions
            elif section_name == "Markdown":
                section_selected = self.config.include_markdown_extensions
            elif section_name == "Shell/Bash":
                section_selected = self.config.include_shell_extensions

            # Remove settings section if not selected
            if not section_selected:
                content = self._remove_section(content, f"{section_name} Settings", "settings")

        return content

    def _remove_section(self, content: str, section_name: str, _section_type: str) -> str:
        """Remove a section between begin/end markers and fix trailing commas."""
        begin_pattern = f"// #### Begin {section_name} ####"
        end_pattern = f"// #### End {section_name} ####"

        # Find the section and remove it
        lines = content.split("\n")
        result_lines = []
        in_section = False

        for line in lines:
            if begin_pattern in line:
                in_section = True
                continue
            if end_pattern in line:
                in_section = False
                continue
            if not in_section:
                result_lines.append(line)

        # Fix trailing commas after section removal
        content = "\n".join(result_lines)
        return self._fix_trailing_commas(content)

    def _fix_trailing_commas(self, content: str) -> str:
        """Fix trailing commas in JSON that would be invalid after section removal."""
        lines = content.split("\n")
        result_lines = []

        for _i, line in enumerate(lines):
            result_lines.append(line)

            # Check if this line ends with a comment like "// #### End Core VS Code Settings ####"
            # and the next non-empty line starts a new section
            if "// #### End Core VS Code Settings ####" in line:
                # Look back to find the last property line and ensure it has a comma
                for j in range(len(result_lines) - 2, -1, -1):  # Go backwards
                    prev_line = result_lines[j].strip()
                    if prev_line and not prev_line.startswith("//") and not prev_line.startswith("/*"):
                        # This is a property line - ensure it ends with comma
                        if not prev_line.endswith(",") and not prev_line.endswith("{") and not prev_line.endswith("["):
                            result_lines[j] = result_lines[j] + ","
                        break

        # Handle trailing commas before closing braces and fix block comment issues
        final_lines = []
        for i, line in enumerate(result_lines):
            # Check for situations where we need to add comma before block comment
            if line.strip() == "}," and i < len(result_lines) - 1:
                # Look ahead to see if next line is a block comment
                next_line = result_lines[i + 1].strip() if i + 1 < len(result_lines) else ""
                if next_line.startswith("/*"):
                    # The comma is already there, this is good
                    final_lines.append(line)
                else:
                    final_lines.append(line)
            elif line.strip().endswith(","):
                # Look ahead to see what comes next
                next_significant_line = None
                for j in range(i + 1, len(result_lines)):
                    if result_lines[j].strip():  # Non-empty line
                        next_significant_line = result_lines[j].strip()
                        break

                # If the next significant line closes an object/array, remove the comma
                if next_significant_line and next_significant_line.startswith(("}", "]")):
                    final_lines.append(line.rstrip(","))
                else:
                    final_lines.append(line)
            else:
                final_lines.append(line)

        return "\n".join(final_lines)

    def _ensure_psi_header_section(self, content: str) -> str:
        """Ensure PSI Header section is present and update templates with actual content."""
        # If PSI Header is configured, replace template placeholders with actual content
        if self.config.psi_header_templates:
            content = self._update_psi_header_templates(content)
        return content

    def _get_psi_languages_for_selected_tools(self) -> list[tuple[str, str]]:
        """Get PSI header languages that should be included based on selected tools."""
        # Base languages to include if PSI header is enabled
        base_languages = [("*", "Default")]

        # If user selected specific PSI header templates, include those
        if self.config.psi_header_templates:
            return self.config.psi_header_templates

        # Otherwise, automatically include languages based on selected tools
        languages_to_include = base_languages.copy()

        # Map tools to their corresponding PSI header languages
        tool_language_mapping = {
            # Go Development
            "golang": ("go", "Go"),
            "golangci-lint": ("go", "Go"),
            "goreleaser": ("go", "Go"),
            # .NET Development
            "dotnet": ("csharp", "C#"),
            # Node Development
            "node": ("javascript", "JavaScript"),
            "pnpm": ("javascript", "JavaScript"),
            "yarn": ("javascript", "JavaScript"),
            "deno": ("typescript", "TypeScript"),
            "bun": ("javascript", "JavaScript"),
            # Python
            "python": ("python", "Python"),
            # PowerShell
            "powershell": ("powershell", "PowerShell"),
            # HashiCorp Tools (use terraform language)
            "opentofu": ("terraform", "Terraform/OpenTofu"),
            "openbao": ("terraform", "Terraform/OpenTofu"),
            "packer": ("terraform", "Terraform/OpenTofu"),
        }

        # Check which tools are selected and add their languages
        included_languages = set()
        for tool_name, is_selected in self.config.tool_selected.items():
            if is_selected and tool_name in tool_language_mapping:
                lang_id, lang_name = tool_language_mapping[tool_name]
                if lang_id not in included_languages:
                    languages_to_include.append((lang_id, lang_name))
                    included_languages.add(lang_id)

        # Always include common languages if any development tools are selected
        if any(self.config.tool_selected.values()):
            common_languages = [
                ("shellscript", "Shell Script"),
                ("markdown", "Markdown"),
            ]
            for lang_id, lang_name in common_languages:
                if lang_id not in included_languages:
                    languages_to_include.append((lang_id, lang_name))
                    included_languages.add(lang_id)

        return languages_to_include

    def _update_psi_header_templates(self, content: str) -> str:
        """Update PSI header templates with actual template content from user configuration."""

        # Generate the template content for each configured language
        template_entries = []

        # Get all languages that should have templates based on selected tools
        languages_to_include = self._get_psi_languages_for_selected_tools()

        for lang_id, _lang_name in languages_to_include:
            # Create the default template content similar to bash script
            current_year = datetime.now(tz=UTC).year
            company = self.config.psi_header_company or "My Company"

            # Generate template text based on language
            if lang_id == "powershell":
                # PowerShell has special .DESCRIPTION format
                template_lines = [
                    ".DESCRIPTION",
                    f"Copyright © {current_year} {company}. All rights reserved.",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]
            else:
                # Standard template for other languages
                template_lines = [
                    f"Copyright © {current_year} {company}. All rights reserved.",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]

            template_entry = {
                "language": lang_id,
                "template": template_lines,
            }
            template_entries.append(template_entry)

        # If no custom templates, add a default one
        if not template_entries:
            current_year = datetime.now(tz=UTC).year
            company = self.config.psi_header_company or "My Company"
            default_template = {
                "language": "*",
                "template": [f"Copyright © {current_year} {company}. All rights reserved."],
            }
            template_entries.append(default_template)

        # Now replace the "psi-header.templates" section in the content
        # Find the templates array and replace it with our generated content
        lines = content.split("\n")
        result_lines = []
        templates_indent = ""

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for the start of psi-header.templates section
            if '"psi-header.templates": [' in line:
                templates_indent = line[: line.find('"psi-header.templates"')]
                result_lines.append(line)  # Add the opening line

                # Skip until we find the closing bracket for this array
                i += 1
                bracket_count = 1
                while i < len(lines) and bracket_count > 0:
                    line = lines[i]
                    # Count brackets to find the end of the array
                    bracket_count += line.count("[") - line.count("]")
                    if bracket_count == 0:
                        # This is the closing line, we'll replace everything before it
                        break
                    i += 1

                # Now insert our custom templates
                for j, template_entry in enumerate(template_entries):
                    result_lines.append(f"{templates_indent}          {{")
                    result_lines.append(f'{templates_indent}            "language": "{template_entry["language"]}",')

                    # Format the template array
                    template_json = json.dumps(template_entry["template"], ensure_ascii=False)
                    result_lines.append(f'{templates_indent}            "template": {template_json}')

                    # Add closing brace with comma if not the last entry
                    if j < len(template_entries) - 1:
                        result_lines.append(f"{templates_indent}          }},")
                    else:
                        result_lines.append(f"{templates_indent}          }}")

                # Add the closing bracket line
                if i < len(lines):
                    result_lines.append(lines[i])
            else:
                result_lines.append(line)

            i += 1

        return "\n".join(result_lines)

    def _remove_psi_header_section(self, content: str) -> str:
        """Remove PSI Header section if not selected."""
        content = self._remove_section(content, "PSI Header", "extensions")
        return self._remove_section(content, "PSI Header Settings", "settings")

    def _update_container_env_hatch_vars(self, content: str) -> str:
        """Update containerEnv section to include Hatch environment variables."""
        if not self.config.install_python_repository:
            return content

        # Find the containerEnv section
        lines = content.split("\n")
        result_lines = []
        in_container_env = False
        container_env_indent = ""
        added_hatch_vars = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for containerEnv section start
            if '"containerEnv":' in line and "{" in line:
                in_container_env = True
                container_env_indent = line[: line.find('"containerEnv"')]
                result_lines.append(line)
                i += 1
                continue

            # If we're in containerEnv section, look for the closing brace
            if in_container_env:
                # Check if this is the end of containerEnv (closing brace with same indentation)
                if line.strip() == "}," or (
                    line.strip() == "}" and i + 1 < len(lines) and lines[i + 1].strip().startswith(",")
                ):
                    # Add Hatch environment variables before the closing brace
                    if not added_hatch_vars:
                        # Add comma to previous line if it doesn't have one and it's not a comment
                        if (
                            result_lines
                            and not result_lines[-1].rstrip().endswith(",")
                            and not result_lines[-1].strip().startswith("//")
                        ):
                            result_lines[-1] = result_lines[-1].rstrip() + ","

                        # Add comment and variables with proper indentation
                        result_lines.append(
                            f"{container_env_indent}    // Python Package Publishing Environment Variables",
                        )
                        result_lines.append(
                            f'{container_env_indent}    "HATCH_INDEX_USER": "${{localEnv:HATCH_INDEX_USER}}",',
                        )
                        result_lines.append(
                            f'{container_env_indent}    "HATCH_INDEX_AUTH": "${{localEnv:HATCH_INDEX_AUTH}}",',
                        )

                        # Add HATCH_INDEX_REPO with the user's configured URL (no trailing comma on last item)
                        if self.config.python_publish_url:
                            result_lines.append(
                                f'{container_env_indent}    "HATCH_INDEX_REPO": "{self.config.python_publish_url}"',
                            )

                        added_hatch_vars = True

                    # Add the closing brace
                    result_lines.append(line)
                    in_container_env = False
                    i += 1
                    continue

                # Check if Hatch variables already exist (to avoid duplicates)
                if "HATCH_INDEX_USER" in line or "HATCH_INDEX_AUTH" in line or "HATCH_INDEX_REPO" in line:
                    # Skip existing Hatch variables to replace them
                    i += 1
                    continue

            result_lines.append(line)
            i += 1

        return "\n".join(result_lines)

    def _update_container_references_in_content(self, content: str) -> str:
        """Update container name references in the content using regex."""

        # Update name
        content = re.sub(
            r'"name": "[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r'"runArgs": \["--name=[^"]*"\]',
            f'"runArgs": ["--name={self.config.container_name}"]',
            content,
        )

        # Update mount sources
        content = re.sub(
            r'"source": "dynamic-dev-container-shellhistory"',
            f'"source": "{self.config.container_name}-shellhistory"',
            content,
        )
        return re.sub(
            r'"source": "dynamic-dev-container-plugins"',
            f'"source": "{self.config.container_name}-plugins"',
            content,
        )

    def _replace_extensions_array(self, content: str) -> str:
        """Replace the extensions array while preserving comments and structure.

        Parameters
        ----------
        content : str
            The original devcontainer.json content as a string

        Returns
        -------
        str
            The updated content with the extensions array replaced

        """
        # Generate the filtered extensions list
        extensions: list[str] = self._generate_extensions_list()

        # Find the extensions array in the content
        extensions_pattern = r'(\s*"extensions": \[)(.*?)(\n\s*\])'

        def replace_extensions(match: re.Match[str]) -> str:
            """Build the replacement text for the extensions array.

            Parameters
            ----------
            match : re.Match[str]
                Regex match object capturing the extensions array region

            Returns
            -------
            str
                Formatted multiline string containing the filtered extensions

            """
            indent = "        "  # Match the original indentation
            extensions_lines: list[str] = []

            for i, ext in enumerate(extensions):
                comma = "," if i < len(extensions) - 1 else ""
                extensions_lines.append(f'{indent}"{ext}"{comma}')

            extensions_content = "\n".join(extensions_lines)
            return f"{match.group(1)}\n{extensions_content}{match.group(3)}"

        return re.sub(extensions_pattern, replace_extensions, content, flags=re.DOTALL)

    def _replace_settings_object(self, content: str) -> str:
        """Replace the settings object while preserving structure and adding only relevant settings."""

        # Find the settings object in the content
        settings_pattern = r'(\s*"settings": \{)(.*?)(\n\s*\})'

        def replace_settings(match: re.Match[str]) -> str:
            # Generate filtered settings content
            filtered_settings = self._generate_filtered_settings_object()
            return f"{match.group(1)}{filtered_settings}{match.group(3)}"

        return re.sub(settings_pattern, replace_settings, content, flags=re.DOTALL)

    def _generate_filtered_settings_object(self) -> str:
        """Generate a properly formatted settings object with only relevant settings."""
        settings = {}

        # Always include core settings
        core_settings = {
            "code-runner.enableAppInsights": False,
            "code-runner.showExecutionMessage": False,
            "code-runner.runInTerminal": True,
            "dev.containers.dockerCredentialHelper": "docker-credential-helper",
            "editor.detectIndentation": False,
            "editor.insertSpaces": True,
            "editor.tabSize": 2,
            "editor.formatOnSave": True,
            "editor.renderWhitespace": "all",
            "editor.rulers": [80, 120],
            "files.eol": "\\n",
            "files.watcherExclude": {
                "**/node_modules/*/**": True,
                "**/.git/objects/**": True,
                "**/.git/subtree-cache/**": True,
                "**/.hg/**": True,
            },
            "files.associations": {
                "*.toml": "toml",
                "*.yaml": "yaml",
                "*.yml": "yaml",
            },
        }
        settings.update(core_settings)

        # Add tool-specific settings based on selections
        for tool, selected in self.config.tool_selected.items():
            if not selected:
                continue

            if tool == "python":
                python_settings = {
                    "python.defaultInterpreterPath": "/home/vscode/.local/share/mise/installs/python/latest/bin/python",
                    "python.terminal.activateEnvironment": False,
                    "python.analysis.autoImportCompletions": True,
                    "python.analysis.typeCheckingMode": "strict",
                }
                settings.update(python_settings)
            elif tool in ["go", "goreleaser"]:
                go_settings = {
                    "go.toolsManagement.checkForUpdates": "off",
                    "go.useLanguageServer": True,
                    "go.formatTool": "gofumpt",
                }
                settings.update(go_settings)
            elif tool == "dotnet":
                dotnet_settings = {
                    "dotnet.server.useOmnisharp": False,
                    "dotnet.completion.showCompletionItemsFromUnimportedNamespaces": True,
                }
                settings.update(dotnet_settings)
            elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                js_settings = {
                    "typescript.preferences.includePackageJsonAutoImports": "auto",
                    "typescript.updateImportsOnFileMove.enabled": "always",
                    "eslint.validate": ["javascript", "javascriptreact", "typescript", "typescriptreact"],
                }
                settings.update(js_settings)

        # Add settings based on flags
        if self.config.include_python_extensions and "python" not in self.config.tool_selected:
            python_settings = {
                "python.defaultInterpreterPath": "/home/vscode/.local/share/mise/installs/python/latest/bin/python",
                "python.terminal.activateEnvironment": False,
                "python.analysis.autoImportCompletions": True,
                "python.analysis.typeCheckingMode": "strict",
            }
            settings.update(python_settings)

        if self.config.include_markdown_extensions:
            markdown_settings = {
                "markdown.extension.toc.levels": "2..6",
                "markdown.extension.orderedList.marker": "one",
                "markdown.extension.orderedList.autoRenumber": True,
            }
            settings.update(markdown_settings)

        if self.config.include_shell_extensions:
            shell_settings = {
                "shellcheck.customArgs": ["-x"],
                "shellcheck.exclude": ["SC1091"],
            }
            settings.update(shell_settings)

        if self.config.include_js_extensions:
            js_settings = {
                "typescript.preferences.includePackageJsonAutoImports": "auto",
                "typescript.updateImportsOnFileMove.enabled": "always",
                "eslint.validate": ["javascript", "javascriptreact", "typescript", "typescriptreact"],
            }
            settings.update(js_settings)

        # Always include these common settings
        common_settings = {
            "mise.checkForUpdates": False,
            "mise.showUpdateNotifications": False,
            "cSpell.enabledLanguageIds": [
                "asciidoc",
                "c",
                "cpp",
                "csharp",
                "css",
                "git-commit",
                "go",
                "handlebars",
                "haskell",
                "html",
                "jade",
                "java",
                "javascript",
                "javascriptreact",
                "json",
                "jsonc",
                "latex",
                "less",
                "markdown",
                "php",
                "plaintext",
                "pug",
                "python",
                "restructuredtext",
                "rust",
                "scala",
                "scss",
                "text",
                "typescript",
                "typescriptreact",
                "yaml",
                "yml",
            ],
            "todo-tree.general.tags": ["BUG", "HACK", "FIXME", "TODO", "XXX", "NOTE", "WARNING"],
            "todo-tree.highlights.customHighlight": {
                "TODO": {"icon": "check", "type": "line"},
                "NOTE": {"icon": "note", "foreground": "#00ff00"},
                "WARNING": {"icon": "alert", "foreground": "#ffaa00"},
                "FIXME": {"icon": "bug", "foreground": "#ff0000"},
            },
        }
        settings.update(common_settings)

        # Convert the settings dict to a JSON string with proper indentation
        settings_json = json.dumps(settings, indent=2, ensure_ascii=False)

        # Add proper indentation for the devcontainer context (8 spaces for each line)
        lines = settings_json.split("\n")
        indented_lines = []
        for i, line in enumerate(lines):
            if i == 0:  # First line (opening brace)
                indented_lines.append("\n        " + line[1:])  # Remove opening brace, add indentation
            elif i == len(lines) - 1:  # Last line (closing brace)
                indented_lines.append("        " + line[:-1])  # Remove closing brace, add indentation
            else:
                indented_lines.append("        " + line)

        return "\n".join(indented_lines)

    def _update_container_references(self, file_path: Path) -> None:
        """Update container name references in the file using sed-like replacements."""
        with open(file_path) as f:
            content = f.read()

        # Update name
        content = re.sub(
            r'"name": "[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r"--name=dynamic-dev-container",
            f"--name={self.config.container_name}",
            content,
        )

        # Update mount sources
        content = re.sub(
            r"dynamic-dev-container-shellhistory",
            f"{self.config.container_name}-shellhistory",
            content,
        )
        content = re.sub(
            r"dynamic-dev-container-plugins",
            f"{self.config.container_name}-plugins",
            content,
        )

        with open(file_path, "w") as f:
            f.write(content)

    def _append_remaining_devcontainer_content(self, temp_file: Path, source_file: Path) -> None:
        """Append the remaining content after extensions array from source file."""
        with open(source_file) as f:
            lines = f.readlines()

        # Find where extensions array ends and get the rest
        extensions_end_found = False
        remaining_lines = []
        in_extensions = False

        for line in lines:
            if '"extensions": [' in line:
                in_extensions = True
                continue
            if in_extensions and line.strip() == "],":
                # Found end of extensions array, start collecting remaining content
                extensions_end_found = True
                remaining_lines.append("      ],\n")
                continue
            if extensions_end_found:
                remaining_lines.append(line)

        # Append remaining content to temp file
        with open(temp_file, "a") as f:
            f.writelines(remaining_lines)

    def _update_settings_in_file(self, file_path: Path) -> None:
        """Update VS Code settings in the devcontainer.json file using text manipulation."""
        # Read the current content
        with open(file_path) as f:
            content = f.read()

        # Find the settings section
        settings_start = content.find('"settings": {')
        if settings_start == -1:
            return

        # Find the end of settings section (look for closing brace at the same indentation level)
        settings_end = self._find_settings_end(content, settings_start)
        if settings_end == -1:
            return

        # Extract the parts before and after settings
        before_settings = content[:settings_start]
        after_settings = content[settings_end:]

        # Generate filtered settings content
        filtered_settings = self._generate_filtered_settings()

        # Reconstruct the file with filtered settings
        new_content = before_settings + filtered_settings + after_settings

        # Write back to file
        with open(file_path, "w") as f:
            f.write(new_content)

    def _find_settings_end(self, content: str, settings_start: int) -> int:
        """Find the end of the settings section by matching braces."""
        # Start after the opening brace of "settings": {
        brace_pos = content.find("{", settings_start)
        if brace_pos == -1:
            return -1

        # Count braces to find the matching closing brace
        brace_count = 1
        pos = brace_pos + 1

        while pos < len(content) and brace_count > 0:
            char = content[pos]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
            pos += 1

        return pos if brace_count == 0 else -1

    def _generate_filtered_settings(self) -> str:
        """Generate filtered settings content based on selected tools."""
        settings_lines = []
        settings_lines.append('      "settings": {')

        # Define settings mappings for different tools/categories
        settings_mappings = {
            "core": [
                '        "code-runner.enableAppInsights": false,',
                '        "code-runner.showExecutionMessage": false,',
                '        "code-runner.runInTerminal": true,',
                '        "dev.containers.dockerCredentialHelper": "docker-credential-helper",',
                '        "editor.detectIndentation": false,',
                '        "editor.insertSpaces": true,',
                '        "editor.tabSize": 2,',
                '        "editor.formatOnSave": true,',
                '        "editor.renderWhitespace": "all",',
                '        "editor.rulers": [80, 120],',
                '        "files.eol": "\\n",',
                '        "files.watcherExclude": {',
                '          "**/node_modules/*/**": true,',
                '          "**/.git/objects/**": true,',
                '          "**/.git/subtree-cache/**": true,',
                '          "**/.hg/**": true',
                "        },",
            ],
            "python": [
                '        "python.defaultInterpreterPath": "/home/vscode/.local/share/mise/installs/python/latest/bin/python",',
                '        "python.terminal.activateEnvironment": false,',
                '        "python.analysis.autoImportCompletions": true,',
                '        "python.analysis.typeCheckingMode": "strict",',
            ],
            "go": [
                '        "go.toolsManagement.checkForUpdates": "off",',
                '        "go.useLanguageServer": true,',
                '        "go.formatTool": "gofumpt",',
            ],
            "dotnet": [
                '        "dotnet.server.useOmnisharp": false,',
                '        "dotnet.completion.showCompletionItemsFromUnimportedNamespaces": true,',
            ],
            "javascript": [
                '        "typescript.preferences.includePackageJsonAutoImports": "auto",',
                '        "typescript.updateImportsOnFileMove.enabled": "always",',
                '        "eslint.validate": ["javascript", "javascriptreact", "typescript", "typescriptreact"],',
            ],
            "markdown": [
                '        "markdown.extension.toc.levels": "2..6",',
                '        "markdown.extension.orderedList.marker": "one",',
                '        "markdown.extension.orderedList.autoRenumber": true,',
            ],
            "shell": [
                '        "shellcheck.customArgs": ["-x"],',
                '        "shellcheck.exclude": ["SC1091"],',
            ],
            "mise": [
                '        "mise.checkForUpdates": false,',
                '        "mise.showUpdateNotifications": false,',
            ],
            "spell": [
                '        "cSpell.enabledLanguageIds": [',
                '          "asciidoc", "c", "cpp", "csharp", "css", "git-commit", "go", "handlebars",',
                '          "haskell", "html", "jade", "java", "javascript", "javascriptreact", "json",',
                '          "jsonc", "latex", "less", "markdown", "php", "plaintext", "pug", "python",',
                '          "restructuredtext", "rust", "scala", "scss", "text", "typescript",',
                '          "typescriptreact", "yaml", "yml"',
                "        ],",
            ],
            "todo": [
                '        "todo-tree.general.tags": ["BUG", "HACK", "FIXME", "TODO", "XXX", "NOTE", "WARNING"],',
                '        "todo-tree.highlights.customHighlight": {',
                '          "TODO": { "icon": "check", "type": "line" },',
                '          "NOTE": { "icon": "note", "foreground": "#00ff00" },',
                '          "WARNING": { "icon": "alert", "foreground": "#ffaa00" },',
                '          "FIXME": { "icon": "bug", "foreground": "#ff0000" }',
                "        },",
            ],
        }

        # Always include core settings
        settings_lines.extend(settings_mappings["core"])

        # Add tool-specific settings based on selections
        for tool, selected in self.config.tool_selected.items():
            if not selected:
                continue

            if tool in ["go", "goreleaser"]:
                settings_lines.extend(settings_mappings["go"])
            elif tool == "dotnet":
                settings_lines.extend(settings_mappings["dotnet"])
            elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                settings_lines.extend(settings_mappings["javascript"])
            elif tool == "python":
                settings_lines.extend(settings_mappings["python"])

        # Add settings based on flags
        if self.config.include_python_extensions and "python" not in self.config.tool_selected:
            settings_lines.extend(settings_mappings["python"])

        if self.config.include_markdown_extensions:
            settings_lines.extend(settings_mappings["markdown"])

        if self.config.include_shell_extensions:
            settings_lines.extend(settings_mappings["shell"])

        if self.config.include_js_extensions:
            settings_lines.extend(settings_mappings["javascript"])

        # Always include these settings
        settings_lines.extend(settings_mappings["mise"])
        settings_lines.extend(settings_mappings["spell"])
        settings_lines.extend(settings_mappings["todo"])

        # Remove trailing comma from last line and close settings
        if settings_lines and settings_lines[-1].endswith(","):
            settings_lines[-1] = settings_lines[-1][:-1]

        settings_lines.append("      }")
        return "\n".join(settings_lines)

    def _extract_settings_section(self, start_marker: str, end_marker: str) -> list[str]:
        """Extract settings lines from a section in the devcontainer.json file."""
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            return []

        with open(source_file) as f:
            lines = f.readlines()

        result = []
        in_section = False

        for line in lines:
            if start_marker in line:
                in_section = True
                continue
            if end_marker in line:
                break
            if in_section:
                # Include all lines in the settings section (preserving comments and formatting)
                result.append(line.rstrip())

        return result

    def _extract_devcontainer_section(self, start_marker: str, end_marker: str) -> list[str]:
        """Extract a section from the devcontainer.json file."""
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            return []

        with open(source_file) as f:
            lines = f.readlines()

        result = []
        in_section = False

        for line in lines:
            if start_marker in line:
                in_section = True
                continue
            if end_marker in line:
                break
            if in_section:
                # Extract extension lines - look for quoted strings that may have comments
                stripped = line.strip()
                if stripped.startswith('"') and ("," in stripped or stripped.endswith('"')):
                    # Extract the extension ID from the quoted string
                    # Handle format: "extension.id", // comment
                    extension_part = stripped.split(",")[0] if "," in stripped else stripped

                    # Remove quotes to get extension ID
                    extension_id = extension_part.strip('"')
                    if extension_id:  # Only add non-empty extension IDs
                        result.append(extension_id)

        return result

    def _generate_extensions_list(self) -> list[str]:
        """Generate the list of VS Code extensions based on selected tools."""
        extensions = []

        # Define extension mappings for different tools/categories
        extension_mappings = {
            "github": [
                "GitHub.copilot",
                "GitHub.copilot-chat",
                "GitHub.vscode-pull-request-github",
                "GitHub.github-vscode-theme",
                "GitHub.remotehub",
                "GitHub.vscode-github-actions",
                "cschleiden.vscode-github-actions",
                "mhutchie.git-graph",
                "huizhou.githd",
            ],
            "python": [
                "ms-python.python",
                "ms-python.mypy-type-checker",
                "charliermarsh.ruff",
                "Textualize.textual-syntax-highlighter",
            ],
            "go": [
                "golang.go",
                "ms-vscode.vscode-go",
            ],
            "dotnet": [
                "ms-dotnettools.csharp",
                "ms-dotnettools.csdevkit",
            ],
            "javascript": [
                "ms-vscode.vscode-typescript-next",
                "ms-vscode.vscode-eslint",
                "esbenp.prettier-vscode",
            ],
            "markdown": [
                "yzhang.markdown-all-in-one",
                "darkriszty.markdown-table-prettify",
            ],
            "shell": [
                "foxundermoon.shell-format",
                "timonwong.shellcheck",
            ],
            "core": [
                "albert.TabOut",
                "ciiqr.encode",
                "EditorConfig.EditorConfig",
                "euskadi31.json-pretty-printer",
                "Gruntfuggly.todo-tree",
                "hediet.vscode-drawio",
                "IronGeek.vscode-env",
                "k--kato.docomment",
                "hverlin.mise-vscode",
                "ms-azuretools.vscode-docker",
                "naumovs.color-highlight",
                "PKief.material-icon-theme",
                "RapidAPI.vscode-rapidapi-client",
                "streetsidesoftware.code-spell-checker",
                "tamasfe.even-better-toml",
            ],
        }

        # Always include GitHub + Core extensions
        extensions.extend(extension_mappings["github"])
        extensions.extend(extension_mappings["core"])

        # Add tool-specific extensions based on selections
        for tool, selected in self.config.tool_selected.items():
            if not selected:
                continue

            if tool in ["go", "goreleaser"]:
                extensions.extend(extension_mappings["go"])
            elif tool == "dotnet":
                extensions.extend(extension_mappings["dotnet"])
            elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                extensions.extend(extension_mappings["javascript"])
            elif tool == "python":
                extensions.extend(extension_mappings["python"])

        # Add extensions based on flags
        if self.config.include_python_extensions and "python" not in self.config.tool_selected:
            extensions.extend(extension_mappings["python"])

        if self.config.include_markdown_extensions:
            extensions.extend(extension_mappings["markdown"])

        if self.config.include_shell_extensions:
            extensions.extend(extension_mappings["shell"])

        if self.config.include_js_extensions:
            extensions.extend(extension_mappings["javascript"])

        if self.config.install_psi_header:
            extensions.append("psioniq.psi-header")

        # Remove duplicates while preserving order
        seen = set()
        unique_extensions = []
        for ext in extensions:
            if ext not in seen:
                seen.add(ext)
                unique_extensions.append(ext)

        return unique_extensions

    def _generate_psi_header_settings(self) -> dict[str, Any]:
        """Generate PSI Header specific settings."""
        if not self.config.install_psi_header:
            return {}

        settings: dict[str, Any] = {}

        # Company configuration
        if self.config.psi_header_company:
            settings["psi-header.config"] = {
                "company": self.config.psi_header_company,
            }

        # Changes tracking configuration
        settings["psi-header.changes-tracking"] = {
            "autoHeader": "autoSave",
            "exclude": ["json"],
            "excludeGlob": ["**/.git/**"],
        }

        # Project creation year
        current_year = str(datetime.now(tz=UTC).year)
        settings["psi-header.variables"] = [["projectCreationYear", current_year]]

        # Language configurations
        lang_configs: list[dict[str, Any]] = []

        # Default configuration for all languages
        lang_configs.append(
            {
                "language": "*",
                "begin": "",
                "end": "",
                "prefix": "// ",
            },
        )

        # Add language-specific configurations based on selected tools and templates
        if self.config.psi_header_templates:
            for lang_id, _lang_name in self.config.psi_header_templates:
                template_lines = [
                    f"Copyright (c) {self.config.psi_header_company or 'Company'} - All Rights Reserved",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]

                lang_config: dict[str, Any] = {
                    "language": lang_id,
                    "template": template_lines,
                }

                # Language-specific configurations
                if lang_id == "python":
                    lang_config.update(
                        {
                            "begin": '"""',
                            "end": '"""',
                            "prefix": "",
                        },
                    )
                elif lang_id in ["shellscript", "bash"]:
                    lang_config.update(
                        {
                            "begin": "",
                            "end": "",
                            "prefix": "# ",
                        },
                    )
                elif lang_id in ["html", "xml"]:
                    lang_config.update(
                        {
                            "begin": "<!--",
                            "end": "-->",
                            "prefix": "",
                        },
                    )
                elif lang_id == "css":
                    lang_config.update(
                        {
                            "begin": "/*",
                            "end": "*/",
                            "prefix": "",
                        },
                    )
                else:
                    # Default for most languages (JavaScript, TypeScript, Go, etc.)
                    lang_config.update(
                        {
                            "begin": "",
                            "end": "",
                            "prefix": "// ",
                        },
                    )

                lang_configs.append(lang_config)

        settings["psi-header.lang-config"] = lang_configs

        return settings

    def update_dev_sh(self) -> None:
        """Update dev.sh with project settings."""
        source_file = self.source_dir / "dev.sh"
        target_file = Path(self.config.project_path) / "dev.sh"

        if not source_file.exists():
            return

        with open(source_file) as f:
            content = f.read()

        # Replace variables
        content = re.sub(
            r'docker_exec_command="[^"]*"',
            f'docker_exec_command="{self.config.docker_exec_command}"',
            content,
        )
        content = re.sub(
            r'project_name="[^"]*"',
            f'project_name="{self.config.project_name}"',
            content,
        )
        content = re.sub(
            r'container_name="[^"]*"',
            f'container_name="{self.config.container_name}"',
            content,
        )

        with open(target_file, "w") as f:
            f.write(content)

        # Make executable
        os.chmod(target_file, 0o744)

    def update_pyproject_toml(self) -> None:
        """Update pyproject.toml with Python project configuration."""
        target_file = Path(self.config.project_path) / "pyproject.toml"

        if not target_file.exists():
            return

        # Read and update pyproject.toml
        with open(target_file) as f:
            content = f.read()

        # Replace project name
        if self.config.python_project_name:
            content = re.sub(
                r'name = "my-awesome-project"',
                f'name = "{self.config.python_project_name}"',
                content,
            )

        # Replace description
        if self.config.python_project_description:
            content = re.sub(
                r'description = "A brief description of your project"',
                f'description = "{self.config.python_project_description}"',
                content,
            )

        # Replace required Python version
        if self.config.python_requires_python:
            content = re.sub(
                r'requires-python = ">=3\.12"',
                f'requires-python = "{self.config.python_requires_python}"',
                content,
            )

        # Replace author information
        if self.config.python_author_name and self.config.python_author_email:
            content = re.sub(
                r'\{ name = "Your Name", email = "your\.email@example\.com" \}',
                f'{{ name = "{self.config.python_author_name}", email = "{self.config.python_author_email}" }}',
                content,
            )
        elif self.config.python_author_name:
            content = re.sub(
                r'\{ name = "Your Name", email = "your\.email@example\.com" \}',
                f'{{ name = "{self.config.python_author_name}" }}',
                content,
            )

        # Replace project URLs
        if self.config.python_homepage_url:
            content = re.sub(
                r'Homepage = "https://github\.com/yourusername/my-awesome-project"',
                f'Homepage = "{self.config.python_homepage_url}"',
                content,
            )

        if self.config.python_source_url:
            content = re.sub(
                r'Source = "https://github\.com/yourusername/my-awesome-project"',
                f'Source = "{self.config.python_source_url}"',
                content,
            )

        # Replace package index URL
        if self.config.python_index_url:
            content = re.sub(
                r'index-url = "https://pypi\.org/simple/"',
                f'index-url = "{self.config.python_index_url}"',
                content,
            )

        # Replace package path in build targets
        if self.config.python_packages_path:
            content = re.sub(
                r'packages = \["src/my_awesome_project"\]',
                f'packages = ["{self.config.python_packages_path}"]',
                content,
            )

            # Also update version path if it follows the same pattern
            if "src/" in self.config.python_packages_path:
                package_name = self.config.python_packages_path.replace("src/", "").replace("/", "_")
                content = re.sub(
                    r'path = "src/my_awesome_project/__about__\.py"',
                    f'path = "src/{package_name}/__about__.py"',
                    content,
                )

            # Update coverage source packages
            if self.config.python_project_name:
                safe_project_name = self.config.python_project_name.replace("-", "_")
                content = re.sub(
                    r'source_pkgs = \["my_awesome_project", "tests"\]',
                    f'source_pkgs = ["{safe_project_name}", "tests"]',
                    content,
                )
                content = re.sub(
                    r'project = \["src", "\*/my_awesome_project/src"\]',
                    f'project = ["src", "*/{safe_project_name}/src"]',
                    content,
                )
                content = re.sub(
                    r'tests = \["tests", "\*/my_awesome_project/tests"\]',
                    f'tests = ["tests", "*/{safe_project_name}/tests"]',
                    content,
                )
                content = re.sub(
                    r'omit = \[\s*"src/my_awesome_project/__about__\.py",\s*\]',
                    f'omit = [\n  "src/{safe_project_name}/__about__.py",\n]',
                    content,
                )

        # Replace license
        if self.config.python_license:
            content = re.sub(
                r'license = \{text = "MIT"\}',
                f'license = {{text = "{self.config.python_license}"}}',
                content,
            )

        # Replace keywords
        if self.config.python_keywords:
            keywords_list = [f'"{kw.strip()}"' for kw in self.config.python_keywords.split(",") if kw.strip()]
            keywords_str = ", ".join(keywords_list)
            content = re.sub(
                r'keywords = \["python", "cli", "automation"\]',
                f"keywords = [{keywords_str}]",
                content,
            )

        # Configure Hatch publishing based on repository settings
        content = self._update_hatch_publish_config(content)

        with open(target_file, "w") as f:
            f.write(content)
        if self.config.python_keywords:
            keywords_list = [f'"{kw.strip()}"' for kw in self.config.python_keywords.split(",") if kw.strip()]
            keywords_str = ", ".join(keywords_list)
            content = re.sub(
                r'keywords = \["python", "package"\]',
                f"keywords = [{keywords_str}]",
                content,
            )

        # Replace repository URL if GitHub info provided
        if self.config.python_github_username and self.config.python_github_project:
            repo_url = f"https://github.com/{self.config.python_github_username}/{self.config.python_github_project}"
            content = re.sub(
                r'repository = "https://github\.com/yourusername/your-repo"',
                f'repository = "{repo_url}"',
                content,
            )

        # Configure Hatch publishing based on repository settings
        content = self._update_hatch_publish_config(content)

        with open(target_file, "w") as f:
            f.write(content)

        # Create environment variables example file if repository is configured
        if self.config.install_python_repository:
            self._create_environment_variables_example()

    def _create_environment_variables_example(self) -> None:
        """Create an example .env file with the required environment variables for publishing."""
        env_file = Path(self.config.project_path) / ".env.example"

        repo_type = self.config.python_repository_type or "pypi"
        publish_url = self.config.python_publish_url or "https://upload.pypi.org/legacy/"

        env_content = f"""# Environment Variables for Python Package Publishing
# Copy this file to .env and fill in your actual credentials
# Note: Never commit .env files with real credentials to version control

# Repository Type: {repo_type.title()}
# Repository URL: {publish_url}

"""

        if repo_type == "pypi":
            env_content += """# PyPI Credentials (get token from https://pypi.org/manage/account/)
HATCH_INDEX_USER=__token__
HATCH_INDEX_AUTH=your_pypi_api_token_here

# For TestPyPI (testing), uncomment these instead:
# HATCH_INDEX_USER=__token__
# HATCH_INDEX_AUTH=your_testpypi_api_token_here
# HATCH_INDEX_REPO=https://test.pypi.org/legacy/
"""
        elif repo_type == "artifactory":
            env_content += f"""# Artifactory Credentials
HATCH_INDEX_USER=your_artifactory_username
HATCH_INDEX_AUTH=your_artifactory_password_or_token
HATCH_INDEX_REPO={publish_url}

# For development repository, you might use:
# HATCH_INDEX_REPO={publish_url.replace("-prod", "-dev") if "-prod" in publish_url else publish_url + "-dev"}
"""
        elif repo_type == "nexus":
            env_content += f"""# Nexus Credentials
HATCH_INDEX_USER=your_nexus_username
HATCH_INDEX_AUTH=your_nexus_password_or_token
HATCH_INDEX_REPO={publish_url}

# For development repository, you might use:
# HATCH_INDEX_REPO={publish_url.replace("-prod", "-dev") if "-prod" in publish_url else publish_url + "-dev"}
"""
        else:
            env_content += f"""# Custom Repository Credentials
HATCH_INDEX_USER=your_username
HATCH_INDEX_AUTH=your_password_or_token
HATCH_INDEX_REPO={publish_url}
"""

        env_content += """
# Usage Instructions:
# 1. Copy this file: cp .env.example .env
# 2. Edit .env with your actual credentials
# 3. Load environment: source .env
# 4. Publish package: hatch publish
#
# For dev containers:
# - HATCH_INDEX_REPO has been automatically configured in .devcontainer/devcontainer.json
# - Set HATCH_INDEX_USER and HATCH_INDEX_AUTH in your local environment:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
# - These will be automatically passed to the dev container on startup
"""

        with open(env_file, "w") as f:
            f.write(env_content)

    def _update_hatch_publish_config(self, content: str) -> str:
        """Update the [tool.hatch.publish.index] section based on repository configuration."""
        if not self.config.install_python_repository:
            # If repository publishing is disabled, set disable = true
            hatch_config = """
[tool.hatch.publish.index]
disable = true"""
        else:
            # Generate environment variable configuration based on repository type
            repo_type = self.config.python_repository_type or "pypi"
            publish_url = self.config.python_publish_url or "https://upload.pypi.org/legacy/"

            # Create specific instructions based on repository type
            if repo_type == "pypi":
                auth_instructions = """# For PyPI (python.org):
#   export HATCH_INDEX_USER=__token__
#   export HATCH_INDEX_AUTH=your_pypi_api_token
#   hatch publish"""
                env_example = """# Environment variables for PyPI publishing:
export HATCH_INDEX_USER=__token__
export HATCH_INDEX_AUTH=your_pypi_api_token"""
            elif repo_type == "artifactory":
                auth_instructions = f"""# For Artifactory repository:
#   export HATCH_INDEX_USER=your_artifactory_username
#   export HATCH_INDEX_AUTH=your_artifactory_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for Artifactory publishing:
export HATCH_INDEX_USER=your_artifactory_username
export HATCH_INDEX_AUTH=your_artifactory_password_or_token
export HATCH_INDEX_REPO={publish_url}"""
            elif repo_type == "nexus":
                auth_instructions = f"""# For Nexus repository:
#   export HATCH_INDEX_USER=your_nexus_username
#   export HATCH_INDEX_AUTH=your_nexus_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for Nexus publishing:
export HATCH_INDEX_USER=your_nexus_username
export HATCH_INDEX_AUTH=your_nexus_password_or_token
export HATCH_INDEX_REPO={publish_url}"""
            else:
                auth_instructions = f"""# For custom repository:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for custom repository publishing:
export HATCH_INDEX_USER=your_username
export HATCH_INDEX_AUTH=your_password_or_token
export HATCH_INDEX_REPO={publish_url}"""

            hatch_config = f"""
[tool.hatch.publish.index]
disable = false  # Set to true to disable publishing entirely

# Repository Configuration for {repo_type.title()}
# Repository URL: {publish_url}
#
# IMPORTANT: Set these environment variables for authentication and repository:
{auth_instructions}
#
# Copy and customize these environment variables:
{env_example}
#
# For development containers, add these to your .devcontainer/devcontainer.json:
# "containerEnv": {{
#   "HATCH_INDEX_USER": "${{localEnv:HATCH_INDEX_USER}}",
#   "HATCH_INDEX_AUTH": "${{localEnv:HATCH_INDEX_AUTH}}",
#   "HATCH_INDEX_REPO": "{publish_url}"
# }}
#
# NOTE: If using install.py, these containerEnv variables are automatically configured!
#
# Repository configuration via environment variables (recommended for containers):
# - HATCH_INDEX_USER: Username for authentication
# - HATCH_INDEX_AUTH: Password/token for authentication
# - HATCH_INDEX_REPO: Repository URL (overrides default PyPI)"""

        # Replace the entire [tool.hatch.publish.index] section
        # First, find and remove any existing hatch publish configuration
        pattern = r"\[tool\.hatch\.publish\.index\].*?(?=\n\[|\nTODO|\n$|\Z)"
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

        # Also remove any old repos configurations that might exist
        pattern = r"\[tool\.hatch\.publish\.index\.repos\.[^\]]+\].*?(?=\n\[|\n$|\Z)"
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

        # Remove multiple consecutive blank lines
        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Find the end of the hatch publish comment section and add our config
        insertion_point = content.find("# To publish to a specific repository:")
        if insertion_point != -1:
            # Find the end of the comment block
            lines = content[insertion_point:].split("\n")
            comment_end = insertion_point
            for i, line in enumerate(lines):
                if line.startswith("#") or line.strip() == "":
                    comment_end = insertion_point + len("\n".join(lines[: i + 1]))
                else:
                    break

            # Insert our configuration after the comments
            content = content[:comment_end] + "\n" + hatch_config + "\n" + content[comment_end:]
        else:
            # Fallback: add at the end
            content += "\n" + hatch_config + "\n"

        # Check if hatch publish config already exists and replace it
        if "[tool.hatch.publish.index]" in content:
            # Replace existing configuration
            # Find the start and end of the hatch publish section
            pattern = r"\[tool\.hatch\.publish\.index\].*?(?=\n\[|$)"
            content = re.sub(pattern, hatch_config.strip(), content, flags=re.DOTALL)
        else:
            # Append new configuration
            content += "\n" + hatch_config

        # Return the updated content
        return content

    def configure_psi_header(self) -> None:
        """Configure PSI Header extension settings."""
        if not self.config.install_psi_header:
            return

        settings_dir = Path(self.config.project_path) / ".vscode"
        settings_file = settings_dir / "settings.json"

        settings_dir.mkdir(exist_ok=True)

        # Basic PSI Header configuration
        psi_config: dict[str, Any] = {
            "psi-header.config": {
                "forceToTop": True,
                "blankLinesAfter": 1,
                "license": "Custom",
            },
            "psi-header.templates": [],
        }

        # Add company name if provided
        if self.config.psi_header_company:
            psi_config["psi-header.config"]["company"] = self.config.psi_header_company

        # Add language-specific templates
        for lang_id, _lang_name in self.config.psi_header_templates:
            template_config: dict[str, Any] = {
                "language": lang_id,
                "template": [
                    f"Copyright (c) {self.config.psi_header_company or 'Company'} - All Rights Reserved",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ],
            }
            psi_config["psi-header.templates"].append(template_config)

        # Read existing settings or create new
        existing_settings: dict[str, Any] = {}
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    existing_settings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_settings = {}

        # Merge PSI Header settings
        existing_settings.update(psi_config)

        # Write updated settings

        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)

    def configure_python_repository_settings(self) -> None:
        """Configure Python repository settings if needed."""
        if not self.config.install_python_tools:
            return

        # Update pip.conf or similar configuration files
        pip_dir = Path(self.config.project_path) / ".pip"
        pip_conf = pip_dir / "pip.conf"

        if self.config.python_index_url and self.config.python_index_url != "https://pypi.org/simple/":
            pip_dir.mkdir(exist_ok=True)

            config_content = [
                "[global]",
                f"index-url = {self.config.python_index_url}",
            ]

            if self.config.python_extra_index_url:
                config_content.append(f"extra-index-url = {self.config.python_extra_index_url}")

            with open(pip_conf, "w") as f:
                f.write("\n".join(config_content) + "\n")

    def show_completion(self) -> None:
        """Show completion message and exit."""
        console = Console()
        console.print("\n[bold green]Installation completed successfully![/bold green]")
        console.print("\n[cyan]Project Settings Applied:[/cyan]")
        console.print(f"  Project Name: {self.config.project_name}")
        console.print(f"  Container Name: {self.config.container_name}")
        console.print(f"  Display Name: {self.config.display_name}")

        if self.config.docker_exec_command:
            console.print(f"  Docker Exec Command: {self.config.docker_exec_command}")

        console.print("\n[cyan]Next steps:[/cyan]")
        console.print("1. [yellow]Recommended:[/yellow] Set GITHUB_TOKEN environment variable")

        # Add Python repository configuration instructions if enabled
        if self.config.install_python_repository:
            env_file = Path(self.config.project_path) / ".env.example"
            if env_file.exists():
                console.print(
                    "2. [yellow]Python Publishing:[/yellow] Environment variables automatically configured",
                )
                console.print(f"   • Review: {env_file}")
                console.print("   • Set HATCH_INDEX_USER and HATCH_INDEX_AUTH in your local environment")
                console.print("   • HATCH_INDEX_REPO automatically configured in devcontainer.json")
                console.print("   • Variables will be passed to dev container on startup")
                console.print(f"3. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
                console.print(f"4. Review tool versions in {self.config.project_path}/.mise.toml")
            else:
                console.print(f"2. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
                console.print(f"3. Review tool versions in {self.config.project_path}/.mise.toml")
        else:
            console.print(f"2. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
            console.print(f"3. Review tool versions in {self.config.project_path}/.mise.toml")

        console.print(f"\n[blue]You can now run:[/blue] cd {self.config.project_path} && ./dev.sh")

        # Exit after showing completion
        self.app.call_later(self.app.exit)


class DynamicDevContainerApp(App[None]):
    """Main application class."""

    CSS_PATH = "install.tcss"

    def __init__(self, project_path: str = "") -> None:
        """Initialize the Dynamic Dev Container application.

        Parameters
        ----------
        project_path : str, optional
            Path where the dev container will be created, by default ""

        Raises
        ------
        FileNotFoundError
            If required template files are not found in the current directory

        """
        super().__init__()
        self.config = ProjectConfig()
        self.config.project_path = project_path
        self.source_dir = Path.cwd()  # Assume running from source directory

        # Verify required files exist
        if not (self.source_dir / ".devcontainer" / "devcontainer.json").exists():
            msg = "Required template files not found. Must run from dynamic-dev-container directory."
            raise FileNotFoundError(msg)

        # Parse .mise.toml
        self.sections, self.tool_selected, self.tool_version_value, self.tool_version_configurable = (
            MiseParser.parse_mise_sections(self.source_dir / ".mise.toml")
        )

        logger.debug("DynamicDevContainerApp initialized successfully")

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Called when app is mounted."""
        self.push_screen(WelcomeScreen(), self.after_welcome)

    def after_welcome(self, _result: None = None) -> None:
        """Called after welcome screen."""
        try:
            # Set a default project path if none provided
            if not self.config.project_path:
                self.config.project_path = str(Path.home() / "my-project")

            # Always proceed to project config screen
            self.push_screen(ProjectConfigScreen(self.config), self.after_project_config)

        except Exception as e:
            logger.exception("Exception in after_welcome: %s", e)
            # Try to show an error message and exit gracefully
            self.notify(f"Error: {e}", severity="error")
            self.exit()

    def after_project_config(self, _result: None = None) -> None:
        """Called after project config screen."""

        # Always show tool selection screen, even if no tools available
        self.push_screen(
            ToolSelectionScreen(
                self.config,
                self.sections,
                self.tool_selected,
                self.tool_version_configurable,
                self.tool_version_value,
            ),
            self.after_tool_selection,
        )

    def show_tool_selection(self) -> None:
        """Show tool selection screen with current state."""

        # Show tool selection screen with current selections
        self.push_screen(
            ToolSelectionScreen(
                self.config,
                self.sections,
                self.tool_selected,
                self.tool_version_configurable,
                self.tool_version_value,
            ),
            self.after_tool_selection,
        )

    def after_tool_selection(self, _result: None = None) -> None:
        """Called after tool selection screen."""

        # Python repository configuration is now handled inline in ToolSelectionScreen
        # Version configuration is also handled inline in ToolSelectionScreen
        # Skip the separate screens and go directly to PSI Header configuration
        self.show_psi_header_config()

    def after_python_repository(self, _result: None = None) -> None:
        """Called after Python repository configuration."""
        # Continue to PSI Header configuration
        self.show_psi_header_config()

    def after_python_project(self, _result: None = None) -> None:
        """Called after Python project metadata configuration."""
        # Return to tool selection to allow selection of other tools
        self.show_tool_selection()

    def check_tool_versions(self) -> None:
        """Check if we need to show tool version configuration screen."""
        configurable_tools = [
            tool
            for tool, configurable in self.config.tool_version_configurable.items()
            if configurable and self.config.tool_selected.get(tool, False)
        ]

        if configurable_tools:
            self.push_screen(ToolVersionScreen(self.config), self.after_tool_versions)
        else:
            # Show PSI Header configuration
            self.show_psi_header_config()

    def after_tool_versions(self, _result: None = None) -> None:
        """Called after tool version configuration."""
        # Show PSI Header configuration
        self.show_psi_header_config()

    def show_psi_header_config(self) -> None:
        """Show PSI Header configuration screen."""
        self.push_screen(PSIHeaderScreen(self.config, self.source_dir), self.after_psi_header)

    def after_psi_header(self, _result: None = None) -> None:
        """Called after PSI Header configuration."""
        # Now show summary
        self.push_screen(SummaryScreen(self.config), self.after_summary)

    def after_summary(self, _result: None = None) -> None:
        """Called after summary screen."""
        self.push_screen(InstallationScreen(self.config, self.source_dir))


def main() -> None:
    """Main entry point."""
    global DEBUG_MODE  # noqa: PLW0603  # Needed for CLI debug configuration

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
        DEBUG_MODE = True
        # Reconfigure logging for debug mode
        setup_logging(DEBUG_MODE)

    if args.help_extended:
        print("""
Dynamic Dev Container TUI Setup - Python Version

This is a Python implementation of the original install.sh script with enhanced
TUI capabilities using the Textual library.

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
