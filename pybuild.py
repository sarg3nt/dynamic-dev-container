#!/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""Build and deploy Python packages to configurable repositories."""

# cSpell:ignore kairos sysinfra pytest Dproject CREDS qube pybuild

import argparse
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Define a constant for the file change debounce interval (in seconds)
FILE_CHANGE_DEBOUNCE_SECONDS = 3


def load_config() -> dict[str, object]:
    """Load configuration from pyproject.toml.

    Returns
    -------
    config : dict[str, object]
        Configuration dictionary with repository URLs and settings.

    Raises
    ------
    SystemExit
        If required configuration is missing from pyproject.toml.

    """

    config: dict[str, object] = {}

    try:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            logger.error("pyproject.toml file not found. This file is required for configuration.")
            sys.exit(1)

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Get package name from project section
        if "project" in pyproject_data and "name" in pyproject_data["project"]:
            config["package_name"] = pyproject_data["project"]["name"]
        else:
            logger.error("Package name not found in pyproject.toml [project] section.")
            sys.exit(1)

        # Get repository configuration from tool.pybuild section
        if "tool" in pyproject_data and "pybuild" in pyproject_data["tool"]:
            pybuild_config = pyproject_data["tool"]["pybuild"]
            # Load all pybuild configuration values
            config.update(pybuild_config)
        else:
            logger.error("Repository configuration not found in pyproject.toml [tool.pybuild] section.")
            logger.info("Please run the install.sh script to configure your repository settings.")
            sys.exit(1)

        # Validate required configuration
        if not config.get("publish_base_url"):
            logger.error("publish_base_url must be configured in pyproject.toml [tool.pybuild] section.")
            sys.exit(1)
        if not config.get("install_index_url"):
            logger.error("install_index_url must be configured in pyproject.toml [tool.pybuild] section.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Could not load pyproject.toml configuration: {e}")
        logger.info("Please check your pyproject.toml file format and configuration.")
        sys.exit(1)

    return config


def get_publish_url(env: str, config: dict[str, object]) -> str:
    """Get the publish URL for the specified environment.

    Parameters
    ----------
    env : str
        Environment ('dev' or 'prod')
    config : dict[str, object]
        Configuration dictionary

    Returns
    -------
    str
        Repository URL for publishing

    """

    base_url = str(config["publish_base_url"])
    suffix = str(config.get("dev_suffix", "")) if env == "dev" else str(config.get("prod_suffix", ""))

    # Handle different URL patterns
    if "artifactory" in base_url and suffix:
        # For Artifactory: append suffix to repository name
        return base_url + suffix

    if suffix and base_url and "pypi.org" not in base_url:
        # For custom repositories with suffix (but not PyPI)
        return base_url + suffix

    # For PyPI or repositories without suffix
    return base_url


def get_install_urls(config: dict[str, object], use_dev: bool = False) -> tuple[str, str]:
    """Get the install URLs.

    Parameters
    ----------
    config : dict[str, object]
        Configuration dictionary
    use_dev : bool
        Whether to use dev environment URLs

    Returns
    -------
    tuple[str, str]
        Index URL and extra index URL

    """
    base_index = str(config["install_index_url"])
    extra_index = str(config.get("install_extra_index_url", ""))

    dev_suffix = str(config.get("dev_suffix", ""))
    if use_dev and dev_suffix:
        # Modify URLs for dev environment if needed
        if "artifactory" in base_index:
            base_index = base_index.replace("/simple", dev_suffix + "/simple")
        if extra_index and "artifactory" in extra_index:
            extra_index = extra_index.replace("/simple", dev_suffix + "/simple")

    return base_index, extra_index


def static_analysis() -> None:
    """Run static analysis using SonarQube."""

    logger.info("Running static analysis.")

    # Check if sonar-scanner exists
    if not shutil.which("sonar-scanner"):
        sys.tracebacklimit = 0  # Suppress traceback for this exception
        file_not_found_error = "The 'sonar-scanner' binary is not found in PATH. Please install it.  This command is meant to be ran from the SonarQube docker container."
        raise FileNotFoundError(file_not_found_error)

    sonar_memory_limit = os.getenv("SONAR_MEMORY_LIMIT", "1024")
    repo_root = os.path.dirname(os.path.realpath(__file__))
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
    test_paths = ["tests", "test", "/workspaces/tests"]
    test_path = None

    for path in test_paths:
        if os.path.exists(path):
            test_path = path
            break

    if not test_path:
        # Default to current directory if no test directory found
        test_path = "."
        logger.warning("No dedicated test directory found, running tests from current directory")

    run_command(["pytest", "-s", test_path])

    logger.success("Tests complete.")


