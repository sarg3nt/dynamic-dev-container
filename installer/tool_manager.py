"""Tool management utilities for development container setup.

This module provides utilities for managing development tools, their versions,
and descriptions. It includes background loading capabilities for better performance.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from installer.constants import (
    DEBUG_MODE,
    DEFAULT_WORKER_COUNT,
    MIN_VERSION_PARTS,
    TOOL_ASSIGNMENT_PARTS,
)

# Get logger
logger = logging.getLogger(__name__)


class BackgroundDescriptionLoader(threading.Thread):
    """Background thread for loading tool descriptions from .mise.toml comments."""

    def __init__(self, tools: list[str], max_workers: int = DEFAULT_WORKER_COUNT) -> None:
        """Initialize the background loader.

        Parameters
        ----------
        tools : list[str]
            List of tool names to load descriptions for
        max_workers : int, optional
            Maximum number of parallel worker threads, by default 5

        """
        super().__init__(daemon=True)
        self.tools = tools
        self.max_workers = max_workers
        self.completed = 0
        self.total = len(tools)
        self.start_time = 0.0
        self.end_time = 0.0
        self._complete = False
        self._completion_event = threading.Event()
        self._lock = threading.Lock()  # For thread-safe counter updates

    def run(self) -> None:
        """Run the background loading process with parallel workers."""
        self.start_time = time.time()

        if DEBUG_MODE:
            logger.debug(
                "Background description loading started for %d tools with %d workers",
                self.total,
                self.max_workers,
            )

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_tool = {executor.submit(self.__load_tool_description, tool): tool for tool in self.tools}

            # Process completed tasks as they finish
            for future in as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    description = future.result()
                    if DEBUG_MODE and description:
                        logger.debug("Loaded description for %s: %s", tool, description[:50] + "...")
                except Exception as e:
                    if DEBUG_MODE:
                        logger.debug("Failed to load description for %s: %s", tool, e)

                # Thread-safe counter update
                with self._lock:
                    self.completed += 1

        self.end_time = time.time()
        self._complete = True
        self._completion_event.set()

        total_time = self.end_time - self.start_time
        if DEBUG_MODE:
            logger.debug(
                "Background description loading completed in %.2f seconds (%d/%d tools)",
                total_time,
                self.completed,
                self.total,
            )

    def __load_tool_description(self, tool: str) -> str | None:
        """Load description for a single tool using .mise.toml comments.

        Parameters
        ----------
        tool : str
            The name of the tool to load description for

        Returns
        -------
        str | None
            The tool description if found, None otherwise

        """
        # Check cache first
        if tool in ToolManager._description_cache:  # noqa: SLF001
            return ToolManager._description_cache[tool]  # noqa: SLF001

        # Get description from .mise.toml comments
        description = ToolManager.__get_mise_description(tool)

        # Use generic fallback if not found
        if not description:
            description = f"{tool} - Development tool"

        # Cache the result
        ToolManager._description_cache[tool] = description  # noqa: SLF001
        return description

    def is_complete(self) -> bool:
        """Check if loading is complete.

        Returns
        -------
        bool
            True if background loading has completed, False otherwise

        """
        return self._complete

    def get_progress(self) -> tuple[int, int]:
        """Get loading progress (completed, total).

        Returns
        -------
        tuple[int, int]
            A tuple containing (completed_count, total_count)

        """
        return self.completed, self.total

    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """Wait for loading to complete with timeout.

        Parameters
        ----------
        timeout : float, optional
            Maximum time to wait in seconds, by default 30.0

        Returns
        -------
        bool
            True if loading completed within timeout, False if timeout occurred

        """
        return self._completion_event.wait(timeout)


class ToolManager:
    """Manages development tools and their versions.

    Tool descriptions are loaded from .mise.toml comments and versions are obtained
    via the 'mise ls-remote' command. No network API calls are made for descriptions.
    """

    # Class-level cache for tool descriptions
    _description_cache: dict[str, str] = {}

    # Background loading system
    _background_loader: BackgroundDescriptionLoader | None = None
    _loading_started = False

    @classmethod
    def start_background_loading(cls, all_tools: list[str], max_workers: int = DEFAULT_WORKER_COUNT) -> None:
        """Start background loading of tool descriptions.

        Parameters
        ----------
        all_tools : list[str]
            List of all tools to load descriptions for
        max_workers : int, optional
            Maximum number of worker threads, by default DEFAULT_WORKER_COUNT

        """
        if not cls._loading_started:
            cls._background_loader = BackgroundDescriptionLoader(all_tools, max_workers=max_workers)
            cls._background_loader.start()
            cls._loading_started = True

    @classmethod
    def is_loading_complete(cls) -> bool:
        """Check if background loading is complete.

        Returns
        -------
        bool
            True if background loading has finished, False otherwise

        """
        return cls._background_loader is not None and cls._background_loader.is_complete()

    @classmethod
    def get_loading_progress(cls) -> tuple[int, int]:
        """Get loading progress (completed, total).

        Returns
        -------
        tuple[int, int]
            A tuple containing (completed_count, total_count) for background loading

        """
        if cls._background_loader is None:
            return 0, 0
        return cls._background_loader.get_progress()

    @classmethod
    def wait_for_loading_complete(cls, timeout: float = 30.0) -> bool:
        """Wait for background loading to complete with timeout.

        Parameters
        ----------
        timeout : float, optional
            Maximum time to wait in seconds, by default 30.0

        Returns
        -------
        bool
            True if loading completed within timeout, False if timeout occurred

        """
        if cls._background_loader is None:
            return True
        return cls._background_loader.wait_for_completion(timeout)

    @staticmethod
    def detect_container_runtime() -> tuple[str, str] | None:
        """Detect available container runtime.

        Returns
        -------
        tuple[str, str] | None
            Tuple of (command, runtime_type) if found, None if no runtime available

        """

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
        """Get latest major versions for a tool, similar to install.sh logic.

        Parameters
        ----------
        tool_name : str
            Name of the tool to get version list for

        Returns
        -------
        list[str]
            List of available versions with 'latest' first, followed by recent major versions

        """
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
        """Get latest major versions for a tool (legacy method for compatibility).

        Parameters
        ----------
        tool_name : str
            Name of the tool to get version display string for

        Returns
        -------
        str
            Formatted string of available versions for display

        """
        versions = ToolManager.get_version_list(tool_name)
        if len(versions) > 1:
            return f"(e.g., {', '.join(versions[1:])})"  # Skip 'latest' for display
        return "(latest version available)"

    @staticmethod
    def get_tool_description(tool: str) -> str:
        """Get description for a development tool from .mise.toml comments.

        Parameters
        ----------
        tool : str
            The name of the tool to get description for

        Returns
        -------
        str
            The tool description, uses fallback if not found in .mise.toml

        """
        # Try to get description from cache first
        cached_desc = ToolManager.__get_cached_description(tool)
        if cached_desc:
            return cached_desc

        # Get description from .mise.toml comments
        description = ToolManager.__get_mise_description(tool)

        # Use generic fallback if not found
        if not description:
            description = f"{tool} - Development tool"

        # Cache the result
        ToolManager.__cache_description(tool, description)
        return description

    @staticmethod
    def __get_cached_description(tool: str) -> str | None:
        """Get cached description for a tool.

        Parameters
        ----------
        tool : str
            The tool name to get cached description for

        Returns
        -------
        str | None
            Cached description if available, None otherwise

        """
        return ToolManager._description_cache.get(tool)

    @staticmethod
    def __cache_description(tool: str, description: str) -> None:
        """Cache description for a tool.

        Parameters
        ----------
        tool : str
            The tool name to cache description for
        description : str
            The description to cache

        """
        ToolManager._description_cache[tool] = description

    @staticmethod
    def __get_mise_description(tool: str) -> str | None:
        """Get tool description from .mise.toml comments.

        Parameters
        ----------
        tool : str
            The name of the tool to get description for

        Returns
        -------
        str | None
            The tool description from .mise.toml comment, None if not found

        """
        try:
            # Look for .mise.toml in current directory or workspace
            mise_file = Path(".mise.toml")
            if not mise_file.exists():
                # Try to find it in the workspace directory
                workspace_paths = [
                    Path("/workspaces/dynamic-dev-container/.mise.toml"),
                    Path.cwd() / ".mise.toml",
                    Path.cwd().parent / ".mise.toml",
                ]
                for path in workspace_paths:
                    if path.exists():
                        mise_file = path
                        break
                else:
                    return None

            with open(mise_file, encoding="utf-8") as f:
                content = f.read()

            # Look for the tool and its comment
            lines = content.split("\n")
            for line in lines:
                stripped = line.strip()
                # Look for lines like: tool = 'version' # description
                if "=" in stripped and "#" in stripped:
                    parts = stripped.split("=", 1)
                    if len(parts) == TOOL_ASSIGNMENT_PARTS:
                        tool_name = parts[0].strip()
                        if tool_name == tool:
                            # Extract comment after #
                            right_side = parts[1]
                            if "#" in right_side:
                                comment = right_side.split("#", 1)[1].strip()
                                if comment and not comment.startswith("version"):
                                    return comment

        except Exception as e:
            if DEBUG_MODE:
                logger.debug("Failed to parse .mise.toml descriptions for %s: %s", tool, e)

        return None
