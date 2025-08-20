"""Screen classes for the Dynamic Dev Container installer TUI.

This module contains the essential screen classes that make up the user interface
for the Dynamic Dev Container installer.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

# Check if required dependencies are available first
try:
    import pyperclip
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.css.query import NoMatches
    from textual.screen import Screen
    from textual.widgets import (
        Button,
        Checkbox,
        Footer,
        Header,
        Input,
        Label,
        Markdown,
        RichLog,
    )
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    import sys

    sys.exit(1)

# Import our modules
from .tools import DevContainerParser, MiseParser, ToolManager
from .utils import DEBUG_MODE, MAX_DEBUG_MESSAGES, logger, tui_log_handler

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Focus, Key

    from .app import DynamicDevContainerApp
    from .config import ProjectConfig


class DebugMixin:
    """Mixin class to add debug functionality to screens.

    This mixin should be used with classes that inherit from Screen.
    """

    def get_debug_widget(self) -> Container:
        """Create a debug output widget for the screen.

        Returns
        -------
        Container
            A container widget with debug log display

        """
        debug_log = RichLog(
            max_lines=50,
            wrap=True,
            highlight=True,
            markup=True,
            id="debug_log",
        )

        # Populate with existing debug messages immediately
        self._populate_debug_log(debug_log)

        return Container(
            Label("Debug Output:", classes="debug-title"),
            debug_log,
            id="debug_container",
            classes="debug-panel",
        )

    def _populate_debug_log(self, debug_log: RichLog) -> None:
        """Populate debug log with current messages.

        Parameters
        ----------
        debug_log : RichLog
            The RichLog widget to populate with debug messages

        """
        messages = tui_log_handler.get_messages()

        if not messages:
            debug_log.write("[dim]No debug messages available yet. Perform some operations to see debug output.[/dim]")
        else:
            # Show recent messages (last MAX_DEBUG_MESSAGES or all if fewer)
            recent_messages = messages[-MAX_DEBUG_MESSAGES:] if len(messages) > MAX_DEBUG_MESSAGES else messages
            for msg in recent_messages:
                # Ensure message is properly formatted for display
                try:
                    debug_log.write(msg)
                except Exception as e:
                    # If there's an issue with the message, show a safe version
                    debug_log.write(f"[red]Error displaying message: {e}[/red]")

    def update_debug_output(self) -> None:
        """Update the debug output with new messages.

        Refreshes the debug log widget with the latest captured log messages.
        """
        try:
            # Use cast to tell mypy this mixin is used with Screen classes
            screen = cast("Screen[None]", self)
            debug_log = screen.query_one("#debug_log", RichLog)

            # Clear and repopulate to ensure fresh content
            debug_log.clear()
            self._populate_debug_log(debug_log)

            # Force a refresh to ensure content is displayed
            debug_log.refresh()

        except NoMatches:
            # Debug widget not found - this is normal when debug panel isn't shown
            pass
        except Exception as e:
            # Log any other errors for debugging
            logger.debug("Failed to update debug output: %s", e)

    def _copy_debug_output(self) -> None:
        """Standard debug copy functionality for all screens.

        Copies all captured debug messages to the system clipboard and
        displays a notification to the user.
        """
        try:
            messages = tui_log_handler.get_messages()
            debug_text = "\n".join(messages)
            pyperclip.copy(debug_text)
            screen = cast("Screen[None]", self)
            screen.notify("Debug output copied to clipboard!", timeout=2, severity="information")
        except Exception as e:
            screen = cast("Screen[None]", self)
            screen.notify(f"Failed to copy debug output: {e}", timeout=3, severity="error")

    def _rebuild_with_debug_panel(self) -> None:
        """Standard debug panel creation for all screens.

        Attempts to add a debug panel to the current screen by finding
        the main container and mounting a debug widget.
        """
        try:
            # Try to find a main container with common IDs
            main_container = None
            container_ids = [
                "#welcome-container",
                "#project-container",
                "#summary-container",
                "#install-container",
                "#tools-container",
                "#main-content",
                "#psi-container",
            ]

            for container_id in container_ids:
                try:
                    screen = cast("Screen[None]", self)
                    main_container = screen.query_one(container_id)
                    break
                except NoMatches:
                    continue

            if not main_container:
                logger.debug("DebugMixin: Could not find any main container for debug panel")
                return

            # Remove any existing debug container first
            try:
                screen = cast("Screen[None]", self)
                existing_debug = screen.query_one("#debug_container")
                existing_debug.remove()
                logger.debug("DebugMixin: Removed existing debug container")
            except NoMatches:
                pass  # No existing debug container, which is fine

            # Create the standardized debug panel
            debug_log = RichLog(
                max_lines=50,
                wrap=True,
                highlight=True,
                markup=True,
                id="debug_log",
            )

            # Populate immediately with current messages
            self._populate_debug_log(debug_log)

            debug_container = Container(
                Horizontal(
                    Label("Debug Output (Ctrl+D to toggle):", classes="debug-title"),
                    Button("Copy Debug", id="copy_debug_btn", classes="debug-copy-btn"),
                    id="debug-header",
                ),
                debug_log,
                id="debug_container",
                classes="debug-panel",
            )

            # Mount the debug container
            main_container.mount(debug_container)
            logger.debug("DebugMixin: Successfully added debug panel to screen")

        except Exception as e:
            logger.debug("DebugMixin: Failed to create debug panel: %s", e)


class WelcomeScreen(Screen[None], DebugMixin):
    """Welcome screen for the installer."""

    BINDINGS = [
        Binding("enter", "continue", "Continue"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Markdown(f"""
# Dynamic Dev Container Setup

Welcome to the **Dynamic Dev Container TUI Setup**!

This wizard will guide you through configuring your development container with the tools and extensions you need.

## System Status:
- Debug Mode: {"✅ Enabled" if DEBUG_MODE else "❌ Disabled"}

## Getting Started:
- Press **ENTER** to start the configuration wizard
- Press **Ctrl+Q** to quit the application
- Press **Ctrl+D** to view debug output

## Navigation Tips:
- Use **TAB** and **SHIFT+TAB** to move between elements
- Use **SPACE** or **ENTER** to select/deselect checkboxes
- Use **ENTER** to activate buttons and continue
- Use **ESCAPE** to go back to previous screens
- Most screens show available key bindings in the footer

## What This Wizard Will Configure:
- 🛠️  **Development tools** and their versions (Python, Go, Node.js, etc.)
- 🧩 **VS Code extensions** for your selected languages
- 🐳 **Container environment** and settings
- 🐍 **Python project structure** (optional)
- 📝 **File header templates** (optional)

## Features:
- ⚡ **Dynamic tool discovery using Mise** - automatically finds latest versions and allows users to set versions easily.
- 🎯 **Smart defaults** - pre-selects common tool combinations
- 📋 **Full customization** - override any setting

---

**Ready to create your perfect dev environment?**

Press **ENTER** to begin the setup wizard...
            """),
            id="welcome-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted.

        Sets up debug logging and periodic debug output updates for the welcome screen.
        """
        logger.debug("WelcomeScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def action_continue(self) -> None:
        """Continue to the next screen.

        Triggers the transition to the project configuration screen.
        """
        # Call the next step directly
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_welcome)
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "copy_debug_btn":
            self._copy_debug_output()


