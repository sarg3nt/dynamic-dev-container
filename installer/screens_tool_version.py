"""Tool version configuration screen for the Dynamic Dev Container installer.

This module contains the ToolVersionScreen class, which provides a user interface
for configuring specific versions of selected development tools. The screen
handles version input validation and saves configurations for tools that
support version specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual import log as logger
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label

from installer.debug_utils import DebugMixin
from installer.tool_manager import ToolManager

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from installer.config import ProjectConfig
    from installer.protocols import DevContainerApp


class ToolVersionScreen(Screen[None], DebugMixin):
    """Screen for configuring specific tool versions."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
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
        logger.debug("ToolVersionScreen mounted - Debug functionality available (Ctrl+D)")

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

        # Set focus to the first version input if any tools are configurable
        if self.configurable_tools:
            try:
                first_tool = self.configurable_tools[0]
                first_input = self.query_one(f"#version_{first_tool}", Input)
                first_input.focus()
            except Exception:
                logger.debug("Could not set focus to first version input")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()

    def save_config(self) -> None:
        """Save current configuration."""
        for tool in self.configurable_tools:
            version_input = self.query_one(f"#version_{tool}", Input)
            version = version_input.value.strip() or "latest"
            self.config.tool_version_value[tool] = version

        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_tool_versions)
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
