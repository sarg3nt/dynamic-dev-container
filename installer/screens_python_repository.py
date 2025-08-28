"""Python repository screen for the Dynamic Dev Container installer.

This module contains the PythonRepositoryScreen class which handles Python
repository and project configuration settings.
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


class PythonRepositoryScreen(Screen[None]):
    """Screen for configuring Python repository settings."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
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

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Set focus to the first input field
        try:
            self.query_one("#project_name", Input).focus()
        except Exception:
            logger.debug("Could not set focus to project_name input")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle repository type selection.

        Ensures only one repository type can be selected at a time and updates
        the URL fields based on the selected repository type.

        Parameters
        ----------
        event : Checkbox.Changed
            The checkbox change event containing checkbox information

        """
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

        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_python_repository)
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