def dev(continuously: bool = False) -> None:
    """Build, publish to the dev environment, and install the Python library.

    Parameters
    ----------
    continuously: bool
        If True, monitor the `src` directory for file changes and rerun the commands.

    """
    config = load_config()
    package_name = config["package_name"]

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
    spinner_states = ["|", "/", "-", "\\"]  # Spinner characters

    try:
        last_modified_time = None
        spinner_index = 0  # Index to track the current spinner state
        while True:
            if event_handler.modified:
                last_modified_time = time.time()
                event_handler.modified = False
                print(
                    "  \033[94m\033[0m  ",
                    end="",
                    flush=True,
                )  # Blue save icon for file change

            if last_modified_time and time.time() - last_modified_time >= FILE_CHANGE_DEBOUNCE_SECONDS:
                build(quiet=True)
                print(
                    "  \033[92m\033[0m ",
                    end="",
                    flush=False,
                )  # Green python icon for build complete
                install_local(quiet=True)
                print(
                    "\033[92m\033[0m",
                    end="",
                    flush=False,
                )  # Green -> icon for install complete

                last_modified_time = None  # Reset the timer after running commands
            elif last_modified_time and time.time() - last_modified_time < FILE_CHANGE_DEBOUNCE_SECONDS:
                print(
                    f"\r\033[97m{spinner_states[spinner_index]}\033[0m",
                    end="",
                    flush=False,
                )  # Spinner animation
                spinner_index = (spinner_index + 1) % len(
                    spinner_states,
                )  # Update spinner index

            if not last_modified_time:
                print(
                    f"\r\033[97m{spinner_states[spinner_index]}\033[0m",
                    end="",
                    flush=False,
                )  # Spinner animation
                spinner_index = (spinner_index + 1) % len(
                    spinner_states,
                )  # Update spinner index

            time.sleep(0.1)  # Polling interval
    except KeyboardInterrupt:
        logger.info("Stopping continuous mode.")
    finally:
        observer.stop()
        observer.join()


def build(quiet: bool = False) -> None:
    """Build the Python library.

    Parameters
    ----------
    quiet: bool
        If True, suppress logging output and console output from commands.

    """
    config = load_config()
    package_name = config["package_name"]

    if not quiet:
        logger.info(f"Building {package_name} Python library.")
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
    package_name = config["package_name"]

    if not quiet:
        logger.info(f"Publishing {package_name} Python library to {env}.")

    repo_url = get_publish_url(env, config)
    run_command(["hatch", "publish", "-y", "--repo", repo_url], quiet=quiet)

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
    package_name = config["package_name"]

    if not quiet:
        logger.info(f"Installing {package_name} Python library.")

    index_url, extra_index_url = get_install_urls(config, use_dev=True)

    no_deps = "--no-deps" if is_package_installed(str(package_name)) else ""

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

    install_cmd.append(str(package_name))

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
    package_name = config["package_name"]

    if not quiet:
        logger.info(f"Installing {package_name} Python library from local build.")

    dist_dir = os.path.join(os.path.dirname(__file__), "dist")
    wheel_files = [f for f in os.listdir(dist_dir) if f.endswith(".whl")]

    if not wheel_files:
        logger.error(
            "No wheel file found in the 'dist' directory. Please build the library first.",
        )
        return

    no_deps = "--no-deps" if is_package_installed(str(package_name)) else ""
    latest_wheel = sorted(wheel_files)[-1]  # Pick the latest wheel file
    run_command(
        [
            "pip",
            "install",
            "--force-reinstall",
            "--disable-pip-version-check",
            no_deps,
            os.path.join(dist_dir, latest_wheel),
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


def check_requirements() -> None:
    """Check required environment variables."""

    logger.info("Checking environment variables.")

    hatch_user = os.getenv("HATCH_INDEX_USER")
    hatch_auth = os.getenv("HATCH_INDEX_AUTH")

    if not hatch_user:
        logger.error("HATCH_INDEX_USER environment variable must be set.")
        sys.exit(1)

    if not hatch_auth:
        logger.error("HATCH_INDEX_AUTH environment variable must be set.")
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
    subprocess.CalledProcessError
        If the command fails.

    """

    logger.debug(f"Running command: {' '.join(command)}")

    try:
        subprocess.run(
            command,
            check=True,
            env=env,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
        )
    except subprocess.CalledProcessError as e:
        if not quiet:
            logger.error(f"Command failed: {e}")
        raise


class ChangeHandler(FileSystemEventHandler):
    """Handler to track file changes in the src directory."""

    modified: bool

    def __init__(self) -> None:
        """Initialize the ChangeHandler and set the modified flag to False."""
        self.modified = False

    from watchdog.events import FileSystemEvent

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle the event when a file is modified.

        Parameters
        ----------
        event : FileSystemEvent
            The file system event object containing information about the modified file.

        """

        src_path = event.src_path.decode() if isinstance(event.src_path, bytes) else event.src_path
        if src_path.endswith(".py"):  # Monitor only Python files
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
    """Main entry point for the script."""

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

    check_requirements()

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


if __name__ == "__main__":
    main()
