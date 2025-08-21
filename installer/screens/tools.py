"""Tool-related screens for the Dynamic Dev Container installer.

This module contains screens for tool selection and version configuration.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

try:
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Label
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    import sys

    sys.exit(1)

from installer.screens.project import ProjectConfigScreen
from installer.tools import MiseParser, ToolManager
from installer.utils import logger

from .mixins import DebugMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Focus

    from installer.app import DynamicDevContainerApp
    from installer.config import ProjectConfig


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
        source_dir: Path | None = None,
    ) -> None:
        """Initialize the tool selection screen.

        Parameters
        ----------
        config : ProjectConfig
            The project configuration data
        sections : list[str]
            List of tool sections available
        tool_selected : dict[str, bool]
            Mapping of tool names to their selection status
        tool_version_configurable : dict[str, bool]
            Mapping of tool names to whether they support version configuration
        tool_version_value : dict[str, str]
            Mapping of tool names to their configured versions
        source_dir : Path, optional
            Path to the source directory containing .mise.toml

        """
        super().__init__()
        self.config = config
        self.sections = sections
        self.tool_selected = tool_selected
        self.tool_version_configurable = tool_version_configurable
        self.tool_version_value = tool_version_value
        self.source_dir = source_dir or Path.cwd()
        self.current_section = 0
        self._updating_checkboxes = False
        self._refreshing_config = False
        self._widget_counter = 0
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
            # Check if current section has multiple tools for Select All button
            current_section = self.sections[self.current_section]
            tools_in_section = MiseParser.get_section_tools(self.source_dir / ".mise.toml", current_section)
            show_select_all = len(tools_in_section) > 1

            # Create tools header with Select All button (always create but hide if not needed)
            select_all_btn = Button("Select All", id="select_all_tools", classes="version-btn-small")
            if not show_select_all:
                select_all_btn.display = False

            tools_header_widgets = [
                Label("Available Tools:", classes="column-title"),
                select_all_btn,
            ]

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

        # Initialize the tools display and update header
        self.refresh_tools()
        self._update_tools_header_if_needed()

    def refresh_tools(self) -> None:
        """Refresh the tools display for current section."""
        if not self.sections:
            return

        try:
            tools_container = self.query_one("#tools-scroll", ScrollableContainer)
            tools_container.remove_children()

            current_section = self.sections[self.current_section]
            tools = MiseParser.get_section_tools(self.source_dir / ".mise.toml", current_section)

            if not tools:
                tools_container.mount(Label("No tools found in this section", classes="compact"))
                return

            # Add checkboxes for each tool
            first_checkbox = None
            for tool in tools:
                description = ToolManager.get_tool_description(tool)
                checkbox = Checkbox(description, id=f"tool_{tool}", classes="compact")
                checkbox.value = self.tool_selected.get(tool, False)
                tools_container.mount(checkbox)

                # Remember the first checkbox for focus
                if first_checkbox is None:
                    first_checkbox = checkbox

            # Handle Python repository configuration if Python is available AND selected
            if "python" in tools:
                python_selected = self.tool_selected.get("python", False)
                if python_selected:
                    # Add pyproject.toml configuration checkbox only when Python is selected
                    repo_checkbox = Checkbox(
                        "Configure pyproject.toml",
                        id="py_repo_enabled",
                        value=self.config.install_python_repository,
                        classes="compact repo-checkbox",
                    )
                    tools_container.mount(repo_checkbox)

            # Update configuration panel
            self.refresh_configuration()

            # Focus the first checkbox for better UX
            if first_checkbox is not None:
                self.call_after_refresh(lambda: first_checkbox.focus())

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
            tools_in_current_section = MiseParser.get_section_tools(self.source_dir / ".mise.toml", current_section)

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
                return

            # Show Python configuration first if Python is selected
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
                    )

            # Show other tool configurations
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

    def _select_all_tools(self) -> None:
        """Select all available tools in the current section."""
        try:
            if not self.sections:
                return

            current_section = self.sections[self.current_section]
            tools = MiseParser.get_section_tools(self.source_dir / ".mise.toml", current_section)

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
                    # The checkbox should be created by the Python checkbox selection logic
                    # but if it doesn't exist yet, we may need to create it here
                    repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
                    # Optionally auto-enable pyproject.toml configuration
                    repo_checkbox.value = True
                    self.config.install_python_repository = True
                except Exception as e:
                    logger.debug(
                        "Could not update Python repository checkbox (will be created by checkbox handler): %s",
                        e,
                    )

            # Refresh configuration panel to show settings for all selected tools
            self.refresh_configuration()

            logger.debug("Selected all tools in section %s: %s", current_section, tools)

        except Exception as e:
            logger.debug("Error selecting all tools: %s", e)

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

            # If Python was selected/deselected, add/remove pyproject checkbox
            if tool_name == "python":
                self._updating_checkboxes = True
                try:
                    tools_container = self.query_one("#tools-scroll")

                    if event.value:
                        # Python was selected - add the pyproject checkbox if it doesn't exist
                        try:
                            # Check if checkbox already exists
                            self.query_one("#py_repo_enabled", Checkbox)
                        except Exception:
                            # Checkbox doesn't exist, create and add it
                            repo_checkbox = Checkbox(
                                "Configure pyproject.toml",
                                id="py_repo_enabled",
                                value=self.config.install_python_repository,
                                classes="compact repo-checkbox",
                            )
                            tools_container.mount(repo_checkbox)
                    else:
                        # Python was deselected - remove the pyproject checkbox if it exists
                        try:
                            repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
                            repo_checkbox.remove()
                            self.config.install_python_repository = False
                        except Exception as e:
                            # Checkbox doesn't exist, nothing to remove
                            logger.debug("Pyproject checkbox not found for removal: %s", e)
                except Exception as e:
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

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes."""
        input_id = event.input.id
        if input_id and input_id.startswith("version_"):
            # Handle tool version input changes
            parts = input_id.split("_", 2)  # Split into ['version', tool, counter]
            if len(parts) >= 2:  # noqa: PLR2004
                tool = parts[1]
                new_value = event.value.strip() or "latest"
                if tool in self.tool_version_value:
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

    def _update_username_from_homepage(self) -> None:
        """Update username in other URLs based on homepage URL."""
        try:
            # Find homepage input field (with dynamic ID)
            all_inputs = self.query(Input)
            homepage_input = None
            for inp in all_inputs:
                if inp.id and inp.id.startswith("pyproject_homepage"):
                    homepage_input = inp
                    break

            if not homepage_input:
                return

            homepage_url = homepage_input.value
            if homepage_url:
                logger.debug("Processing homepage URL on focus loss: %s", homepage_url)
                self._check_and_propagate_username(homepage_url)

        except Exception as e:
            # Inputs might not exist yet
            logger.debug("Could not update username from homepage: %s", e)

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

    def save_tool_selection(self) -> None:
        """Save current tool selection state to the config object and app."""
        # Save tool selection state to config
        self.config.tool_selected = self.tool_selected.copy()
        self.config.tool_version_configurable = self.tool_version_configurable.copy()
        self.config.tool_version_value = self.tool_version_value.copy()

        logger.debug("ToolSelectionScreen: Saved tool selection state: %s", self.config.tool_selected)
        logger.debug("ToolSelectionScreen: Config object ID: %s", id(self.config))

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

    def action_back(self) -> None:
        """Go back to previous screen."""
        # Should go back to project config
        self.app.push_screen(ProjectConfigScreen(self.config))

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

    def action_next(self) -> None:
        """Save tool selection and go to next screen."""
        self.save_tool_selection()
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_tool_selection)
        self.app.pop_screen()

    def action_prev_section(self) -> None:
        """Go to previous tool section."""
        if self.current_section > 0:
            self.current_section -= 1
            self.refresh_tools()
            self._update_section_title()
            self._update_section_buttons()
            self._update_tools_header_if_needed()

    def action_next_section(self) -> None:
        """Go to next tool section."""
        if self.current_section < len(self.sections) - 1:
            self.current_section += 1
            self.refresh_tools()
            self._update_section_title()
            self._update_section_buttons()
            self._update_tools_header_if_needed()

    def _update_tools_header(self) -> None:
        """Update the tools header with conditional Select All button."""
        try:
            tools_header = self.query_one("#tools-header", Horizontal)

            # Check if current section has multiple tools
            current_section = self.sections[self.current_section]
            logger.debug(
                "_update_tools_header called for section: %s (index %d)",
                current_section,
                self.current_section,
            )

            tools_in_section = MiseParser.get_section_tools(self.source_dir / ".mise.toml", current_section)

            logger.debug(
                "Updating tools header for section %s: found %d tools: %s",
                current_section,
                len(tools_in_section),
                tools_in_section,
            )

            # Check if Select All button already exists
            try:
                select_all_btn = self.query_one("#select_all_tools")
                # Button exists, show/hide based on tool count
                if len(tools_in_section) > 1:
                    select_all_btn.display = True
                    logger.debug("Showed existing Select All button for section %s", current_section)
                else:
                    select_all_btn.display = False
                    logger.debug("Hid existing Select All button for section %s", current_section)

            except Exception:
                # Button doesn't exist, create it if needed
                if len(tools_in_section) > 1:
                    select_all_btn = Button("Select All", id="select_all_tools", classes="version-btn-small")
                    tools_header.mount(select_all_btn)
                    logger.debug("Created new Select All button for section %s", current_section)
                else:
                    logger.debug(
                        "No Select All button needed for section %s - only %d tools",
                        current_section,
                        len(tools_in_section),
                    )

        except Exception as e:
            logger.error("Error updating tools header: %s", e)

    def _update_tools_header_if_needed(self) -> None:
        """Update tools header if it exists (for when screen is already mounted)."""
        try:
            # Only try to update if the header exists (screen is mounted)
            self.query_one("#tools-header", Horizontal)
            self._update_tools_header()
        except Exception:
            # Header doesn't exist yet, will be created in compose()
            logger.debug("Tools header not found, skipping update")

    def _update_section_title(self) -> None:
        """Update the section title display."""
        try:
            title_label = self.query_one("Label.title")
            current_section = self.sections[self.current_section]
            new_title = (
                f"Development Tools - {current_section} - Section {self.current_section + 1} of {len(self.sections)}"
            )

            # Remove the old title and mount a new one
            title_label.remove()

            # Find the parent container and mount new title
            container = self.query_one("#tools-container")
            container.mount(Label(new_title, classes="title"), before=0)

        except Exception as e:
            logger.debug("Could not update section title: %s", e)

    def _update_section_buttons(self) -> None:
        """Update section navigation button states."""
        try:
            prev_btn = self.query_one("#prev_btn", Button)
            next_btn = self.query_one("#next_section_btn", Button)

            prev_btn.disabled = self.current_section == 0
            next_btn.disabled = self.current_section >= len(self.sections) - 1
        except Exception as e:
            logger.debug("Could not update section buttons: %s", e)


class ToolVersionScreen(Screen[None], DebugMixin):
    """Screen for configuring tool versions."""

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
        yield Label("Tool Version Screen - To be implemented", classes="title")
        yield Footer()

    def action_next(self) -> None:
        """Go to next screen."""
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go to previous screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
