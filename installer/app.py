"""Main application class for the Dynamic Dev Container installer.

This module contains the DynamicDevContainerApp class which coordinates
the TUI screens and manages the overall application flow.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from .config import ProjectConfig
from .screens import (
    InstallationScreen,
    ProjectConfigScreen,
    PSIHeaderScreen,
    SummaryScreen,
    ToolSelectionScreen,
    ToolVersionScreen,
    WelcomeScreen,
)
from .tools import MiseParser, ToolManager
from .utils import DEBUG_MODE, DEFAULT_WORKER_COUNT, logger


class DynamicDevContainerApp(App[None]):
    """Main application class for the Dynamic Dev Container installer.

    This class manages the overall TUI application flow, coordinating between
    different screens for configuration, tool selection, and installation.
    """

    CSS_PATH = "install.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

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

        # Start background loading of tool descriptions
        self._start_background_description_loading()

        logger.debug("DynamicDevContainerApp initialized successfully")

    def _start_background_description_loading(self) -> None:
        """Start background loading of tool descriptions for all available tools."""
        all_tools = set()

        # Collect all tools from all sections
        for section in self.sections:
            tools_in_section = MiseParser.get_section_tools(self.source_dir / ".mise.toml", section)
            all_tools.update(tools_in_section)

        # Convert to sorted list for consistent ordering
        tool_list = sorted(all_tools)

        if DEBUG_MODE:
            logger.debug("Starting background loading for %d tools: %s", len(tool_list), ", ".join(tool_list))

        # Start the background loading with parallel processing
        ToolManager.start_background_loading(tool_list, max_workers=DEFAULT_WORKER_COUNT)

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
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
        logger.debug("App after_tool_selection: config.tool_selected = %s", self.config.tool_selected)
        logger.debug("App after_tool_selection: Config object ID: %s", id(self.config))

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
        """Check if tool version configuration is needed and navigate accordingly.

        Examines the selected tools to determine if any have configurable versions.
        If configurable tools are found, shows the ToolVersionScreen. Otherwise,
        proceeds directly to PSI header configuration.
        """
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
        logger.debug("App: About to show PSI Header screen with config.tool_selected: %s", self.config.tool_selected)
        logger.debug("App: Config object ID: %s", id(self.config))
        self.push_screen(PSIHeaderScreen(self.config, self.source_dir), self.after_psi_header)

    def after_psi_header(self, _result: None = None) -> None:
        """Called after PSI Header configuration."""
        # Now show summary

        self.push_screen(SummaryScreen(self.config), self.after_summary)

    def after_summary(self, _result: None = None) -> None:
        """Called after summary screen."""

        self.push_screen(InstallationScreen(self.config, self.source_dir))

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
