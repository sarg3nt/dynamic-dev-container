#!/usr/bin/env python3
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
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(tempfile.gettempdir() + "/install_debug.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)


# Check if required dependencies are available
def check_and_install_dependencies() -> None:
    """Check for required dependencies and install them if needed."""
    required_packages = [
        ("textual", "textual[dev]>=0.41.0"),
        ("rich", "rich>=13.0.0"),
        ("toml", "toml>=0.10.0"),
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
    import toml
    from rich.console import Console
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.screen import Screen
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
    )
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    sys.exit(1)


# Constants
MIN_VERSION_PARTS = 2
VERSION_BUTTON_PARTS = 4


class ProjectConfig:
    """Container for project configuration data."""

    def __init__(self) -> None:
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
        self.python_publish_url: str = ""
        self.python_index_url: str = ""
        self.python_extra_index_url: str = ""
        self.python_dev_suffix: str = ""
        self.python_prod_suffix: str = ""
        self.python_repository_type: str = ""

        # Python project metadata
        self.python_project_name: str = ""
        self.python_project_description: str = ""
        self.python_author_name: str = ""
        self.python_author_email: str = ""
        self.python_github_username: str = ""
        self.python_github_project: str = ""
        self.python_license: str = ""
        self.python_keywords: str = ""

        # PSI Header configuration
        self.install_psi_header: bool = False
        self.psi_header_company: str = ""
        self.psi_header_templates: list[tuple[str, str]] = []


class OSDetector:
    """Utility class for detecting OS and package managers."""

    @staticmethod
    def detect_os_and_package_manager() -> str:
        """Detect the OS and return the appropriate package manager."""
        system = platform.system().lower()

        if system == "linux":
            # Check for different Linux distributions
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    content = f.read()

                if any(distro in content.lower() for distro in ["rocky", "rhel", "centos", "fedora", "almalinux"]):
                    if shutil.which("dnf"):
                        return "dnf"
                    if shutil.which("yum"):
                        return "yum"
                elif any(distro in content.lower() for distro in ["ubuntu", "debian"]):
                    if shutil.which("apt-get"):
                        return "apt-get"
                    if shutil.which("apt"):
                        return "apt"
                elif any(distro in content.lower() for distro in ["arch", "manjaro"]):
                    if shutil.which("pacman"):
                        return "pacman"
                elif "opensuse" in content.lower() or "sles" in content.lower():
                    if shutil.which("zypper"):
                        return "zypper"
                elif "alpine" in content.lower():
                    if shutil.which("apk"):
                        return "apk"

        elif system == "darwin" and shutil.which("brew"):
            return "brew"

        return "unknown"

    @staticmethod
    def get_install_command(package_manager: str, package: str) -> list[str] | None:
        """Get the install command for a package manager."""
        commands = {
            "dnf": ["sudo", "dnf", "install", "-y", package],
            "yum": ["sudo", "yum", "install", "-y", package],
            "apt-get": ["sudo", "apt-get", "update", "&&", "sudo", "apt-get", "install", "-y", package],
            "apt": ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y", package],
            "pacman": ["sudo", "pacman", "-Sy", "--noconfirm", package],
            "zypper": ["sudo", "zypper", "install", "-y", package],
            "apk": ["sudo", "apk", "add", package],
            "brew": ["brew", "install", package],
        }
        return commands.get(package_manager)


class ToolManager:
    """Manages development tools and their versions."""

    @staticmethod
    def detect_container_runtime() -> tuple[str, str] | None:
        """Detect available container runtime."""
        import shutil

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
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

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
                    ["mise", "ls-remote", tool_name],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    versions_output = result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass

        # If mise not available or failed, try using container
        if not versions_output:
            versions_output = ToolManager.run_container_command("jdxcode/mise", "mise", "ls-remote", tool_name)

        # Parse versions from output
        lines = versions_output.split("\n")
        versions = []

        for line in lines:
            stripped_line = line.strip()
            # Filter out pre-release versions and non-version lines
            if stripped_line and not any(x in stripped_line.lower() for x in ["rc", "alpha", "beta", "dev", "pre"]):
                # Basic version pattern matching
                if re.match(r"^\d+\.\d+(\.\d+)?", stripped_line):
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
        versions = ToolManager.get_latest_major_versions(tool_name)
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
            line = line.strip()

            if line == "[tools]":
                in_tools_section = True
                continue

            if in_tools_section and line.startswith("[") and line != "[tools]":
                break

            if in_tools_section:
                # Check for section markers (these start with ####)
                begin_match = re.match(r"^#### Begin (.+)$", line)
                if begin_match:
                    current_section = begin_match.group(1)
                    if current_section not in sections:
                        sections.append(current_section)
                    continue

                end_match = re.match(r"^#### End (.+)$", line)
                if end_match:
                    current_section = None
                    continue

                # Check for tool definitions (only when we're in a section)
                if current_section:
                    tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", line)
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
            line = line.strip()

            if line == f"#### Begin {section_name}":
                in_section = True
                continue

            if line == f"#### End {section_name}":
                break

            if in_section:
                tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", line)
                if tool_match:
                    tools.append(tool_match.group(1))

        return tools


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


class WelcomeScreen(Screen[None]):
    """Welcome screen for the installer."""

    BINDINGS = [
        Binding("enter", "continue", "Continue"),
        Binding("q", "quit", "Quit"),
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

Press **ENTER** to continue...
            """),
            id="welcome-container",
        )
        yield Footer()

    def action_continue(self) -> None:
        """Continue to the next screen."""
        """Continue to the next screen."""
        # Call the next step directly
        self.app.call_later(self.app.after_welcome)
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        """Quit the application."""
        self.app.exit()


class PythonRepositoryScreen(Screen[None]):
    """Screen for configuring Python repository settings."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Label("Python Repository Configuration", classes="title"),
            Label("Configure Python package repository settings:"),
            Label("Repository Type:"),
            Container(
                Checkbox("PyPI (default)", id="repo_pypi", value=True),
                Checkbox("Artifactory", id="repo_artifactory"),
                Checkbox("Nexus", id="repo_nexus"),
                Checkbox("Custom", id="repo_custom"),
                id="repo_types",
            ),
            Label("Publishing URL:"),
            Input(placeholder="https://pypi.org/simple/", id="publish_url"),
            Label("Index URL:"),
            Input(placeholder="https://pypi.org/simple/", id="index_url"),
            Label("Extra Index URL (optional):"),
            Input(placeholder="Additional package index", id="extra_index_url"),
            Label("Development Suffix:"),
            Input(value="dev", id="dev_suffix"),
            Label("Production Suffix:"),
            Input(value="prod", id="prod_suffix"),
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save Python repository configuration."""
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
        self.config.python_publish_url = self.query_one("#publish_url", Input).value or "https://pypi.org/simple/"
        self.config.python_index_url = self.query_one("#index_url", Input).value or "https://pypi.org/simple/"
        self.config.python_extra_index_url = self.query_one("#extra_index_url", Input).value
        self.config.python_dev_suffix = self.query_one("#dev_suffix", Input).value or "dev"
        self.config.python_prod_suffix = self.query_one("#prod_suffix", Input).value or "prod"

        self.app.call_later(self.app.after_python_repository)
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

        self.app.call_later(self.app.after_python_project)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class PSIHeaderScreen(Screen[None]):
    """Screen for PSI Header configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Label("PSI Header Configuration", classes="title"),
            Label("Configure PSI Header extension for file templates:"),
            Checkbox("Install PSI Header Extension", id="install_psi", value=self.config.install_psi_header),
            Label("Company Name:"),
            Input(placeholder="Your Company Name", id="company_name"),
            Label("Language Templates:"),
            ScrollableContainer(
                Label("Select languages for custom headers:"),
                Checkbox("Python (.py)", id="lang_python"),
                Checkbox("JavaScript (.js)", id="lang_javascript"),
                Checkbox("TypeScript (.ts)", id="lang_typescript"),
                Checkbox("Go (.go)", id="lang_go"),
                Checkbox("Shell (.sh)", id="lang_shell"),
                Checkbox("YAML (.yml)", id="lang_yaml"),
                Checkbox("JSON (.json)", id="lang_json"),
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        """Save PSI Header configuration."""
        self.config.install_psi_header = self.query_one("#install_psi", Checkbox).value
        self.config.psi_header_company = self.query_one("#company_name", Input).value

        # Collect selected language templates
        self.config.psi_header_templates = []
        language_mappings = {
            "lang_python": ("python", "Python"),
            "lang_javascript": ("javascript", "JavaScript"),
            "lang_typescript": ("typescript", "TypeScript"),
            "lang_go": ("go", "Go"),
            "lang_shell": ("shellscript", "Shell"),
            "lang_yaml": ("yaml", "YAML"),
            "lang_json": ("json", "JSON"),
        }

        for checkbox_id, (lang_id, lang_name) in language_mappings.items():
            if self.query_one(f"#{checkbox_id}", Checkbox).value:
                self.config.psi_header_templates.append((lang_id, lang_name))

        self.app.call_later(self.app.after_psi_header)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class ToolVersionScreen(Screen[None]):
    """Screen for configuring specific tool versions."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
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

        self.app.call_later(self.app.after_tool_versions)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class ProjectConfigScreen(Screen[None]):
    """Screen for project configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
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
        except Exception:
            default_name = "my-project"

        if not default_name or default_name in [".", ".."]:
            default_name = "my-project"

        default_display = default_name.replace("-", " ").replace("_", " ").title()
        default_container = f"{default_name}-container"

        # Generate docker exec command from display name
        words = default_display.split()
        if words:
            default_exec = "".join(word[0].lower() for word in words if word)
        else:
            default_exec = "mp"  # fallback

        yield Header()
        yield Container(
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def action_next(self) -> None:
        """Go to next step."""
        """Save configuration and continue."""
        self.save_config()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()

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
        self.app.call_later(self.app.after_project_config)
        self.app.pop_screen()


class ToolSelectionScreen(Screen[None]):
    """Screen for selecting development tools."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(
        self,
        config: ProjectConfig,
        sections: list[str],
        tool_selected: dict[str, bool],
        tool_version_configurable: dict[str, bool],
        tool_version_value: dict[str, str],
    ):
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

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        if not self.sections:
            yield Container(
                Label("No tool sections found in .mise.toml", classes="title"),
                Button("Next", id="next_btn", variant="primary"),
                id="tools-container",
            )
        else:
            yield Container(
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
                    Button("Previous Section", id="prev_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Section",
                        id="next_section_btn",
                        disabled=self.current_section >= len(self.sections) - 1,
                    ),
                    Button("Finish Tool Selection", id="next_btn", variant="primary"),
                    id="button-row",
                ),
                id="tools-container",
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Called when the screen is mounted."""
        self.refresh_tools()

    def refresh_tools(self) -> None:
        """Refresh the tools display for current section."""
        if not self.sections:
            return

        tools_container = self.query_one("#tools-scroll", ScrollableContainer)
        tools_container.remove_children()

        current_section = self.sections[self.current_section]
        tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

        if not tools:
            no_tools_label = Label("No tools found in this section", classes="compact")
            tools_container.mount(no_tools_label)
            return

        for tool in tools:
            description = ToolManager.get_tool_description(tool)

            # Add checkbox for the tool (no version buttons in left panel anymore)
            checkbox = Checkbox(description, id=f"tool_{tool}", classes="compact")
            checkbox.value = self.tool_selected.get(tool, False)

            tools_container.mount(checkbox)  # Update configuration panel
        self.refresh_configuration()

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
            if selected_tools_in_section:
                # Show Python configuration if selected in current section
                if "python" in selected_tools_in_section:
                    # Repository type
                    config_container.mount(Label("Repository Type:", classes="compact section-header"))
                    python_repo_container = Container(
                        RadioSet(
                            RadioButton("PyPI", id="py_repo_pypi", value=True, classes="compact"),
                            RadioButton("Artifactory", id="py_repo_artifactory", classes="compact"),
                            RadioButton("Custom", id="py_repo_custom", classes="compact"),
                            id="py_repo_radioset",
                        ),
                        classes="compact-group",
                    )
                    config_container.mount(python_repo_container)

                    # URLs (compact inputs)
                    config_container.mount(Label("Index URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            placeholder="https://pypi.org/simple/",
                            id="py_index_url",
                            classes="compact-input",
                        ),
                    )

            # Clean up any existing version inputs before creating new ones
            self._cleanup_version_inputs()

            # Show version configuration ONLY for configurable tools selected in the CURRENT section
            # (not all sections) to keep the interface section-specific
            configurable_tools_in_current_section = [
                tool for tool in selected_tools_in_section if self.tool_version_configurable.get(tool, False)
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
                    versions = ToolManager.get_version_list(tool)

                    for version in versions:
                        # Replace dots with underscores for valid CSS identifiers
                        safe_version = version.replace(".", "_")
                        version_btn = Button(
                            version,
                            id=f"version_btn_{tool}_{safe_version}",
                            classes="version-btn-small",
                        )
                        tool_version_container.mount(version_btn)

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

            # Update configuration panel when selections change
            self.refresh_configuration()
        elif event.checkbox.id.startswith("py_repo_"):
            # Handle Python repository type selection
            if event.value:
                # Uncheck other repository types
                for repo_type in ["py_repo_pypi", "py_repo_artifactory", "py_repo_custom"]:
                    if repo_type != event.checkbox.id:
                        try:
                            checkbox = self.query_one(f"#{repo_type}", Checkbox)
                            checkbox.value = False
                        except Exception:
                            pass  # Checkbox might not exist yet

    def _cleanup_version_inputs(self) -> None:
        """Remove any existing version input widgets to prevent duplicates."""
        try:
            # Find and remove all version input widgets
            for tool in list(self.tool_version_configurable.keys()):
                try:
                    version_widget = self.query_one(f"#version_{tool}", Input)
                    version_widget.remove()
                except Exception:
                    pass  # Widget might not exist
        except Exception:
            pass  # Ignore cleanup errors

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
                except Exception:
                    # Input might not exist yet, which is fine
                    pass
            return

        if button_id == "prev_btn":
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

    def refresh_controls(self) -> None:
        """Refresh button states."""
        prev_btn = self.query_one("#prev_btn", Button)
        next_section_btn = self.query_one("#next_section_btn", Button)

        prev_btn.disabled = self.current_section == 0
        next_section_btn.disabled = self.current_section >= len(self.sections) - 1

        # Update title and subtitle
        title_label = self.query_one("Label")
        title_label.update(f"Development Tools - {self.sections[self.current_section]}")

        # Update subtitle showing section progress
        try:
            subtitle_label = self.query_one("Label.subtitle")
            subtitle_label.update(f"Section {self.current_section + 1} of {len(self.sections)}")
        except Exception:
            # Subtitle might not exist yet
            pass

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
            except Exception:
                # Checkbox might not exist
                pass

        # Save any configuration values
        self.save_configuration_values()

    def save_configuration_values(self) -> None:
        """Save current configuration values from input fields."""
        # Save Python configuration
        try:
            if self.query_one("#py_repo_pypi", Checkbox).value:
                self.config.python_repository_type = "PyPI"
            elif self.query_one("#py_repo_artifactory", Checkbox).value:
                self.config.python_repository_type = "Artifactory"
            elif self.query_one("#py_repo_custom", Checkbox).value:
                self.config.python_repository_type = "Custom"
        except Exception:
            pass

        try:
            self.config.python_index_url = self.query_one("#py_index_url", Input).value
        except Exception:
            pass

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
                except Exception:
                    try:
                        # Fallback to simple ID format
                        version_input = self.query_one(f"#version_{tool}", Input)
                        self.tool_version_value[tool] = version_input.value or "latest"
                    except Exception:
                        pass

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
        self.app.call_later(self.app.after_tool_selection)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        """Continue to next screen."""
        self.save_current_section()
        self.finalize_selection()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


class SummaryScreen(Screen[None]):
    """Summary screen showing final configuration."""

    BINDINGS = [
        Binding("enter", "install", "Install"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        super().__init__()
        self.config = config

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
                if version != "latest":
                    summary += f"- **{tool}** ({version})\n"
                else:
                    summary += f"- **{tool}**\n"
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

    def action_install(self) -> None:
        """Start the installation process."""
        self.app.call_later(self.app.after_summary)
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go to previous step."""
        """Go back to previous screen."""
        self.app.pop_screen()


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

    def create_project_directory(self):
        """Create project directory if it doesn't exist."""
        project_path = Path(self.config.project_path)
        project_path.mkdir(parents=True, exist_ok=True)

    def copy_files(self):
        """Copy files and directories to target."""
        source_dir = self.source_dir
        target_dir = Path(self.config.project_path)

        FileManager.copy_files_and_directories(
            source_dir,
            target_dir,
            include_python=self.config.install_python_tools,
        )

    def generate_mise_toml(self):
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

    def generate_devcontainer_json(self):
        """Generate custom devcontainer.json based on configuration."""
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        target_file = Path(self.config.project_path) / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            return

        # This is a simplified version - in practice, you'd want to parse and modify JSON
        # For now, copy and do basic replacements
        with open(source_file) as f:
            content = f.read()

        # Replace basic values
        content = content.replace(
            '"name": "Dynamic Dev Container"',
            f'"name": "{self.config.display_name}"',
        )
        content = content.replace(
            "--name=dynamic-dev-container",
            f"--name={self.config.container_name}",
        )
        content = content.replace(
            "dynamic-dev-container-shellhistory",
            f"{self.config.container_name}-shellhistory",
        )
        content = content.replace(
            "dynamic-dev-container-plugins",
            f"{self.config.container_name}-plugins",
        )

        # Write modified content
        with open(target_file, "w") as f:
            f.write(content)

    def update_dev_sh(self):
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

    def update_pyproject_toml(self):
        """Update pyproject.toml with Python project configuration."""
        target_file = Path(self.config.project_path) / "pyproject.toml"

        if not target_file.exists() or not self.config.python_project_name:
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

        # Replace description if provided
        if self.config.python_project_description:
            content = re.sub(
                r'description = "A brief description of your project"',
                f'description = "{self.config.python_project_description}"',
                content,
            )

        # Replace author information
        if self.config.python_author_name and self.config.python_author_email:
            author_line = f'"{self.config.python_author_name} <{self.config.python_author_email}>"'
            content = re.sub(
                r'authors = \["Your Name <your\.email@example\.com>"\]',
                f"authors = [{author_line}]",
                content,
            )
        elif self.config.python_author_name:
            content = re.sub(
                r'authors = \["Your Name <your\.email@example\.com>"\]',
                f'authors = ["{self.config.python_author_name}"]',
                content,
            )

        # Replace license
        if self.config.python_license:
            content = re.sub(
                r'license = "MIT"',
                f'license = "{self.config.python_license}"',
                content,
            )

        # Replace keywords
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

        with open(target_file, "w") as f:
            f.write(content)

    def configure_psi_header(self):
        """Configure PSI Header extension settings."""
        if not self.config.install_psi_header:
            return

        settings_dir = Path(self.config.project_path) / ".vscode"
        settings_file = settings_dir / "settings.json"

        settings_dir.mkdir(exist_ok=True)

        # Basic PSI Header configuration
        psi_config = {
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
            template_config = {
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
        existing_settings = {}
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

    def configure_python_repository_settings(self):
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

    def show_completion(self):
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
        console.print(f"2. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
        console.print(f"3. Review tool versions in {self.config.project_path}/.mise.toml")
        console.print(f"\n[blue]You can now run:[/blue] cd {self.config.project_path} && ./dev.sh")

        # Exit after showing completion
        self.app.call_later(self.app.exit)


class DynamicDevContainerApp(App):
    """Main application class."""

    CSS_PATH = "install.tcss"

    def __init__(self, project_path: str = ""):
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

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Called when app is mounted."""
        self.push_screen(WelcomeScreen(), self.after_welcome)

    def after_welcome(self):
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

    def after_project_config(self):
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

    def show_tool_selection(self):
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

    def after_tool_selection(self):
        """Called after tool selection screen."""

        # Skip Python-specific screens since configuration is now inline
        # Go directly to tool version configuration or next step
        self.check_tool_versions()

    def after_python_repository(self):
        """Called after Python repository configuration."""
        # Show Python project metadata screen
        self.push_screen(PythonProjectScreen(self.config), self.after_python_project)

    def after_python_project(self):
        """Called after Python project metadata configuration."""
        # Return to tool selection to allow selection of other tools
        self.show_tool_selection()

    def check_tool_versions(self):
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

    def after_tool_versions(self):
        """Called after tool version configuration."""
        # Show PSI Header configuration
        self.show_psi_header_config()

    def show_psi_header_config(self):
        """Show PSI Header configuration screen."""
        self.push_screen(PSIHeaderScreen(self.config), self.after_psi_header)

    def after_psi_header(self):
        """Called after PSI Header configuration."""
        # Now show summary
        self.push_screen(SummaryScreen(self.config), self.after_summary)

    def after_summary(self):
        """Called after summary screen."""
        self.push_screen(InstallationScreen(self.config, self.source_dir))


def main() -> None:
    """Main entry point."""
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

    args = parser.parse_args()

    if args.help_extended:
        print("""
Dynamic Dev Container TUI Setup - Python Version

This is a Python implementation of the original install.sh script with enhanced
TUI capabilities using the Textual library.

Usage: python install.py [project_path]

Arguments:
  project_path    Path where the dev container will be created
                  If not provided, you'll be prompted to enter it

Examples:
  python install.py ~/my-project
  python install.py /workspace/new-project
  python install.py  # Will prompt for path

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