# Create placeholder classes for screens that will be extracted later
# These provide basic functionality while we complete the refactoring
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
                    "Enter your project configuration details:\n[dim]Configuration that will be injected into the 'devcontainer.json' and 'dev.sh' files.[/dim]",
                ),
                Horizontal(
                    # Left column
                    Container(
                        Label(
                            "Project Path:\n[dim]Path to the project source which is usually includes the git repository name.[/dim]",
                        ),
                        Input(value=self.config.project_path or str(Path.home() / default_name), id="project_path"),
                        Label("Project Name:\n[dim]Name of the project, usually the git repository name.[/dim]"),
                        Input(value=default_name, id="project_name"),
                        Label("Display Name:\n[dim]Pretty printed project name with spaces and capitalization.[/dim]"),
                        Input(value=default_display, id="display_name"),
                        classes="config-column",
                    ),
                    # Right column
                    Container(
                        Label(
                            "Container Name:\n[dim]Dev Container name, typically the git repository name plus '-dev'[/dim]",
                        ),
                        Input(value=default_container, id="container_name"),
                        Label(
                            "Docker Exec Command:\n[dim]Optional command to be injected into users shell init file to exec into running container.[/dim]",
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
        """Called when the screen is mounted."""
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


class ToolSelectionScreen(Screen[None], DebugMixin):
    """Screen for selecting development tools."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug", show=True),
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
        self.sections = sections or ["tools"]  # Provide default if empty
        self.tool_selected = tool_selected
        self.tool_version_configurable = tool_version_configurable
        self.tool_version_value = tool_version_value
        self.current_section = 0
        self._updating_checkboxes = False  # Flag to prevent recursive updates
        self._refreshing_config = False  # Flag to prevent overlapping refresh calls
        self._widget_counter = 0  # Counter to make widget IDs unique
        self._username_propagated = False  # Flag to track if username propagation has occurred
        self._last_focused_input: str | None = None  # Track last focused input for focus loss detection

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        if not self.sections:
            yield Container(
                Label("No tool sections found in .mise.toml", classes="title"),
                Label("Using default tools..."),
                Horizontal(
                    Button("Back", id="back_btn"),
                    Button("Next", id="next_btn", variant="primary"),
                    id="button-row",
                ),
                id="tools-container",
            )
        else:
            # Create main layout container
            yield Container(
                Label(
                    f"Development Tools - {self.sections[self.current_section]} - Section {self.current_section + 1} of {len(self.sections)}",
                    classes="title",
                ),
                Horizontal(
                    # Left column for tool selection
                    Container(
                        Horizontal(
                            Label("Available Tools:", classes="column-title"),
                            Button("Select All", id="select_all_tools", classes="version-btn-small"),
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
                # Section navigation and buttons
                Horizontal(
                    Button("Back", id="back_btn"),
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
        logger.debug("ToolSelectionScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Initialize the tools display
        self.refresh_tools()

    def refresh_tools(self) -> None:
        """Refresh the tools display for current section."""
        if not self.sections:
            return

        try:
            tools_container = self.query_one("#tools-scroll", ScrollableContainer)
            tools_container.remove_children()

            current_section = self.sections[self.current_section]
            tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            # Update Select All button visibility
            try:
                select_all_btn = self.query_one("#select_all_tools", Button)
                # Show button only if there are multiple tools
                if len(tools) > 1:
                    select_all_btn.display = True
                    select_all_btn.can_focus = False  # Make it not focusable via tab
                else:
                    select_all_btn.display = False
            except Exception as e:
                # Button might not exist yet during initialization
                logger.debug("Could not update select all button visibility: %s", e)

            if not tools:
                tools_container.mount(Label("No tools found in this section", classes="compact"))
                return

            # Add checkboxes for each tool
            for tool in tools:
                description = ToolManager.get_tool_description(tool)
                checkbox = Checkbox(description, id=f"tool_{tool}", classes="compact")
                checkbox.value = self.tool_selected.get(tool, False)
                tools_container.mount(checkbox)

            # Handle Python repository configuration if Python is available
            if "python" in tools:
                # Add pyproject.toml configuration checkbox
                python_selected = self.tool_selected.get("python", False)
                repo_checkbox = Checkbox(
                    "Configure pyproject.toml",
                    id="py_repo_enabled",
                    value=self.config.install_python_repository and python_selected,
                    disabled=not python_selected,
                    classes="compact repo-checkbox",
                )
                tools_container.mount(repo_checkbox)

            # Update configuration panel
            self.refresh_configuration()

        except Exception as e:
            logger.debug("Error refreshing tools: %s", e)

    def refresh_configuration(self) -> None:
        """Refresh the configuration panel based on selected tools."""
        # Prevent overlapping calls
        if self._refreshing_config:
            logger.debug("Skipping refresh_configuration - already refreshing")
            return

        # Check if we're in the middle of updating to prevent recursion
        if self._updating_checkboxes:
            logger.debug("Skipping refresh_configuration due to _updating_checkboxes")
            return

        self._refreshing_config = True
        self._widget_counter += 1  # Increment counter for unique IDs

        try:
            config_container = self.query_one("#config-scroll", ScrollableContainer)

            # Clear all children
            config_container.remove_children()

            # Check which tools are selected
            if not self.sections:
                config_container.mount(Label("No tools available", classes="compact"))
                return

            current_section = self.sections[self.current_section]
            tools_in_current_section = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            # Debug logging
            logger.debug("Current section: %s", current_section)
            logger.debug("Tools in current section: %s", tools_in_current_section)
            logger.debug("Tool selected dict: %s", self.tool_selected)
            logger.debug("Python selected: %s", self.tool_selected.get("python", False))

            # Only show tools that are BOTH selected AND in the current section
            selected_tools_in_section = [
                tool for tool in tools_in_current_section if self.tool_selected.get(tool, False)
            ]

            logger.debug("Selected tools in section: %s", selected_tools_in_section)

            if not selected_tools_in_section:
                config_container.mount(Label("Select tools to see configuration options", classes="compact"))
                return  # Show Python configuration first if Python is selected
            if "python" in selected_tools_in_section:
                config_container.mount(Label("Python Version:", classes="compact section-header"))
                python_version = self.tool_version_value.get("python", "latest")

                # Create a horizontal container for Python version
                python_version_container = Horizontal(classes="tool-version-row")
                config_container.mount(python_version_container)

                # Tool name label
                python_version_container.mount(Label("python:", classes="compact tool-label"))

                # Version buttons for Python
                self._create_version_buttons("python", python_version_container, 4)

                # Version input field
                config_container.mount(
                    Input(
                        value=python_version,
                        placeholder="version or 'latest'",
                        id=f"version_python_{self._widget_counter}",
                        classes="version-input",
                    ),
                )

                # Add pyproject.toml configuration if enabled
                if self.config.install_python_repository:
                    config_container.mount(Label("PyProject.toml Configuration:", classes="compact section-header"))

                    # Project metadata section
                    config_container.mount(Label("Project Metadata:", classes="compact subsection-header"))

                    # Project name
                    config_container.mount(Label("Package Name:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_project_name or "my-awesome-project",
                            placeholder="Enter package name (lowercase, no spaces)",
                            id=f"pyproject_name_{self._widget_counter}",
                            classes="compact-input",
                        ),
                    )

                    # Project description
                    config_container.mount(Label("Description:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_project_description or "A brief description of your project",
                            placeholder="Enter project description",
                            id=f"pyproject_description_{self._widget_counter}",
                            classes="compact-input",
                        ),
                    )

                    # Required Python version
                    config_container.mount(Label("Required Python Version:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_requires_python or ">=3.12",
                            placeholder="e.g., >=3.12",
                            id=f"pyproject_requires_python_{self._widget_counter}",
                            classes="compact-input",
                        ),
                    )

                    # Author name
                    config_container.mount(Label("Author Name:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_author_name or "Your Name",
                            placeholder="Enter author name",
                            id=f"pyproject_author_name_{self._widget_counter}",
                            classes="compact-input",
                        ),
                    )

                    # Author email
                    config_container.mount(Label("Author Email:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_author_email or "your.email@example.com",
                            placeholder="Enter author email",
                            id="pyproject_author_email",
                            classes="compact-input",
                        ),
                    )

                    # Project URLs section
                    config_container.mount(Label("Project URLs:", classes="compact subsection-header"))

                    # Homepage URL
                    config_container.mount(Label("Homepage URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_homepage_url or self._get_default_homepage_url(),
                            placeholder="Enter homepage URL",
                            id="pyproject_homepage",
                            classes="compact-input",
                        ),
                    )

                    # Source URL
                    config_container.mount(Label("Source URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_source_url or self._get_default_source_url(),
                            placeholder="Enter source repository URL",
                            id="pyproject_source",
                            classes="compact-input",
                        ),
                    )

                    # Documentation URL
                    config_container.mount(Label("Documentation URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_documentation_url or self._get_default_documentation_url(),
                            placeholder="Enter documentation URL",
                            id="pyproject_documentation",
                            classes="compact-input",
                        ),
                    )

                    # Build configuration section
                    config_container.mount(Label("Build Configuration:", classes="compact subsection-header"))

                    # Package path
                    config_container.mount(Label("Package Path:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_packages_path or self._get_default_package_path(),
                            placeholder="Enter package path (e.g., src/package_name)",
                            id="pyproject_packages",
                            classes="compact-input",
                        ),
                    )

                    # Repository publishing section
                    config_container.mount(Label("Repository Publishing:", classes="compact subsection-header"))

                    # Package Index URL
                    config_container.mount(Label("Package Index URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_index_url or "https://pypi.org/simple/",
                            placeholder="Package index URL",
                            id="pyproject_index_url",
                            classes="compact-input",
                        ),
                    )

                    # Publishing URL
                    config_container.mount(Label("Publishing URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_publish_url or "https://upload.pypi.org/legacy/",
                            placeholder="Publishing URL",
                            id="pyproject_publish_url",
                            classes="compact-input",
                        ),
                    )  # Show other tool configurations
            configurable_tools_in_current_section = [
                tool
                for tool in selected_tools_in_section
                if self.tool_version_configurable.get(tool, False) and tool != "python"
            ]

            if configurable_tools_in_current_section:
                config_container.mount(Label("Tool Versions:", classes="compact section-header"))
                for tool in configurable_tools_in_current_section:
                    current_version = self.tool_version_value.get(tool, "latest")

                    # Create a horizontal container for tool name and version buttons
                    tool_version_container = Horizontal(classes="tool-version-row")
                    config_container.mount(tool_version_container)

                    # Tool name label
                    tool_version_container.mount(Label(f"{tool}:", classes="compact tool-label"))

                    # Version buttons
                    self._create_version_buttons(tool, tool_version_container)

                    # Version input field - use unique ID to avoid conflicts
                    config_container.mount(
                        Input(
                            value=current_version,
                            placeholder="version or 'latest'",
                            id=f"version_{tool}_{self._widget_counter}",
                            classes="version-input",
                        ),
                    )

        except Exception as e:
            logger.debug("Error refreshing configuration: %s", e)
        finally:
            self._refreshing_config = False

    def _create_version_buttons(
        self,
        tool: str,
        parent_container: Horizontal,
        version_limit: int | None = None,
    ) -> None:
        """Create version buttons for a tool.

        Parameters
        ----------
        tool : str
            The tool name
        parent_container : Horizontal
            The container to mount the buttons to
        version_limit : int | None
            Maximum number of versions to show, None for all

        """
        try:
            versions = ToolManager.get_version_list(tool)
            if version_limit:
                versions = versions[:version_limit]

            for version in versions:
                # Replace dots with underscores for valid CSS identifiers
                safe_version = version.replace(".", "_")
                version_btn = Button(
                    version,
                    id=f"version_btn_{tool}_{safe_version}",
                    classes="version-btn-small",
                )
                version_btn.can_focus = False  # Make version buttons not focusable via tab
                parent_container.mount(version_btn)
        except Exception as e:
            logger.debug("Error creating version buttons for %s: %s", tool, e)

    def _get_default_homepage_url(self) -> str:
        """Get default homepage URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def _get_default_source_url(self) -> str:
        """Get default source URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def _get_default_documentation_url(self) -> str:
        """Get default documentation URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}/README.md"
        return "https://github.com/yourusername/my-awesome-project/README.md"

    def _get_default_package_path(self) -> str:
        """Get default package path based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
            return f"src/{package_name_clean}"
        return "src/my_awesome_project"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.action_next()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "prev_btn":
            self.action_prev_section()
        elif event.button.id == "next_section_btn":
            self.action_next_section()
        elif event.button.id == "select_all_tools":
            self._select_all_tools()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()
        elif event.button.id and event.button.id.startswith("version_btn_"):
            # Handle version button clicks
            self._handle_version_button_click(event.button.id)

    def _handle_version_button_click(self, button_id: str) -> None:
        """Handle version button clicks.

        Parameters
        ----------
        button_id : str
            The ID of the clicked version button

        """
        try:
            # Parse button ID: version_btn_{tool}_{safe_version}
            parts = button_id.split("_", 3)  # Split into ['version', 'btn', tool, safe_version]
            min_parts_count = 4
            if len(parts) >= min_parts_count:
                tool = parts[2]
                safe_version = parts[3]
                # Convert safe version back to actual version
                version = safe_version.replace("_", ".")

                # Update the tool version value
                self.tool_version_value[tool] = version

                # Update the input field - need to find the current input field with dynamic ID
                try:
                    # For Python, look for version_python_* pattern using a different approach
                    if tool == "python":
                        # Find all Input widgets and filter by ID pattern
                        all_inputs = self.query(Input)
                        python_version_input = None
                        for input_widget in all_inputs:
                            if input_widget.id and input_widget.id.startswith("version_python_"):
                                python_version_input = input_widget
                                break

                        if python_version_input:
                            python_version_input.value = version
                        else:
                            logger.debug("Could not find any Python version input field")
                    else:
                        # For other tools, find the version input field with the current counter
                        all_inputs = self.query(Input)
                        tool_version_input = None
                        for input_widget in all_inputs:
                            if input_widget.id and input_widget.id.startswith(f"version_{tool}_"):
                                tool_version_input = input_widget
                                break

                        if tool_version_input:
                            tool_version_input.value = version
                        else:
                            logger.debug("Could not find version input field for tool: %s", tool)
                except Exception as e:
                    # Input field might not exist yet
                    logger.debug("Could not update input field for %s: %s", tool, e)

                logger.debug("Set %s version to %s", tool, version)
        except Exception as e:
            logger.debug("Error handling version button click: %s", e)

    def _select_all_tools(self) -> None:
        """Select all available tools in the current section."""
        try:
            if not self.sections:
                return

            current_section = self.sections[self.current_section]
            tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            if not tools:
                return

            # Set all tools as selected in the internal state
            for tool in tools:
                self.tool_selected[tool] = True

            # Update all tool checkboxes to checked state
            for tool in tools:
                checkbox_id = f"tool_{tool}"
                try:
                    checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                    checkbox.value = True
                except Exception as e:
                    logger.debug("Could not find checkbox for tool %s: %s", tool, e)

            # Update Python repository checkbox if Python is selected
            if "python" in tools:
                try:
                    repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
                    repo_checkbox.disabled = False  # Enable since Python is now selected
                    # Optionally auto-enable pyproject.toml configuration
                    repo_checkbox.value = True
                    self.config.install_python_repository = True
                except Exception as e:
                    logger.debug("Could not update Python repository checkbox: %s", e)

            # Refresh configuration panel to show settings for all selected tools
            self.refresh_configuration()

            logger.debug("Selected all tools in section %s: %s", current_section, tools)

        except Exception as e:
            logger.debug("Error selecting all tools: %s", e)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes."""
        input_id = event.input.id
        if input_id and input_id.startswith("version_"):
            # Extract tool name from input ID (handle both old and new format)
            if "_python_" in input_id:
                tool = "python"
            else:
                # Extract tool name for other tools - handle both formats:
                # version_{tool} (old format) or version_{tool}_{counter} (new format)
                parts = input_id.replace("version_", "").split("_")
                tool = parts[0]  # Take the first part as tool name

            new_value = event.value
            # Update the tool version value
            self.tool_version_value[tool] = new_value
            logger.debug("Updated %s version to %s via input", tool, new_value)
        elif input_id and input_id.startswith("pyproject_"):
            # Handle pyproject.toml configuration changes (strip counter suffix)
            base_id = input_id.split("_")[0] + "_" + input_id.split("_")[1]  # Get pyproject_fieldname
            self._handle_pyproject_input_change(base_id, event.value)

    def on_focus(self, event: Focus) -> None:
        """Handle focus events to track input focus changes."""
        # Track the currently focused input
        if event.control and hasattr(event.control, "id") and event.control.id:
            self._last_focused_input = event.control.id
            logger.debug("Input gained focus: %s", event.control.id)

    def on_descendant_focus(self, event: Focus) -> None:
        """Handle when focus moves to track focus loss from inputs."""
        # When focus moves from one input to another, process the previous input
        if hasattr(self, "_last_focused_input") and event.control and hasattr(event.control, "id"):
            previous_input_id = self._last_focused_input
            current_input_id = event.control.id if event.control.id else None

            # If focus moved from a tracked input to something else, process the previous input
            if previous_input_id and previous_input_id != current_input_id:
                self._process_input_on_focus_loss(previous_input_id)

            # Update tracked input
            if current_input_id:
                self._last_focused_input = current_input_id

    def _handle_pyproject_input_change(self, input_id: str, value: str) -> None:
        """Handle pyproject.toml input changes.

        Parameters
        ----------
        input_id : str
            The ID of the input field
        value : str
            The new value

        """
        if input_id == "pyproject_name":
            self.config.python_project_name = value
            # Update package name and related fields when package name changes
            logger.debug("Package name input changed to: %s", value)
            # Use call_later to ensure all widgets are mounted before updating
            self.call_later(self._update_package_related_fields, value)
        elif input_id == "pyproject_description":
            self.config.python_project_description = value
        elif input_id == "pyproject_requires_python":
            self.config.python_requires_python = value
        elif input_id == "pyproject_author_name":
            self.config.python_author_name = value
        elif input_id == "pyproject_author_email":
            self.config.python_author_email = value
        elif input_id == "pyproject_homepage":
            self.config.python_homepage_url = value
            # Handle Homepage URL changes - the username propagation will happen on focus loss
            logger.debug("Homepage URL input changed to: %s", value)
        elif input_id == "pyproject_source":
            self.config.python_source_url = value
        elif input_id == "pyproject_documentation":
            self.config.python_documentation_url = value
        elif input_id == "pyproject_packages":
            self.config.python_packages_path = value
        elif input_id == "pyproject_index_url":
            self.config.python_index_url = value
        elif input_id == "pyproject_publish_url":
            self.config.python_publish_url = value

        logger.debug("Updated pyproject field %s to %s", input_id, value)

    def _process_input_on_focus_loss(self, input_id: str) -> None:
        """Process specific inputs when they lose focus.

        Parameters
        ----------
        input_id : str
            The ID of the input that lost focus

        """
        try:
            # Check if this is a homepage URL field (with dynamic ID)
            if input_id and input_id.startswith("pyproject_homepage") and not self._username_propagated:
                # Process homepage URL immediately on focus loss
                homepage_inputs = self.query(Input)
                homepage_input = None
                for inp in homepage_inputs:
                    if inp.id and inp.id.startswith("pyproject_homepage"):
                        homepage_input = inp
                        break

                if homepage_input:
                    homepage_value = homepage_input.value.strip()
                    if homepage_value:
                        logger.debug("Processing homepage URL on focus loss: %s", homepage_value)
                        self._check_and_propagate_username(homepage_value)

        except Exception as e:
            logger.debug("Error processing input on focus loss (%s): %s", input_id, e)

    def _check_and_propagate_username(self, homepage_url: str) -> None:
        """Check if homepage URL contains a valid username and propagate it.

        Extracts username from a GitHub URL and automatically populates
        other URL fields (source, documentation) if they still contain
        template values.

        Parameters
        ----------
        homepage_url : str
            The homepage URL to analyze for username extraction

        """
        logger.debug("Checking homepage URL for username propagation: %s", homepage_url)

        # Only propagate if the URL looks complete (contains github.com and has a slash after username)
        if not homepage_url or "github.com/" not in homepage_url:
            logger.debug("URL not complete enough for propagation")
            return

        try:
            # Extract username from the homepage URL
            username = self._extract_username_from_url(homepage_url)
            if not username or username == "yourusername":
                # No valid username found or still using template
                logger.debug("No valid username found or still using template: %s", username)
                return

            # Check if the URL has a repo name too (should have at least two parts after github.com)
            url_match = re.search(r"github\.com/([^/]+)/(.+)", homepage_url)
            if not url_match:
                logger.debug("URL doesn't have repo name yet, waiting for complete URL")
                return

            logger.debug("Valid username found: %s, propagating to other fields", username)

            # Find other URL input fields (with dynamic IDs)
            all_inputs = self.query(Input)
            source_input = None
            documentation_input = None

            for inp in all_inputs:
                if inp.id and inp.id.startswith("pyproject_source"):
                    source_input = inp
                elif inp.id and inp.id.startswith("pyproject_documentation"):
                    documentation_input = inp

            # Update source URL if it still uses template username
            if source_input and "yourusername" in source_input.value:
                repo_name = url_match.group(2)
                new_source = f"https://github.com/{username}/{repo_name}"
                source_input.value = new_source
                self.config.python_source_url = new_source
                logger.debug("Updated source URL to: %s", new_source)

            # Update documentation URL
            if documentation_input and (
                not documentation_input.value.strip()
                or "yourusername" in documentation_input.value
                or documentation_input.value == self._get_default_documentation_url()
            ):
                repo_name = url_match.group(2)
                new_documentation = f"https://github.com/{username}/{repo_name}/README.md"
                documentation_input.value = new_documentation
                self.config.python_documentation_url = new_documentation
                logger.debug("Updated documentation URL to: %s", new_documentation)

            # Mark that username propagation has happened
            self._username_propagated = True
            logger.debug("Username propagation completed, future changes will not propagate")

        except Exception as e:
            logger.debug("Could not check/propagate username: %s", e)

    def _extract_username_from_url(self, url: str) -> str:
        """Extract username from a GitHub URL.

        Parameters
        ----------
        url : str
            The URL to extract username from

        Returns
        -------
        str
            The extracted username, or empty string if not found

        """
        if not url:
            return ""

        # Match GitHub URLs: https://github.com/username/repo
        github_match = re.search(r"github\.com/([^/]+)", url)
        if github_match:
            return github_match.group(1)

        return ""

    def _update_package_related_fields(self, package_name: str) -> None:
        """Update fields that depend on the package name.

        Parameters
        ----------
        package_name : str
            The new package name

        """
        # Always try to update, even for empty package names (to show defaults)
        logger.debug("Updating package-related fields for package name: %s", package_name)

        try:
            # Convert package name to valid formats
            if package_name and package_name.strip():
                package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
                package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            else:
                # Use defaults for empty package name
                package_name_clean = "my_awesome_project"
                package_name_url = "my-awesome-project"

            # Find input fields with dynamic IDs
            all_inputs = self.query(Input)
            homepage_input = None
            source_input = None
            documentation_input = None
            packages_input = None

            for inp in all_inputs:
                if inp.id and inp.id.startswith("pyproject_homepage"):
                    homepage_input = inp
                elif inp.id and inp.id.startswith("pyproject_source"):
                    source_input = inp
                elif inp.id and inp.id.startswith("pyproject_documentation"):
                    documentation_input = inp
                elif inp.id and inp.id.startswith("pyproject_packages"):
                    packages_input = inp

            # Update Homepage URL if it still has the default value
            if homepage_input:
                logger.debug("Current homepage URL: %s", homepage_input.value)

                # Update if it's empty, has the exact default, or looks like a generated URL
                should_update_homepage = (
                    not homepage_input.value
                    or homepage_input.value == "https://github.com/yourusername/my-awesome-project"
                    or "my-awesome-project" in homepage_input.value
                    or "yourusername" in homepage_input.value  # Also update if it has the template username
                    or homepage_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
                )

                if should_update_homepage:
                    new_url = f"https://github.com/yourusername/{package_name_url}"
                    homepage_input.value = new_url
                    self.config.python_homepage_url = new_url
                    logger.debug("Updated homepage URL to: %s", new_url)

            # Update Source URL if it still has the default value
            if source_input:
                logger.debug("Current source URL: %s", source_input.value)

                # Update if it's empty, has the exact default, or looks like a generated URL
                should_update_source = (
                    not source_input.value
                    or source_input.value == "https://github.com/yourusername/my-awesome-project"
                    or "my-awesome-project" in source_input.value
                    or "yourusername" in source_input.value  # Also update if it has the template username
                    or source_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
                )

                if should_update_source:
                    new_url = f"https://github.com/yourusername/{package_name_url}"
                    source_input.value = new_url
                    self.config.python_source_url = new_url
                    logger.debug("Updated source URL to: %s", new_url)

            # Update Documentation URL if it still has the default value
            if documentation_input:
                logger.debug("Current documentation URL: %s", documentation_input.value)

                # Update if it's empty, has the exact default, or looks like a generated URL
                should_update_documentation = (
                    not documentation_input.value
                    or documentation_input.value == "https://github.com/yourusername/my-awesome-project/README.md"
                    or "my-awesome-project" in documentation_input.value
                    or "yourusername" in documentation_input.value  # Also update if it has the template username
                    or documentation_input.value.startswith("https://github.com/yourusername/")  # Any generated URL
                )

                if should_update_documentation:
                    new_url = f"https://github.com/yourusername/{package_name_url}/README.md"
                    documentation_input.value = new_url
                    self.config.python_documentation_url = new_url
                    logger.debug("Updated documentation URL to: %s", new_url)

            # Update Package Path if it still has the default value
            if packages_input:
                logger.debug("Current package path: %s", packages_input.value)

                # Update if it's empty, has the exact default, or looks like a generated path
                should_update_path = (
                    not packages_input.value
                    or packages_input.value == "src/my_awesome_project"
                    or "my_awesome_project" in packages_input.value
                    or packages_input.value.startswith("src/")  # Any src/ path
                )

                if should_update_path:
                    new_path = f"src/{package_name_clean}"
                    packages_input.value = new_path
                    self.config.python_packages_path = new_path
                    logger.debug("Updated package path to: %s", new_path)

        except Exception as e:
            # Log errors for debugging
            logger.debug("Could not update package-related fields: %s", e)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        # Prevent recursive updates
        if self._updating_checkboxes:
            return

        checkbox_id = event.checkbox.id
        if checkbox_id and checkbox_id.startswith("tool_"):
            tool_name = checkbox_id[5:]  # Remove "tool_" prefix
            self.tool_selected[tool_name] = event.value
            logger.debug("Tool %s %s", tool_name, "selected" if event.value else "deselected")

            # If Python was selected/deselected, update pyproject checkbox state
            if tool_name == "python":
                self._updating_checkboxes = True
                try:
                    repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
                    repo_checkbox.disabled = not event.value
                    if not event.value:
                        repo_checkbox.value = False
                        self.config.install_python_repository = False
                except Exception as e:
                    # Pyproject checkbox might not exist
                    logger.debug("Could not update pyproject checkbox: %s", e)
                finally:
                    self._updating_checkboxes = False

            # Refresh configuration panel for all tool changes
            self.refresh_configuration()
        elif checkbox_id == "py_repo_enabled":
            # Handle pyproject checkbox directly without setting the updating flag
            # since we want refresh_configuration to run
            if self.config.install_python_repository != event.value:
                self.config.install_python_repository = event.value
                logger.debug("Python repository configuration %s", "enabled" if event.value else "disabled")
                # Refresh configuration panel to show/hide pyproject fields
                self.refresh_configuration()

    def action_next(self) -> None:
        """Go to next step."""
        # Save the current tool selection state to config before transitioning
        self.save_tool_selection()

        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_tool_selection)
        self.app.pop_screen()

    def save_tool_selection(self) -> None:
        """Save current tool selection state to the config object and app."""
        # Save tool selection state to config
        self.config.tool_selected = self.tool_selected.copy()
        self.config.tool_version_configurable = self.tool_version_configurable.copy()
        self.config.tool_version_value = self.tool_version_value.copy()

        logger.debug("ToolSelectionScreen: Saved tool selection state: %s", self.config.tool_selected)
        logger.debug("ToolSelectionScreen: Config object ID: %s", id(self.config))

    def action_back(self) -> None:
        """Go back to previous screen."""
        # Should go back to project config
        self.app.push_screen(ProjectConfigScreen(self.config))

    def action_prev_section(self) -> None:
        """Go to previous section."""
        if self.current_section > 0:
            self.current_section -= 1
            self.refresh_tools()
            # Update the section title
            self._update_section_title()

    def action_next_section(self) -> None:
        """Go to next section."""
        if self.current_section < len(self.sections) - 1:
            self.current_section += 1
            self.refresh_tools()
            # Update the section title
            self._update_section_title()

    def _update_section_title(self) -> None:
        """Update the section title label."""
        try:
            title_text = f"Development Tools - {self.sections[self.current_section]} - Section {self.current_section + 1} of {len(self.sections)}"
            # Update the title - need to find and update the title label
            title_labels = self.query("Label.title")
            if title_labels:
                title_label = title_labels[0]
                # Update the label text by changing its children
                if hasattr(title_label, "update"):
                    title_label.update(title_text)
                else:
                    # Remove and recreate with new text
                    parent = title_label.parent
                    title_label.remove()
                    if parent and hasattr(parent, "mount"):
                        parent.mount(Label(title_text, classes="title"), before=0)

            # Update button states
            prev_btn = self.query_one("#prev_btn", Button)
            next_section_btn = self.query_one("#next_section_btn", Button)
            prev_btn.disabled = self.current_section == 0
            next_section_btn.disabled = self.current_section >= len(self.sections) - 1

        except Exception as e:
            logger.debug("Error updating section title: %s", e)

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

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


class ToolVersionScreen(Screen[None], DebugMixin):
    """Screen for configuring tool versions (placeholder for future implementation)."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the tool version screen.

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
            Label("Tool Version Configuration", classes="title"),
            Label(
                "🚧 This screen is reserved for future tool version configuration features.\n[dim]Tool versions are currently configured in the Tool Selection screen.[/dim]",
            ),
            Label("✅ Tool versions are already configured in the previous screen"),
            Button("Continue", id="continue_btn", variant="primary"),
            id="tool-version-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("ToolVersionScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus to the continue button
        try:
            self.query_one("#continue_btn", Button).focus()
        except Exception:
            logger.debug("Could not set focus to continue button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "continue_btn":
            self.action_next()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_next(self) -> None:
        """Continue to next screen."""
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_tool_versions)
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go back to tool selection."""
        # Go back to previous screen
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

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


class PSIHeaderScreen(Screen[None], DebugMixin):
    """Screen for PSI Header configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug", show=True),
    ]

    def __init__(self, config: ProjectConfig, source_dir: Path) -> None:
        """Initialize the PSI Header screen.

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

        # Debug: Log the received config state
        logger.debug("PSI Header: Received config with tool_selected: %s", self.config.tool_selected)
        logger.debug("PSI Header: Config object ID: %s", id(self.config))

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        # Get available languages from devcontainer.json template
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        logger.debug("PSI Header: Looking for devcontainer.json at: %s", devcontainer_file)
        logger.debug("PSI Header: File exists: %s", devcontainer_file.exists())

        available_languages = DevContainerParser.parse_psi_header_languages(devcontainer_file)
        logger.debug("PSI Header: Available languages from devcontainer.json: %s", available_languages)

        # Determine which languages should be auto-selected based on selected tools
        auto_selected_languages = self._get_auto_selected_languages()
        logger.debug("PSI Header: Auto-selected languages: %s", auto_selected_languages)

        yield Header()
        yield Container(
            ScrollableContainer(
                Label("PSI Header Configuration", classes="title"),
                Label(
                    "Configure PSI Header extension for file templates:\n[dim]PSI Header automatically adds copyright and metadata headers to new files.[/dim]",
                ),
                Checkbox("Install PSI Header Extension", id="install_psi", value=self.config.install_psi_header),
                # Configuration panel that shows/hides based on extension installation
                Container(
                    Label("Company Name:\n[dim]Your company/organization name for copyright headers[/dim]"),
                    Input(
                        placeholder="Your Company Name",
                        id="company_name",
                        value=self.config.psi_header_company,
                        classes="compact-input",
                    ),
                    Label("Language Templates:", classes="section-header"),
                    Label(
                        "Select languages for custom headers (auto-selected based on your tools):",
                        classes="compact",
                    ),
                    Container(
                        *self._create_language_checkboxes(available_languages, auto_selected_languages),
                        id="language-container",
                        classes="language-selection",
                    ),
                    id="extension-config-panel",
                    classes="extension-config",
                ),
                id="psi-header-container",
            ),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Next", id="next_btn", variant="primary"),
                id="button-row",
            ),
            id="psi-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("PSIHeaderScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set initial visibility of configuration panel
        self._toggle_config_panel(self.config.install_psi_header)

        # Set focus to the first checkbox
        try:
            self.query_one("#install_psi", Checkbox).focus()
        except Exception:
            logger.debug("Could not set focus to install_psi checkbox")

    def _get_auto_selected_languages(self) -> set[str]:
        """Get languages that should be auto-selected based on selected tools.

        Analyzes the selected development tools and returns a set of language
        identifiers that should be automatically selected for PSI Header templates.

        Returns
        -------
        set[str]
            Set of language identifiers to auto-select (e.g., 'python', 'go', 'javascript')

        """
        auto_selected = set()

        # Debug: Log the current tool selection state
        logger.debug("PSI Header auto-selection: tool_selected = %s", self.config.tool_selected)

        # Try to get tool selection from the app if config is empty
        if not self.config.tool_selected:
            try:
                app = cast("DynamicDevContainerApp", self.app)
                if hasattr(app, "config") and hasattr(app.config, "tool_selected"):
                    logger.debug(
                        "PSI Header: Config tool_selected is empty, trying app.config: %s",
                        app.config.tool_selected,
                    )
                    self.config.tool_selected = app.config.tool_selected.copy()
                    logger.debug("PSI Header: Updated config tool_selected: %s", self.config.tool_selected)
            except Exception as e:
                logger.debug("PSI Header: Could not get tool selection from app: %s", e)

        # Get language mappings from .mise.toml comments
        tool_language_mapping = self._get_tool_language_mapping()
        logger.debug("PSI Header auto-selection: tool_language_mapping = %s", tool_language_mapping)

        # Add languages for selected tools
        for tool, selected in self.config.tool_selected.items():
            if selected and tool in tool_language_mapping:
                language = tool_language_mapping[tool]
                auto_selected.add(language)
                logger.debug("PSI Header auto-selection: Added %s for tool %s", language, tool)

        # Fallback: Add common tool-to-language mappings if .mise.toml doesn't have them
        common_mappings = {
            "python": "python",
            "golang": "go",
            "go": "go",
            "node": "javascript",
            "nodejs": "javascript",
            "rust": "rust",
            "java": "java",
            "dotnet": "csharp",
        }

        for tool, selected in self.config.tool_selected.items():
            if selected and tool in common_mappings:
                language = common_mappings[tool]
                auto_selected.add(language)
                logger.debug("PSI Header auto-selection: Added %s for tool %s (fallback mapping)", language, tool)

        # Always include common languages if any development tools are selected
        if any(self.config.tool_selected.values()):
            auto_selected.update(["shellscript", "markdown"])
            logger.debug("PSI Header auto-selection: Added common languages (shellscript, markdown)")

        logger.debug("PSI Header auto-selection: Final auto_selected = %s", auto_selected)
        return auto_selected

    def _get_tool_language_mapping(self) -> dict[str, str]:
        """Get tool to language mappings from .mise.toml comments.

        Parses .mise.toml file to extract #language: suffixes from tool comments
        and creates a mapping dictionary for PSI Header language selection.

        Returns
        -------
        dict[str, str]
            Mapping from tool names to language identifiers (e.g., {'python': 'python', 'golang': 'go'})

        """
        mapping: dict[str, str] = {}
        tool_assignment_parts = 2

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
                    return mapping

            with open(mise_file, encoding="utf-8") as f:
                content = f.read()

            # Look for tools with language mappings
            lines = content.split("\n")
            for line in lines:
                stripped = line.strip()
                # Look for lines like: tool = 'version' # description #language:python
                if "=" in stripped and "#language:" in stripped:
                    parts = stripped.split("=", 1)
                    if len(parts) == tool_assignment_parts:
                        tool_name = parts[0].strip()
                        # Extract language after #language:
                        language_part = stripped.split("#language:", 1)[1].strip()
                        if language_part:
                            mapping[tool_name] = language_part

        except Exception as e:
            logger.debug("Failed to parse .mise.toml language mappings: %s", e)

        return mapping

    def _create_language_checkboxes(
        self,
        available_languages: list[tuple[str, str]],
        auto_selected: set[str],
    ) -> list[Checkbox]:
        """Create checkboxes for available languages with auto-selection.

        Parameters
        ----------
        available_languages : list[tuple[str, str]]
            List of (language_id, display_name) tuples
        auto_selected : set[str]
            Set of language IDs that should be pre-selected

        Returns
        -------
        list[Checkbox]
            List of checkbox widgets for language selection

        """
        checkboxes = []

        logger.debug("PSI Header: Creating checkboxes for %d languages", len(available_languages))
        logger.debug("PSI Header: Available languages: %s", available_languages)
        logger.debug("PSI Header: Auto-selected languages: %s", auto_selected)

        for lang_id, display_name in available_languages:
            # Check if this language should be auto-selected
            is_selected = lang_id in auto_selected

            # Create a checkbox ID
            checkbox_id = f"lang_{lang_id}"

            logger.debug("PSI Header: Creating checkbox for %s (%s) - selected: %s", lang_id, display_name, is_selected)

            # Create the checkbox
            checkbox = Checkbox(display_name, id=checkbox_id, value=is_selected, classes="compact")
            checkboxes.append(checkbox)

        logger.debug("PSI Header: Created %d checkboxes", len(checkboxes))
        return checkboxes

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.action_next()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        if event.checkbox.id == "install_psi":
            # Toggle visibility of the extension configuration panel
            self._toggle_config_panel(event.value)

    def _toggle_config_panel(self, show: bool) -> None:
        """Show or hide the extension configuration panel.

        Parameters
        ----------
        show : bool
            True to show the panel, False to hide it

        """
        try:
            config_panel = self.query_one("#extension-config-panel", Container)
            if show:
                config_panel.display = True
                logger.debug("PSI Header: Showed configuration panel")
            else:
                config_panel.display = False
                logger.debug("PSI Header: Hid configuration panel")
        except Exception as e:
            logger.debug("PSI Header: Could not toggle config panel visibility: %s", e)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes."""
        # This prevents any interference with debug panel
        # Just handle the company name input
        if event.input.id == "company_name":
            logger.debug("PSI Header: Company name changed to: %s", event.value)

    def save_config(self) -> None:
        """Save PSI Header configuration."""
        self.config.install_psi_header = self.query_one("#install_psi", Checkbox).value
        self.config.psi_header_company = self.query_one("#company_name", Input).value

        # Collect selected language templates from dynamic checkboxes
        self.config.psi_header_templates = []

        # Get available languages from devcontainer.json template
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        available_languages = DevContainerParser.parse_psi_header_languages(devcontainer_file)

        # Check each available language checkbox
        for lang_id, display_name in available_languages:
            checkbox_id = f"lang_{lang_id}"
            try:
                checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                if checkbox.value:
                    # Extract just the language name from display name (e.g., "Python" from "Python (.py)")
                    lang_name = display_name.split(" (")[0] if " (" in display_name else display_name
                    self.config.psi_header_templates.append((lang_id, lang_name))
            except NoMatches:
                # Skip if checkbox doesn't exist
                continue

        logger.debug(
            "PSI Header config saved: install=%s, company=%s, templates=%s",
            self.config.install_psi_header,
            self.config.psi_header_company,
            self.config.psi_header_templates,
        )

        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_psi_header)
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to next step."""
        self.save_config()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go back to previous screen."""
        # Go back to tool selection screen
        app = cast("DynamicDevContainerApp", self.app)
        self.app.pop_screen()
        app.show_tool_selection()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it and mount to main container
            try:
                main_container = self.query_one("#psi-container")

                debug_log = RichLog(
                    max_lines=50,
                    wrap=True,
                    highlight=True,
                    markup=True,
                    id="debug_log",
                )

                # Populate immediately with current messages
                self._populate_debug_log(debug_log)

                debug_container = Container(
                    Horizontal(
                        Label("Debug Output (Ctrl+D to toggle):", classes="debug-title"),
                        Button("Copy Debug", id="copy_debug_btn", classes="debug-copy-btn"),
                        id="debug-header",
                    ),
                    debug_log,
                    id="debug_container",
                    classes="debug-panel",
                )

                # Mount to main container instead of screen level
                main_container.mount(debug_container)
            except Exception as e:
                logger.debug("PSI Header: Failed to create debug panel: %s", e)

    def key_ctrl_d(self, event: Key) -> None:
        """Handle Ctrl+D key even when Input widgets have focus."""
        event.stop()  # Stop event propagation to prevent Input handling
        self.action_toggle_debug()


class SummaryScreen(Screen[None], DebugMixin):
    """Screen showing configuration summary before installation."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the summary screen.

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
        yield ScrollableContainer(
            Label("Configuration Summary", classes="title"),
            Label(
                "Review your configuration before installation:\n[dim]Verify all settings are correct before proceeding with the installation.[/dim]",
            ),
            self._create_project_config_section(),
            self._create_tools_section(),
            self._create_extensions_section(),
            self._create_python_config_section(),
            Horizontal(
                Button("Back", id="back_btn"),
                Button("Install & Generate", id="continue_btn", variant="primary"),
                id="button-row",
            ),
            id="summary-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("SummaryScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus to the continue button
        try:
            self.query_one("#continue_btn", Button).focus()
        except Exception:
            logger.debug("Could not set focus to continue button")

    def _create_project_config_section(self) -> Container:
        """Create project configuration summary section.

        Returns
        -------
        Container
            Widget container with project configuration details

        """
        content: list[Label | Markdown] = []
        content.append(Label("📁 Project Configuration", classes="section-header"))

        # Project details
        details = [
            f"**Project Name:** {self.config.project_name or 'Not set'}",
            f"**Display Name:** {self.config.display_name or 'Not set'}",
            f"**Project Path:** {self.config.project_path or 'Not set'}",
            f"**Container Name:** {self.config.container_name or 'Not set'}",
        ]

        if self.config.docker_exec_command:
            details.append(f"**Docker Exec Command:** {self.config.docker_exec_command}")

        content.append(Markdown("\n".join(details)))
        return Container(*content, classes="summary-section")

    def _create_tools_section(self) -> Container:
        """Create tools configuration summary section.

        Returns
        -------
        Container
            Widget container with tools configuration details

        """
        content: list[Label | Markdown] = []
        content.append(Label("🛠️  Development Tools", classes="section-header"))

        # Selected tools
        if self.config.tool_selected:
            selected_tools = [tool for tool, selected in self.config.tool_selected.items() if selected]
            if selected_tools:
                tools_info = []
                for tool in sorted(selected_tools):
                    version = self.config.tool_version_value.get(tool, "latest")
                    tools_info.append(f"- **{tool}:** {version}")
                content.append(Markdown("**Selected Tools:**\n" + "\n".join(tools_info)))
            else:
                content.append(Label("No tools selected", classes="compact"))
        else:
            content.append(Label("No tools configured", classes="compact"))

        return Container(*content, classes="summary-section")

    def _create_extensions_section(self) -> Container:
        """Create VS Code extensions summary section.

        Returns
        -------
        Container
            Widget container with extensions configuration details

        """
        content: list[Label | Markdown] = []
        content.append(Label("🧩 VS Code Extensions", classes="section-header"))

        # PSI Header extension
        if self.config.install_psi_header:
            psi_info = ["**PSI Header Extension:** ✅ Enabled"]
            if self.config.psi_header_company:
                psi_info.append(f"- **Company Name:** {self.config.psi_header_company}")
            if self.config.psi_header_templates:
                template_names = [template[1] for template in self.config.psi_header_templates]
                psi_info.append(f"- **Language Templates:** {', '.join(template_names)}")
            content.append(Markdown("\n".join(psi_info)))
        else:
            content.append(Label("**PSI Header Extension:** ❌ Disabled", classes="compact"))

        # Add other extensions here as they're implemented
        return Container(*content, classes="summary-section")

    def _create_python_config_section(self) -> Container:
        """Create Python project configuration summary section.

        Returns
        -------
        Container
            Widget container with Python configuration details

        """
        content: list[Label | Markdown] = []

        # Only show this section if Python is selected and repository is enabled
        if self.config.tool_selected.get("python", False) and self.config.install_python_repository:
            content.append(Label("🐍 Python Project Configuration", classes="section-header"))

            python_info = [
                f"**Package Name:** {self.config.python_project_name or 'Not set'}",
                f"**Description:** {self.config.python_project_description or 'Not set'}",
                f"**Author:** {self.config.python_author_name or 'Not set'}",
            ]

            if self.config.python_author_email:
                python_info.append(f"**Author Email:** {self.config.python_author_email}")

            python_info.extend(
                [
                    f"**Required Python:** {self.config.python_requires_python or '>=3.12'}",
                    f"**Package Path:** {self.config.python_packages_path or 'Not set'}",
                ],
            )

            # URLs
            if any(
                [
                    self.config.python_homepage_url,
                    self.config.python_source_url,
                    self.config.python_documentation_url,
                ],
            ):
                python_info.append("**Project URLs:**")
                if self.config.python_homepage_url:
                    python_info.append(f"- Homepage: {self.config.python_homepage_url}")
                if self.config.python_source_url:
                    python_info.append(f"- Source: {self.config.python_source_url}")
                if self.config.python_documentation_url:
                    python_info.append(f"- Documentation: {self.config.python_documentation_url}")

            content.append(Markdown("\n".join(python_info)))

        return Container(*content, classes="summary-section") if content else Container()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "continue_btn":
            self.action_next()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_next(self) -> None:
        """Continue to installation."""
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_summary)
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go back to PSI Header configuration."""
        # Go back to PSI Header screen
        app = cast("DynamicDevContainerApp", self.app)
        self.app.pop_screen()
        app.show_psi_header_config()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

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


class InstallationScreen(Screen[None], DebugMixin):
    """Screen for handling the installation process."""

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

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

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield ScrollableContainer(
            Label("Installation & File Generation", classes="title"),
            Label(
                "Generating dev container files and configuration:\n[dim]Please wait while your development environment is being configured.[/dim]",
            ),
            Container(
                Label("📋 Installation Steps:", classes="section-header"),
                Label("✅ Configuration validated", classes="compact"),
                Label("⏳ Generating devcontainer.json...", classes="compact"),
                Label("⏳ Generating .mise.toml...", classes="compact"),
                Label("⏳ Configuring VS Code extensions...", classes="compact"),
                Label("⏳ Setting up project structure...", classes="compact"),
                id="progress-section",
            ),
            Container(
                Label("📁 Files to be created/updated:", classes="section-header"),
                Label("- .devcontainer/devcontainer.json", classes="compact"),
                Label("- .mise.toml", classes="compact"),
                Label("- pyproject.toml (if Python project enabled)", classes="compact"),
                Label("- Various configuration files", classes="compact"),
                id="files-section",
            ),
            Button("Finish", id="finish_btn", variant="primary", disabled=True),
            id="install-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("InstallationScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Start the installation process
        self.call_later(self._simulate_installation)

    def _simulate_installation(self) -> None:
        """Simulate the installation process.

        This is a placeholder that simulates the installation steps.
        In a real implementation, this would call the actual installation logic.
        """
        # For now, just show that installation is complete after a delay
        self.set_timer(2.0, self._complete_installation)

    def _complete_installation(self) -> None:
        """Mark installation as complete."""
        try:
            # Update progress indicators
            progress_section = self.query_one("#progress-section", Container)
            progress_section.remove_children()
            progress_section.mount_all(
                [
                    Label("📋 Installation Complete:", classes="section-header"),
                    Label("✅ Configuration validated", classes="compact"),
                    Label("✅ Generated devcontainer.json", classes="compact"),
                    Label("✅ Generated .mise.toml", classes="compact"),
                    Label("✅ Configured VS Code extensions", classes="compact"),
                    Label("✅ Project structure created", classes="compact"),
                ],
            )

            # Enable the finish button
            finish_btn = self.query_one("#finish_btn", Button)
            finish_btn.disabled = False
            finish_btn.focus()

            self.notify("Installation completed successfully!", severity="information")

        except Exception as e:
            logger.debug("Error completing installation simulation: %s", e)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "finish_btn":
            self.action_finish()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_finish(self) -> None:
        """Finish the installation and exit."""
        self.notify("Dynamic Dev Container setup complete!", severity="information")
        self.app.exit()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

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


__all__ = [
    "DebugMixin",
    "WelcomeScreen",
    "ProjectConfigScreen",
    "ToolSelectionScreen",
    "ToolVersionScreen",
    "PSIHeaderScreen",
    "SummaryScreen",
    "InstallationScreen",
]
