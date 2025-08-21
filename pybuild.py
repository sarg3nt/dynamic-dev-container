#!/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""Build and deploy Python packages to configurable repositories."""

# cSpell:ignore kairos sysinfra pytest Dproject CREDS qube pybuild

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import NamedTuple

from loguru import logger
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Define constants
FILE_CHANGE_DEBOUNCE_SECONDS = 3
SPINNER_STATES = ["|", "/", "-", "\\"]
PYTHON_FILE_EXTENSION = ".py"
DIST_DIR_NAME = "dist"
WHEEL_EXTENSION = ".whl"


class PyBuildError(Exception):
    """Base exception for PyBuild operations."""


class ConfigurationError(PyBuildError):
    """Raised when configuration is invalid or missing."""


class CommandError(PyBuildError):
    """Raised when a command execution fails."""


class PyBuildConfig(NamedTuple):
    """Configuration data for PyBuild operations."""

    package_name: str
    install_index_url: str
    install_extra_index_url: str | None = None
    hatch_repos: dict[str, str] | None = None


def load_config() -> PyBuildConfig:
    """Load configuration from pyproject.toml.

    Returns
    -------
    PyBuildConfig
        Configuration with repository URLs and settings.

    Raises
    ------
    ConfigurationError
        If required configuration is missing from pyproject.toml.

    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        msg = "pyproject.toml file not found. This file is required for configuration."
        raise ConfigurationError(msg)

    try:
        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)
    except Exception as e:
        msg = f"Could not parse pyproject.toml file: {e}"
        raise ConfigurationError(msg) from e

    # Get package name from project section
    project_section = pyproject_data.get("project", {})
    package_name = project_section.get("name")
    if not package_name:
        msg = "Package name not found in pyproject.toml [project] section."
        raise ConfigurationError(msg)

    # Get pip configuration for install URLs
    tool_section = pyproject_data.get("tool", {})
    pip_config = tool_section.get("pip", {})
    install_index_url = pip_config.get("index-url", "https://pypi.org/simple/")

    # Get Hatch repository configuration (optional)
    hatch_section = tool_section.get("hatch", {})
    publish_section = hatch_section.get("publish", {})
    index_section = publish_section.get("index", {})
    repos_section = index_section.get("repos", {})

    # Extract repository URLs from Hatch configuration
    hatch_repos = {}
    for repo_name, repo_config in repos_section.items():
        if isinstance(repo_config, dict) and "url" in repo_config:
            hatch_repos[repo_name] = repo_config["url"]

    return PyBuildConfig(
        package_name=package_name,
        install_index_url=install_index_url,
        install_extra_index_url=None,  # Can be added to pip config if needed
        hatch_repos=hatch_repos if hatch_repos else None,
    )


def get_install_urls(config: PyBuildConfig) -> tuple[str, str]:
    """Get the install URLs.

    Parameters
    ----------
    config : PyBuildConfig
        Configuration data

    Returns
    -------
    tuple[str, str]
        Index URL and extra index URL

    """
    base_index = config.install_index_url
    extra_index = config.install_extra_index_url or ""

    return base_index, extra_index


def static_analysis() -> None:
    """Run static analysis using SonarQube."""
    logger.info("Running static analysis.")

    # Check if sonar-scanner exists
    if not shutil.which("sonar-scanner"):
        msg = (
            "The 'sonar-scanner' binary is not found in PATH. Please install it. "
            "This command is meant to be run from the SonarQube docker container."
        )
        raise CommandError(msg)

    sonar_memory_limit = os.getenv("SONAR_MEMORY_LIMIT", "1024")
    repo_root = Path(__file__).parent
    command = [
        "sonar-scanner",
        "-X",
        f"-Dproject.settings={repo_root}/sonar-project.properties",
    ]
    env = {"SONAR_SCANNER_OPTS": f"-Xmx{sonar_memory_limit}m"}
    run_command(command, env=env)

    logger.success("Static analysis complete.")


def test() -> None:
    """Run Python tests using pytest."""
    logger.info("Running Python tests.")

    # Try to find tests directory in common locations
    test_paths = [Path("tests"), Path("test"), Path("/workspaces/tests")]
    test_path = None

    for path in test_paths:
        if path.exists():
            test_path = path
            break

    if not test_path:
        # Default to current directory if no test directory found
        test_path = Path(".")
        logger.warning(
            "No dedicated test directory found, running tests from current directory",
        )

    run_command(["pytest", "-s", str(test_path)])
    logger.success("Tests complete.")


def dev(continuously: bool = False) -> None:
    """Build, publish to the dev environment, and install the Python library.

    Parameters
    ----------
    continuously: bool
        If True, monitor the `src` directory for file changes and rerun the commands.

    """
    config = load_config()
    package_name = config.package_name

    logger.info(f"Building and publishing {package_name} Python library to dev.")

    if not continuously:
        build()
        install_local(quiet=True)
        logger.success("Dev build and publish complete.")
        return

    logger.info("Running in continuous mode. Monitoring for file changes in 'src'.")

    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path="src", recursive=True)
    observer.start()

    try:
        _continuous_build_loop(event_handler)
    except KeyboardInterrupt:
        logger.info("Stopping continuous mode.")
    finally:
        observer.stop()
        observer.join()


def _continuous_build_loop(event_handler: ChangeHandler) -> None:
    """Run the main loop for continuous building."""
    last_modified_time = None
    spinner_index = 0

    # Hide cursor at start of continuous mode
    print("\033[?25l", end="", flush=True)

    try:
        while True:
            if event_handler.modified:
                last_modified_time = time.time()
                event_handler.modified = False
                print(
                    "  \033[94m\033[0m  ",
                    end="",
                    flush=True,
                )  # Blue save icon for file change

            current_time = time.time()
            if last_modified_time and current_time - last_modified_time >= FILE_CHANGE_DEBOUNCE_SECONDS:
                _execute_build_cycle()
                last_modified_time = None

            elif last_modified_time and current_time - last_modified_time < FILE_CHANGE_DEBOUNCE_SECONDS:
                _show_spinner(spinner_index)
                spinner_index = (spinner_index + 1) % len(SPINNER_STATES)

            if not last_modified_time:
                _show_spinner(spinner_index)
                spinner_index = (spinner_index + 1) % len(SPINNER_STATES)

            time.sleep(0.1)
    finally:
        # Show cursor again when exiting
        print("\033[?25h", end="", flush=True)


def _execute_build_cycle() -> None:
    """Execute a single build and install cycle."""
    build(quiet=True)
    print(
        "  \033[92m🐍\033[0m ",
        end="",
        flush=False,
    )  # Green python icon for build complete
    install_local(quiet=True)
    print("\033[92m➡\033[0m", end="", flush=False)  # Green -> icon for install complete


def _show_spinner(index: int) -> None:
    """Show a spinner animation."""
    print(f"\r\033[97m{SPINNER_STATES[index]}\033[0m", end="", flush=False)


def build(quiet: bool = False) -> None:
    """Build the Python library.

    Parameters
    ----------
    quiet: bool
        If True, suppress logging output and console output from commands.

    """
    config = load_config()
    package_name = config.package_name

    if not quiet:
        logger.info(f"Building {package_name} Python library.")

    # Check if this is actually a buildable Python package
    # Look for version file or source directory
    version_path = Path("src") / package_name.replace("-", "_") / "__about__.py"
    src_dir = Path("src")

    if not src_dir.exists():
        msg = (
            f"No 'src' directory found. This appears to be a template or development environment "
            f"rather than a Python package. To build a package, you need:\n"
            f"1. A 'src' directory with your package code\n"
            f"2. A version file at: {version_path}\n"
            f"3. Proper package structure as defined in pyproject.toml"
        )
        raise CommandError(msg)

    if not version_path.exists():
        msg = (
            f"Version file not found at: {version_path}\n"
            f"Please create this file with a __version__ variable, for example:\n"
            f'__version__ = "0.1.0"'
        )
        raise CommandError(msg)

    run_command(["hatch", "build"], quiet=quiet)
    if not quiet:
        logger.success("Build complete.")


def publish(env: str, quiet: bool = False) -> None:
    """Publish the Python library.

    Parameters
    ----------
    env: str
        The environment to publish to (e.g., 'dev' or 'prod').
    quiet: bool
        If True, suppress logging output and console output from commands.

    """
    config = load_config()
    package_name = config.package_name

    if not quiet:
        logger.info(f"Publishing {package_name} Python library to {env}.")

    # For Hatch-based publishing, we try to find a matching repository
    repo_name = None
    repo_url = None
    if config.hatch_repos:
        # Look for environment-specific repos
        env_repo_key = f"sysinfra-{env}"  # Updated to match actual repo names
        alt_env_repo_key = f"artifactory-{env}" if env in ["dev", "prod"] else None
        nexus_env_repo_key = f"nexus-{env}" if env in ["dev", "prod"] else None

        # Try different naming patterns
        for key in [env_repo_key, alt_env_repo_key, nexus_env_repo_key]:
            if key and key in config.hatch_repos:
                repo_name = key
                repo_url = config.hatch_repos[key]
                break

        # If no environment-specific repo found, use the first available repo
        if not repo_name and config.hatch_repos:
            repo_name = next(iter(config.hatch_repos.keys()))
            repo_url = config.hatch_repos[repo_name]

    # Build the hatch publish command
    publish_cmd = ["hatch", "publish", "-y"]

    # Use environment variable approach since pyproject.toml repos aren't being read properly
    if repo_url:
        # Set HATCH_INDEX_REPO to the URL directly
        env_vars = {"HATCH_INDEX_REPO": repo_url}
        run_command(publish_cmd, env=env_vars, quiet=quiet)
    elif repo_name:
        publish_cmd.extend(["-r", repo_name])
        run_command(publish_cmd, quiet=quiet)
    else:
        # If no repo specified, Hatch will use the default (PyPI)
        run_command(publish_cmd, quiet=quiet)

    if not quiet:
        logger.success("Publish complete.")


def install(quiet: bool = False) -> None:
    """Install the Python library.

    Parameters
    ----------
    quiet: bool
        If True, suppress logging output and console output from commands.

    """
    config = load_config()
    package_name = config.package_name

    if not quiet:
        logger.info(f"Installing {package_name} Python library.")

    index_url, extra_index_url = get_install_urls(config)

    no_deps = "--no-deps" if is_package_installed(package_name) else ""

    install_cmd = [
        "pip",
        "install",
        "--force-reinstall",
        "--disable-pip-version-check",
        no_deps,
        "--index-url",
        index_url,
    ]

    if extra_index_url:
        install_cmd.extend(["--extra-index-url", extra_index_url])

    install_cmd.append(package_name)

    run_command(install_cmd, quiet=quiet)

    if not quiet:
        logger.success("Installation complete.")


def install_local(quiet: bool = False) -> None:
    """Install the locally built Python library.

    Parameters
    ----------
    quiet: bool
        If True, suppress logging output and console output from commands.

    """
    config = load_config()
    package_name = config.package_name

    if not quiet:
        logger.info(f"Installing {package_name} Python library from local build.")

    dist_dir = Path(__file__).parent / DIST_DIR_NAME
    if not dist_dir.exists():
        msg = "No 'dist' directory found. Please build the library first."
        raise CommandError(msg)

    wheel_files = list(dist_dir.glob(f"*{WHEEL_EXTENSION}"))
    if not wheel_files:
        msg = "No wheel file found in the 'dist' directory. Please build the library first."
        raise CommandError(msg)

    no_deps = "--no-deps" if is_package_installed(package_name) else ""
    latest_wheel = sorted(wheel_files)[-1]  # Pick the latest wheel file
    run_command(
        [
            "pip",
            "install",
            "--force-reinstall",
            "--disable-pip-version-check",
            no_deps,
            str(latest_wheel),
        ],
        quiet=quiet,
    )

    if not quiet:
        logger.success("Local installation complete.")


############################################################
# Utilities
###########################################################


def is_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed.

    Parameters
    ----------
    package_name: str
        The name of the package to check.

    Returns
    -------
    bool
        True if the package is installed, False otherwise.

    """
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_requirements(task: str) -> None:
    """Check required environment variables based on the task.

    Parameters
    ----------
    task : str
        The task being performed (dev, build, publish, test, static_analysis)

    """
    logger.info("Checking environment variables.")

    # Only check publishing credentials for publish task
    if task == "publish":
        hatch_user = os.getenv("HATCH_INDEX_USER")
        hatch_auth = os.getenv("HATCH_INDEX_AUTH")

        if not hatch_user:
            logger.error(
                "HATCH_INDEX_USER environment variable must be set for publishing.",
            )
            sys.exit(1)

        if not hatch_auth:
            logger.error(
                "HATCH_INDEX_AUTH environment variable must be set for publishing.",
            )
            sys.exit(1)

    logger.success("Environment variables are set.")


