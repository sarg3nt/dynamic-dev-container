"""Tool selection screen actions and navigation for the Dynamic Dev Container installer.

This module contains action methods, configuration saving, and finalization functionality
for the ToolSelectionScreen class, including screen navigation, tool selection finalization,
and debug panel management.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from textual import log as logger
from textual.widgets import Checkbox, Input, RadioSet

from installer.mise_parser import MiseParser

if TYPE_CHECKING:
    from installer.app import DevContainerApp


class ToolSelectionActionMixin:
    """Mixin providing action and navigation functionality for ToolSelectionScreen.

    This mixin requires the parent class to provide:
    - config: ProjectConfig instance for accessing project configuration
    - current_section: int for current section index
    - sections: list for section names
    - tool_selected: dict for tool selection state
    - tool_version_configurable: dict for tool version configurability
    - tool_version_value: dict for tool version values
    - _widget_generation: int for widget generation tracking
    - query_one: Method for querying Textual widgets by ID
    - app: Application instance for screen navigation
    """

    def save_current_section(self) -> None:
        """Save tool selections and configuration values for the current section.

        Iterates through all tools in the current section and saves their checkbox states
        to the tool_selected dictionary. Also triggers saving of configuration values.
        """
        if not self.sections:
            return

        current_section = self.sections[self.current_section]
        tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

        for tool in tools:
            try:
                checkbox = self.query_one(f"#tool_{tool}", Checkbox)
                self.tool_selected[tool] = checkbox.value
            except Exception as e:
                logger.debug("Checkbox for tool '%s' not found during save: %s", tool, e)

        # Save any configuration values
        self.save_configuration_values()

    def save_configuration_values(self) -> None:
        """Save current configuration values from input fields and controls.

        Retrieves values from various UI elements including Python repository settings,
        repository type selections, and configuration URLs, then updates the
        application configuration object with these values.
        """
        # Save Python repository configuration enable/disable
        try:
            py_repo_checkbox = self.query_one("#py_repo_enabled", Checkbox)
            self.config.install_python_repository = py_repo_checkbox.value
        except Exception as e:
            logger.debug("Python repository enabled checkbox not found during save: %s", e)

        # Save Python configuration
        try:
            radio_set = self.query_one("#py_repo_radioset", RadioSet)
            if radio_set.pressed_button:
                if radio_set.pressed_button.id == "py_repo_pypi":
                    self.config.python_repository_type = "PyPI"
                elif radio_set.pressed_button.id == "py_repo_artifactory":
                    self.config.python_repository_type = "Artifactory"
                elif radio_set.pressed_button.id == "py_repo_nexus":
                    self.config.python_repository_type = "Nexus"
                elif radio_set.pressed_button.id == "py_repo_custom":
                    self.config.python_repository_type = "Custom"
        except Exception as e:
            logger.debug("Python repository type radioset not found during save: %s", e)

        try:
            self.config.python_index_url = self.query_one("#pyproject_index_url", Input).value
        except Exception as e:
            logger.debug("Python index URL input not found during save: %s", e)

        try:
            self.config.python_publish_url = self.query_one("#py_publish_url", Input).value
        except Exception as e:
            logger.debug("Python publish URL input not found during save: %s", e)

        # Save additional pyproject.toml configuration
        try:
            self.config.python_project_name = self.query_one("#pyproject_name", Input).value
        except Exception as e:
            logger.debug("Project name input not found during save: %s", e)

        try:
            self.config.python_project_description = self.query_one("#pyproject_description", Input).value
        except Exception as e:
            logger.debug("Project description input not found during save: %s", e)

        try:
            self.config.python_requires_python = self.query_one("#pyproject_requires_python", Input).value
        except Exception as e:
            logger.debug("Required Python version input not found during save: %s", e)

        try:
            self.config.python_author_name = self.query_one("#pyproject_author_name", Input).value
        except Exception as e:
            logger.debug("Author name input not found during save: %s", e)

        try:
            self.config.python_author_email = self.query_one("#pyproject_author_email", Input).value
        except Exception as e:
            logger.debug("Author email input not found during save: %s", e)

        try:
            self.config.python_homepage_url = self.query_one("#pyproject_homepage", Input).value
        except Exception as e:
            logger.debug("Homepage URL input not found during save: %s", e)

        try:
            self.config.python_source_url = self.query_one("#pyproject_source", Input).value
        except Exception as e:
            logger.debug("Source URL input not found during save: %s", e)

        try:
            self.config.python_documentation_url = self.query_one("#pyproject_documentation", Input).value
        except Exception as e:
            logger.debug("Documentation URL input not found during save: %s", e)

        try:
            self.config.python_packages_path = self.query_one("#pyproject_packages", Input).value
        except Exception as e:
            logger.debug("Packages path input not found during save: %s", e)

        # Save version configurations - only for configurable tools in the current section
        # since version inputs are only shown for the current section
        current_section_name = self.sections[self.current_section] if self.sections else None
        if current_section_name:
            current_section_tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section_name)
            configurable_tools_in_current_section = [
                tool
                for tool in current_section_tools
                if (self.tool_version_configurable.get(tool, False) and self.tool_selected.get(tool, False))
            ]

            for tool in configurable_tools_in_current_section:
                try:
                    # Try generation-based ID first
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    version_input = self.query_one(f"#{version_id}", Input)
                    self.tool_version_value[tool] = version_input.value or "latest"
                except Exception as e:
                    logger.debug("Generation-based version input for tool '%s' not found: %s", tool, e)
                    try:
                        # Fallback to simple ID format
                        version_input = self.query_one(f"#version_{tool}", Input)
                        self.tool_version_value[tool] = version_input.value or "latest"
                    except Exception as e:
                        logger.debug("Version input for tool '%s' not found during save: %s", tool, e)

    def finalize_selection(self) -> None:
        """Finalize tool selection and continue.

        Saves the current section configuration, updates the application config
        with tool selections and versions, sets extension flags based on selected
        tools, and navigates to the next screen in the workflow.
        """
        # Save current section before finalizing
        self.save_current_section()

        # Update config with selections
        self.config.tool_selected = self.tool_selected
        self.config.tool_version_configurable = self.tool_version_configurable
        self.config.tool_version_value = self.tool_version_value

        # Set extension flags based on selected tools
        for tool, selected in self.tool_selected.items():
            if selected:
                if tool == "python":
                    self.config.install_python_tools = True
                    self.config.include_python_extensions = True
                elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                    self.config.include_js_extensions = True
            if selected:
                if tool == "python":
                    self.config.install_python_tools = True
                    self.config.include_python_extensions = True
                elif tool in ["node", "pnpm", "yarn", "deno", "bun"]:
                    self.config.include_js_extensions = True

        # Always include markdown and shell extensions by default
        self.config.include_markdown_extensions = True
        self.config.include_shell_extensions = True

        # Go directly to tool version configuration or next step
        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_tool_selection)
        self.app.pop_screen()

    def action_toggle_debug(self) -> None:
        """Toggle debug mode.

        Shows or hides the debug panel based on current state. If the debug
        panel exists, it will be removed. If it doesn't exist, it will be created.
        """
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self.__rebuild_with_debug_panel()

    def action_next(self) -> None:
        """Go to next step.

        Saves the current section configuration and finalizes the tool selection
        to proceed to the next screen in the configuration workflow.
        """
        self.save_current_section()
        self.finalize_selection()

    def action_quit(self) -> None:
        """Quit the application.

        Exits the application immediately without saving any pending changes.
        """
        self.app.exit()

    def action_back(self) -> None:
        """Go to previous step.

        Returns to the previous screen (ProjectConfigScreen) in the workflow.
        """
        # Import here to avoid circular imports
        from installer.screens.project_config import ProjectConfigScreen  # noqa: PLC0415

        self.app.push_screen(ProjectConfigScreen(self.config))

    def __select_all_tools(self) -> None:
        """Select all available tools in the current section.

        Sets all tools in the current section as selected in the internal state
        and updates the corresponding checkboxes to checked state. Also handles
        Python repository configuration if Python is among the selected tools.
        """
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

    def __rebuild_with_debug_panel(self) -> None:
        """Rebuild the screen with debug panel.

        This method is implemented by the main screen class that includes
        debug functionality. It's called when debug mode is toggled on.
        """
        # This method should be implemented by the main class that has debug capability
        # It's included here as a placeholder for the mixin pattern
