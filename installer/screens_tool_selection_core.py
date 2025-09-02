"""Tool selection screen core UI functionality for the Dynamic Dev Container installer.

This module contains the core UI components of the ToolSelectionScreen class,
including screen composition, loading management, and tools display refresh logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from textual import log as logger
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Button, Checkbox, Header, Label, LoadingIndicator, Static

from installer.constants import DEBUG_MODE
from installer.mise_parser import MiseParser
from installer.screens_navigation import NavigationScreenBase
from installer.tool_manager import ToolManager

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.timer import Timer
    from textual.widget import Widget

    from installer.config import ProjectConfig


class ToolSelectionScreenCore(NavigationScreenBase):
    """Core UI functionality for the Tool Selection screen."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
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

        # Initialize base class properties
        self.section_names = sections
        self.current_section = 0
        self.total_sections = len(sections)
        self.current_section = 0
        self.show_python_config = False
        self.show_other_config: dict[str, Any] = {}  # Track which tools are being configured
        self._refreshing_config = False  # Flag to prevent concurrent refresh calls
        self._widget_generation = 0  # Track widget generation to prevent ID conflicts
        self._active_version_inputs: set[str] = set()  # Track currently active version input IDs
        self._username_propagated = False  # Track if username has been propagated already
        self._last_focused_input: str = ""  # Track the last focused input for focus loss detection
        self._loading_timer: Timer | None = None  # Store reference to loading check timer

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        if not self.sections:
            yield Container(
                Label("No tool sections found in .mise.toml", classes="title"),
                Horizontal(
                    Button("<< Project Description", id="back_btn", classes="nav-button"),
                    Button("Dev Container Extensions >>", id="next_btn", classes="nav-button"),
                    id="button-row",
                ),
                id="tools-container",
            )
        else:
            # Check if current section has multiple tools for Select All button
            current_section = self.sections[self.current_section]
            tools_in_section = MiseParser.get_section_tools(Path(".mise.toml"), current_section)
            show_select_all = len(tools_in_section) > 1

            # Create tools header widgets
            tools_header_widgets: list[Widget] = [Label("Available Tools:", classes="column-title")]

            # Only add Select All button if there are multiple tools
            if show_select_all:
                tools_header_widgets.append(Button("Select All", id="select_all_tools", classes="version-btn-small"))

            # Main content area
            main_content = Container(
                Label(
                    f"Development Tools - {self.sections[self.current_section]} - Section {self.current_section + 1} of {len(self.sections)}",
                    classes="title",
                ),
                Horizontal(
                    # Left column for tool selection
                    Container(
                        Horizontal(
                            *tools_header_widgets,
                            id="tools-header",
                        ),
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
                # Section navigation links - use base class method
                self.create_navigation_links_container("section-links", populate_immediately=True),
                Horizontal(
                    Button("<< Project Description", id="back_btn", classes="nav-button"),
                    Button("Previous Tool", id="prev_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Tool",
                        id="next_section_btn",
                        disabled=self.current_section >= len(self.sections) - 1,
                    ),
                    Button("Dev Container Extensions >>", id="next_btn", classes="nav-button"),
                    id="button-row",
                ),
                id="main-content",
            )

            # Use base class method for layout creation
            yield from self.create_navigation_layout(main_content, "tools-container")

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        logger.debug("ToolSelectionScreen mounted - Debug functionality available (Ctrl+D)")

        # Check if background loading is complete
        if not ToolManager.is_loading_complete():
            self.__show_loading_screen()
        else:
            self.__show_tools_screen()

    def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        if self._loading_timer is not None:
            self._loading_timer.stop()
            self._loading_timer = None

    def refresh_tools(self) -> None:
        """Refresh the tools display for current section.

        Updates the tools list display to show the tools available in the
        currently selected section, handling UI rebuilding as needed.

        """
        if not self.sections:
            return

        tools_container = self.query_one("#tools-scroll", ScrollableContainer)

        # Only remove children if we need to rebuild (avoid duplicate IDs)
        needs_rebuild = True
        current_section = self.sections[self.current_section]
        tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

        # Update Select All button visibility based on tool count
        self.__update_select_all_button_visibility(tools)

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
            self.__add_python_repository_checkbox(tools_container)

        # Update configuration panel
        self.refresh_configuration()

        # Set focus to first tool if we rebuilt the tools
        if needs_rebuild and tools:
            self.__set_focus_to_first_tool()

    def refresh_configuration(self) -> None:
        """Refresh the configuration panel based on selected tools.

        This method should be implemented by a configuration management mixin.
        """
        # Placeholder - this will be implemented in a configuration mixin
        # Configuration logic will be added in another module

    def __add_python_repository_checkbox(self, tools_container: ScrollableContainer) -> None:
        """Add Python repository configuration checkbox if needed."""
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

    def __check_loading_complete(self) -> None:
        """Check if loading is complete and update display.

        Called periodically by a timer to check if background loading has completed.
        Updates the progress display or transitions to the tools screen when done.

        """
        if ToolManager.is_loading_complete():
            # Loading complete, show the tools
            self.__show_tools_screen()
            # Stop the checking timer
            if self._loading_timer is not None:
                self._loading_timer.stop()
                self._loading_timer = None
        else:
            # Update progress
            completed, total = ToolManager.get_loading_progress()
            loading_text = f"Loading tool descriptions... ({completed}/{total})"

            try:
                loading_text_widget = self.query_one("#loading-text", Static)
                loading_text_widget.update(loading_text)
            except Exception as e:
                # Widget might not exist anymore, ignore
                if DEBUG_MODE:
                    logger.debug("Failed to update loading text widget: %s", e)

    def __set_focus_to_first_tool(self) -> None:
        """Set focus to the first tool checkbox."""
        try:
            # Get the current section's tools
            if self.sections and self.current_section < len(self.sections):
                current_section = self.sections[self.current_section]
                tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)
                if tools:
                    first_tool = tools[0]
                    first_checkbox = self.query_one(f"#tool_{first_tool}", Checkbox)
                    first_checkbox.focus()
        except Exception:
            logger.debug("Could not set focus to first tool checkbox")

    def __show_loading_screen(self) -> None:
        """Show loading screen while background description loading completes.

        Displays a loading indicator and progress text while tool descriptions
        are being loaded in the background. Sets up a timer to check for completion.

        """
        # Clear existing content
        tools_container = self.query_one("#tools-scroll", ScrollableContainer)
        tools_container.remove_children()

        # Show loading indicator
        completed, total = ToolManager.get_loading_progress()
        loading_text = f"Loading tool descriptions... ({completed}/{total})"

        tools_container.mount(
            Static(loading_text, id="loading-text"),
            LoadingIndicator(id="loading-spinner"),
        )

        # Set up a timer to check for completion
        self._loading_timer = self.set_interval(0.5, self.__check_loading_complete)

        if DEBUG_MODE:
            logger.debug("Showing loading screen for tool descriptions")

    def __show_tools_screen(self) -> None:
        """Show the actual tools screen after loading is complete.

        Transitions from the loading screen to the main tools selection interface.
        Refreshes the tools display and sets up periodic debug output updates.

        """
        self.refresh_tools()
        # Initialize section navigation links
        self.refresh_navigation_links("section-links", "section_link", "Tools")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus to the first tool checkbox
        self.__set_focus_to_first_tool()

    def __update_select_all_button_visibility(self, tools: list[str]) -> None:
        """Update Select All button visibility based on tool count."""
        try:
            tools_header = self.query_one("#tools-header", Horizontal)
            current_widgets = list(tools_header.children)

            # Check if Select All button currently exists
            has_select_all_btn = any(
                hasattr(widget, "id") and widget.id == "select_all_tools" for widget in current_widgets
            )

            should_have_select_all = len(tools) > 1
            current_section = self.sections[self.current_section]

            logger.debug(
                "SELECT ALL DEBUG: section=%s, tools_count=%d, should_have=%s, has_current=%s",
                current_section,
                len(tools),
                should_have_select_all,
                has_select_all_btn,
            )
            logger.debug("SELECT ALL DEBUG: tools in section: %s", tools)

            if should_have_select_all and not has_select_all_btn:
                # Need to add Select All button
                select_all_btn = Button("Select All", id="select_all_tools", classes="version-btn-small")
                tools_header.mount(select_all_btn)
                logger.debug("Added Select All button for section %s with %d tools", current_section, len(tools))
            elif not should_have_select_all and has_select_all_btn:
                # Need to remove Select All button
                try:
                    select_all_btn = self.query_one("#select_all_tools", Button)
                    select_all_btn.remove()
                    logger.debug("Removed Select All button for section %s", current_section)
                except Exception as e:
                    logger.debug("Could not remove Select All button: %s", e)
            elif should_have_select_all and has_select_all_btn:
                logger.debug("Select All button already exists for section %s", current_section)
            else:
                logger.debug("No Select All button needed for section %s", current_section)

        except Exception as e:
            logger.debug("Could not update Select All button: %s", e)
