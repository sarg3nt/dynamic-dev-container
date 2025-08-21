"""Project configuration screen for the Dynamic Dev Container installer.

This module contains the ProjectConfigScreen class which handles
project-level configuration settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

try:
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import Button, Footer, Header, Input, Label
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    import sys

    sys.exit(1)

from installer.screens.basic import WelcomeScreen
from installer.utils import logger

from .mixins import DebugMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Key

    from installer.app import DynamicDevContainerApp
    from installer.config import ProjectConfig


class ProjectConfigScreen(Screen[None], DebugMixin):
    """Screen for project configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug", show=True),
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
        default_container = f"{default_name}-dev"

        # Generate docker exec command from display name
        words = default_display.split()
        default_exec = "".join(word[0].lower() for word in words if word) if words else "mp"  # fallback

        yield Header()
        yield Container(
            ScrollableContainer(
                Label("Project Configuration", classes="title"),
                Label(
                    "Enter your project configuration details:\\n[dim]Configuration that will be injected into the 'devcontainer.json' and 'dev.sh' files.[/dim]",
                ),
                Horizontal(
                    # Left column
                    Container(
                        Label(
                            "Project Path:\\n[dim]Path to the project source which is usually includes the git repository name.[/dim]",
                        ),
                        Input(value=self.config.project_path or str(Path.home() / default_name), id="project_path"),
                        Label("Project Name:\\n[dim]Name of the project, usually the git repository name.[/dim]"),
                        Input(value=default_name, id="project_name"),
                        Label("Display Name:\\n[dim]Pretty printed project name with spaces and capitalization.[/dim]"),
                        Input(value=default_display, id="display_name"),
                        classes="config-column",
                    ),
                    # Right column
                    Container(
                        Label(
                            "Container Name:\\n[dim]Dev Container name, typically the git repository name plus '-dev'[/dim]",
                        ),
                        Input(value=default_container, id="container_name"),
                        Label(
                            "Docker Exec Command:\\n[dim]Optional command to be injected into users shell init file to exec into running container.[/dim]",
                        ),
                        Input(value=default_exec, id="docker_command"),
                        classes="config-column",
                    ),
                    id="config-columns",
                ),
            ),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="project-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the project config screen when mounted."""
        logger.debug("ProjectConfigScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus to the first input field
        try:
            self.query_one("#project_path", Input).focus()
        except Exception:
            logger.debug("Could not set focus to project_path input")

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
        self.save_config()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to previous screen."""
        # Go back to welcome screen
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

    def key_ctrl_d(self, event: Key) -> None:
        """Handle Ctrl+D key even when Input widgets have focus."""
        event.stop()  # Stop event propagation to prevent Input handling
        self.action_toggle_debug()

    def save_config(self) -> None:
        """Save current configuration."""
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
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_project_config)
        self.app.pop_screen()