def run_command(
    command: list[str],
    env: dict[str, str] | None = None,
    quiet: bool = False,
) -> None:
    """Run a shell command with optional environment variables.

    Parameters
    ----------
    command: list[str]
        The command to execute as a list of strings.
    env: dict[str, str] | None
        Optional environment variables to set for the command.
    quiet: bool
        If True, suppress console output.

    Raises
    ------
    CommandError
        If the command fails.

    """
    logger.debug(f"Running command: {' '.join(command)}")

    # Filter out empty strings from command
    command = [arg for arg in command if arg]

    # Prepare environment - merge with current environment
    final_env = os.environ.copy()
    if env:
        final_env.update(env)

    try:
        subprocess.run(
            command,
            check=True,
            env=final_env,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed with exit code {e.returncode}: {' '.join(command)}"
        if not quiet:
            logger.error(error_msg)
        raise CommandError(error_msg) from e


class ChangeHandler(FileSystemEventHandler):
    """Handler to track file changes in the src directory."""

    def __init__(self) -> None:
        """Initialize the ChangeHandler and set the modified flag to False."""
        super().__init__()
        self.modified = False

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle the event when a file is modified.

        Parameters
        ----------
        event : FileSystemEvent
            The file system event object containing information about the modified file.

        """
        if event.is_directory:
            return

        src_path = str(event.src_path)
        if src_path.endswith(PYTHON_FILE_EXTENSION):  # Monitor only Python files
            self.modified = True


def parse_arguments() -> argparse.ArgumentParser:
    """Parse command-line arguments.

    Returns
    -------
    argparse.ArgumentParser
        Argument parser.

    """
    parser = argparse.ArgumentParser(
        prog="pybuild.py",
        description="Build and deploy Python packages to configurable repositories.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="task", required=False)

    # Subparser for 'dev'
    dev_parser = subparsers.add_parser(
        "dev",
        help="Build, publish to the dev environment, and install the library.",
    )
    dev_parser.add_argument(
        "-c",
        "--continuously",
        action="store_true",
        help="Monitor the `src` directory for file changes and rerun the commands.",
    )

    # Subparser for 'build'
    subparsers.add_parser(
        "build",
        help="Build the Python library.",
    )

    # Subparser for 'publish'
    publish_parser = subparsers.add_parser(
        "publish",
        help="Publish the Python library to the specified environment. ['dev','prod']",
    )
    publish_parser.add_argument(
        "env",
        choices=["dev", "prod"],
        help="The environment to publish to, 'dev', or 'prod'",
    )

    # Subparser for 'test'
    subparsers.add_parser(
        "test",
        help="Run Python tests using pytest.",
    )

    # Subparser for 'static_analysis'
    subparsers.add_parser(
        "static_analysis",
        help="Run static analysis using SonarQube.",
    )

    return parser


def main() -> None:
    """Run the build script main entry point."""
    logger.remove()
    logger.level("INFO", color="<fg 92,168,255>")
    logger.add(
        sys.stdout,
        colorize=True,
        format="<fg 100,100,100>[{time:HH:mm:ss}] {module}.{function}.{line}</> <level>{level}: {message}</level>",
        level=os.environ.get("CM_LOG_LEVEL", "INFO"),
    )

    parser = parse_arguments()
    args = parser.parse_args()

    # Show help if no arguments are provided
    if not args.task:
        parser.print_help()
        sys.exit(0)

    try:
        check_requirements(args.task)

        match args.task:
            case "dev":
                dev(continuously=args.continuously)
            case "build":
                build()
            case "publish":
                publish(args.env)
            case "test":
                test()
            case "static_analysis":
                static_analysis()
            case _:
                logger.error(f"Invalid task: {args.task}")
                sys.exit(1)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except CommandError as e:
        logger.error(f"Command error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
