"""Python project screen for the Dynamic Dev Container installer.

This module contains the PythonProjectScreen class which handles Python
project metadata configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label

from installer.logging_utils import get_logger

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from installer.config import ProjectConfig
    from installer.protocols import DevContainerApp

# Initialize logger for this module
logger = get_logger(__name__)


class PythonProjectScreen(Screen[None]):
    """Screen for Python project metadata configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
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

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Set focus to the first input field
        try:
            self.query_one("#python_project_name", Input).focus()
        except Exception:
            logger.debug("Could not set focus to python_project_name input")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle license selection.

        Ensures only one license type can be selected at a time by deselecting
        other license checkboxes when one is selected.

        Parameters
        ----------
        event : Checkbox.Changed
            The checkbox change event containing checkbox information

        """
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

        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_python_project)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Continue to the next screen.

        Saves the current configuration and proceeds to the next step in the workflow.

        """
        self.save_config()

    def action_quit(self) -> None:
        """Quit the application.

        Exits the Textual application cleanly, terminating the TUI session.

        """
        self.app.exit()

    def action_back(self) -> None:
        """Return to the previous screen.

        Navigates back to the previous step in the configuration workflow.

        """
        self.app.pop_screen()
