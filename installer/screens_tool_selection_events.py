"""Tool selection screen event handlers for the Dynamic Dev Container installer.

This module contains all event handling functionality for the ToolSelectionScreen class,
including checkbox changes, button presses, input field events, and navigation actions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from textual import log as logger
from textual.widgets import Button, Checkbox, Input, RadioSet

from installer.mise_parser import MiseParser

if TYPE_CHECKING:
    from textual.events import Focus, Key

    from installer.config import ProjectConfig

# Constants
VERSION_BUTTON_PARTS = 4


class ToolSelectionEventMixin:
    """Event handling functionality for the Tool Selection screen.

    This mixin requires the following attributes to be present on the class:
    - config: ProjectConfig
    - tool_selected: dict[str, bool]
    - tool_version_configurable: dict[str, bool]
    - tool_version_value: dict[str, str]
    - sections: list[str]
    - current_section: int
    - _username_propagated: bool
    - _last_focused_input: str
    - Various UI query methods from Textual Screen class
    """

    # These attributes should be set by the main class
    config: ProjectConfig
    tool_selected: dict[str, bool]
    tool_version_configurable: dict[str, bool]
    tool_version_value: dict[str, str]
    sections: list[str]
    current_section: int
    _username_propagated: bool
    _last_focused_input: str

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes.

        Parameters
        ----------
        event : Checkbox.Changed
            The checkbox change event

        """
        if not event.checkbox.id:
            return

        # Extract tool name from checkbox ID
        if event.checkbox.id.startswith("tool_"):
            tool_name = event.checkbox.id[5:]  # Remove "tool_" prefix
            self.tool_selected[tool_name] = event.checkbox.value
            logger.debug("Tool %s %s", tool_name, "selected" if event.checkbox.value else "deselected")

            # If Python is selected/deselected, update repository checkbox
            if tool_name == "python":
                self.__handle_python_tool_selection(event.checkbox.value)

            # Refresh configuration panel
            self.refresh_configuration()  # type: ignore[attr-defined]

        elif event.checkbox.id == "py_repo_enabled":
            # Python repository configuration toggle
            self.config.install_python_repository = event.checkbox.value
            logger.debug("Python repository configuration %s", "enabled" if event.checkbox.value else "disabled")
            # Refresh the entire tools display to show/hide repository options
            self.__refresh_python_repository_settings()

        elif event.checkbox.id.startswith("py_repo_"):
            # Handle Python repository type checkboxes (if any specific ones exist)
            logger.debug("Python repository option changed: %s = %s", event.checkbox.id, event.checkbox.value)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio set changes for Python repository type.

        Parameters
        ----------
        event : RadioSet.Changed
            The radio set change event

        """
        if event.radio_set.id == "py_repo_radioset":
            # This would handle repository type radio buttons if they exist
            selected_value = event.pressed.id if event.pressed else None
            logger.debug("Python repository type changed to: %s", selected_value)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes.

        Parameters
        ----------
        event : Input.Changed
            The input change event

        """
        if not event.input.id:
            return

        if event.input.id.startswith("version_"):
            tool_name = event.input.id[8:]  # Remove "version_" prefix
            self.tool_version_value[tool_name] = event.value
            logger.debug("Version for %s set to: %s", tool_name, event.value)

        elif event.input.id == "py_index_url":
            self.config.python_index_url = event.value
            logger.debug("Python index URL updated: %s", event.value)

        elif event.input.id == "py_publish_url":
            self.config.python_publish_url = event.value
            logger.debug("Python publish URL updated: %s", event.value)

        elif event.input.id == "pyproject_name":
            self.config.python_project_name = event.value
            logger.debug("Python project name updated: %s", event.value)
            # Update package-related fields when project name changes
            self.__update_package_related_fields(event.value)

        elif event.input.id == "github_username":
            self.config.python_github_username = event.value
            logger.debug("GitHub username updated: %s", event.value)
            # Update URL fields when username changes
            self.__update_github_related_fields(event.value)

        elif event.input.id == "pyproject_homepage":
            self.config.python_homepage_url = event.value
            logger.debug("Homepage URL updated: %s", event.value)

        # Handle other Python project configuration inputs
        elif event.input.id == "py_project_name":
            self.config.python_project_name = event.value
            self.__update_package_related_fields(event.value)

        elif event.input.id == "py_project_description":
            self.config.python_project_description = event.value

        elif event.input.id == "py_author_name":
            self.config.python_author_name = event.value

        elif event.input.id == "py_author_email":
            self.config.python_author_email = event.value

        elif event.input.id == "py_custom_license":
            # Handle custom license input (would need to add this field to config)
            logger.debug("Custom license updated: %s", event.value)

        elif event.input.id == "py_repo_url":
            self.config.python_publish_url = event.value

        elif event.input.id == "py_index_url":
            self.config.python_index_url = event.value

    def on_focus(self, event: Focus) -> None:
        """Handle focus events to track input focus changes."""
        # Track the currently focused input
        if event.control and hasattr(event.control, "id") and event.control.id and isinstance(event.control, Input):
            self._last_focused_input = event.control.id
            logger.debug("Input focused: %s", event.control.id)

    def on_descendant_focus(self, event: Focus) -> None:
        """Handle when focus moves to track focus loss from inputs."""
        # When focus moves from one input to another, process the previous input
        if (
            hasattr(self, "_last_focused_input")
            and event.control
            and hasattr(event.control, "id")
            and event.control.id != self._last_focused_input
            and self._last_focused_input
        ):
            # Process the input that just lost focus
            self.__process_input_on_focus_loss(self._last_focused_input)
            self._last_focused_input = ""

    def on_key(self, event: Key) -> None:
        """Handle key events for immediate processing."""
        # Check if Enter was pressed in Homepage URL field
        if (
            event.key == "enter"
            and hasattr(self, "app")
            and self.app.focused
            and hasattr(self.app.focused, "id")
            and self.app.focused.id == "pyproject_homepage"
        ):
            # Process homepage URL immediately when Enter is pressed
            try:
                homepage_input = self.query_one("#pyproject_homepage", Input)  # type: ignore[attr-defined]
                self.__check_and_propagate_username(homepage_input.value)
            except Exception as e:
                logger.debug("Could not process homepage URL on Enter: %s", e)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Parameters
        ----------
        event : Button.Pressed
            The button press event

        """
        if not event.button.id:
            return

        button_id = event.button.id

        # Handle version button clicks
        if button_id.startswith("version_btn_"):
            self.__handle_version_button_press(button_id)

        # Handle section link clicks
        elif button_id.startswith("section_link_"):
            section_index = int(button_id.split("_")[-1])
            self.__handle_section_navigation(section_index)

        # Handle main navigation buttons
        elif button_id == "back_btn":
            self.action_back()  # type: ignore[attr-defined]

        elif button_id == "prev_btn":
            self.__navigate_to_previous_section()

        elif button_id == "next_section_btn":
            self.__navigate_to_next_section()

        elif button_id == "next_btn":
            self.action_next()  # type: ignore[attr-defined]

        elif button_id == "select_all_tools":
            self.__select_all_tools()

        elif button_id == "copy_debug_btn":
            self.__copy_debug_info()

        elif button_id == "generate_urls":
            self.__generate_package_urls()

    def __handle_python_tool_selection(self, is_selected: bool) -> None:
        """Handle Python tool selection/deselection.

        Parameters
        ----------
        is_selected : bool
            Whether Python tool is now selected

        """
        if is_selected:
            # Python was selected - show repository configuration option
            logger.debug("Python tool selected, showing repository configuration option")
        else:
            # Python was deselected - hide repository configuration
            self.config.install_python_repository = False
            logger.debug("Python tool deselected, hiding repository configuration")

        # Refresh the tools display to update repository checkbox visibility
        self.__refresh_python_repository_settings()

    def __handle_version_button_press(self, button_id: str) -> None:
        """Handle version button press events.

        Parameters
        ----------
        button_id : str
            The ID of the pressed version button

        """
        # Parse button ID: "version_btn_{tool}_{version}"
        parts = button_id.split("_", 3)
        if len(parts) >= VERSION_BUTTON_PARTS:
            tool = parts[2]
            version = parts[3]
            self.tool_version_value[tool] = version
            logger.debug("Version button pressed: %s = %s", tool, version)

            # Update the corresponding input field if it exists
            try:
                version_input = self.query_one(f"#version_{tool}", Input)  # type: ignore[attr-defined]
                version_input.value = version
            except Exception:
                # Input might not exist yet
                pass

    def __handle_section_navigation(self, section_index: int) -> None:
        """Handle navigation to a specific section.

        Parameters
        ----------
        section_index : int
            The index of the section to navigate to

        """
        if 0 <= section_index < len(self.sections):
            # Save current section before switching
            self.save_current_section()  # type: ignore[attr-defined]

            # Switch to new section
            self.current_section = section_index
            logger.debug("Navigated to section %d: %s", section_index, self.sections[section_index])

            # Refresh display
            self.refresh_tools()  # type: ignore[attr-defined]
            self.refresh_configuration()  # type: ignore[attr-defined]

    def __navigate_to_previous_section(self) -> None:
        """Navigate to the previous tool section."""
        if self.current_section > 0:
            self.__handle_section_navigation(self.current_section - 1)

    def __navigate_to_next_section(self) -> None:
        """Navigate to the next tool section."""
        if self.current_section < len(self.sections) - 1:
            self.__handle_section_navigation(self.current_section + 1)

    def __select_all_tools(self) -> None:
        """Select all available tools in the current section."""
        try:
            if not self.sections:
                logger.debug("No sections available for select all")
                return

            current_section = self.sections[self.current_section]
            tools = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            # Select all tools
            for tool in tools:
                self.tool_selected[tool] = True
                # Update checkbox if it exists
                try:
                    checkbox = self.query_one(f"#tool_{tool}", Checkbox)  # type: ignore[attr-defined]
                    checkbox.value = True
                except Exception:
                    # Checkbox might not exist
                    pass

            logger.debug("Selected all tools in section %s: %s", current_section, tools)

            # Refresh configuration panel
            self.refresh_configuration()  # type: ignore[attr-defined]

        except Exception as e:
            logger.debug("Could not select all tools: %s", e)

    def __copy_debug_info(self) -> None:
        """Copy debug information to clipboard."""
        try:
            debug_output = self.generate_debug_output()  # type: ignore[attr-defined]
            # In a real implementation, this would copy to clipboard
            logger.debug("Debug info would be copied to clipboard: %s chars", len(debug_output))
        except Exception as e:
            logger.debug("Could not copy debug info: %s", e)

    def __generate_package_urls(self) -> None:
        """Generate package URLs based on current configuration."""
        try:
            # This would generate package URLs and update the display
            logger.debug("Generating package URLs for Python configuration")

            # Example URL generation logic (simplified)
            if self.config.install_python_repository:
                # Generate URLs based on current settings
                base_url = self.config.python_publish_url
                project_name = self.config.python_project_name

                if base_url and project_name:
                    # Create a simple package URL mapping
                    package_urls = {
                        "PyPI": f"https://pypi.org/project/{project_name}/",
                        "Repository": base_url,
                        "Index": self.config.python_index_url,
                    }

                    # Store URL mapping for future use when this feature is implemented

                    # Update the display
                    self.update_python_package_urls()  # type: ignore[attr-defined]

                    logger.debug("Generated package URLs: %s", package_urls)

        except Exception as e:
            logger.debug("Could not generate package URLs: %s", e)

    def __refresh_python_repository_settings(self) -> None:
        """Refresh just the Python repository settings in the left column.

        Updates the Python repository configuration display without rebuilding
        the entire tools interface.

        """
        # Simply refresh the entire tools display, but with better duplicate prevention
        self.refresh_tools()  # type: ignore[attr-defined]

    def __process_input_on_focus_loss(self, input_id: str) -> None:
        """Process specific inputs when they lose focus.

        Parameters
        ----------
        input_id : str
            The ID of the input that lost focus

        """
        try:
            if input_id == "pyproject_homepage":
                # Process homepage URL for username extraction
                homepage_input = self.query_one("#pyproject_homepage", Input)  # type: ignore[attr-defined]
                self.__check_and_propagate_username(homepage_input.value)

            elif input_id == "pyproject_name":
                # Update package-related fields when project name changes
                name_input = self.query_one("#pyproject_name", Input)  # type: ignore[attr-defined]
                self.__update_package_related_fields(name_input.value)

            elif input_id == "github_username":
                # Update URL fields when username changes
                username_input = self.query_one("#github_username", Input)  # type: ignore[attr-defined]
                self.__update_github_related_fields(username_input.value)

        except Exception as e:
            logger.debug("Could not process input on focus loss for %s: %s", input_id, e)

    def __check_and_propagate_username(self, homepage_url: str) -> None:
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
            return

        try:
            # Extract username from GitHub URL
            username = self.__extract_username_from_url(homepage_url)
            if not username:
                return

            # Only propagate once per session to avoid overwriting user edits
            if self._username_propagated:
                logger.debug("Username already propagated this session, skipping")
                return

            logger.debug("Extracted username from homepage URL: %s", username)

            # Update GitHub username field if it's empty or contains template value
            try:
                github_username_input = self.query_one("#github_username", Input)  # type: ignore[attr-defined]
                current_username = github_username_input.value
                if not current_username or current_username == "yourusername":
                    github_username_input.value = username
                    self.config.python_github_username = username
                    logger.debug("Updated GitHub username field: %s", username)
            except Exception:
                # Field might not exist
                pass

            # Update other URL fields with the extracted username
            self.__update_github_related_fields(username)

            # Mark as propagated to prevent future automatic updates
            self._username_propagated = True

        except Exception as e:
            logger.debug("Error in username propagation: %s", e)

    def __update_package_related_fields(self, package_name: str) -> None:
        """Update fields that depend on the package name.

        Parameters
        ----------
        package_name : str
            The new package name

        """
        # Always try to update, even for empty package names (to show defaults)
        logger.debug("Updating package-related fields for package name: %s", package_name)

        try:
            # Update homepage URL if it's still the default
            homepage_input = self.query_one("#pyproject_homepage", Input)  # type: ignore[attr-defined]
            current_homepage = homepage_input.value
            if not current_homepage or "my-awesome-project" in current_homepage:
                new_homepage = self.__get_default_homepage_url()
                homepage_input.value = new_homepage
                self.config.python_homepage_url = new_homepage

            # Update source URL if it exists and is still default
            try:
                source_input = self.query_one("#pyproject_source", Input)  # type: ignore[attr-defined]
                current_source = source_input.value
                if not current_source or "my-awesome-project" in current_source:
                    new_source = self.__get_default_source_url()
                    source_input.value = new_source
                    self.config.python_source_url = new_source
            except Exception:
                # Source field might not exist
                pass

            # Update documentation URL if it exists and is still default
            try:
                docs_input = self.query_one("#pyproject_documentation", Input)  # type: ignore[attr-defined]
                current_docs = docs_input.value
                if not current_docs or "my-awesome-project" in current_docs:
                    new_docs = self.__get_default_documentation_url()
                    docs_input.value = new_docs
                    self.config.python_documentation_url = new_docs
            except Exception:
                # Documentation field might not exist
                pass

            # Update package path if it exists and is still default
            try:
                package_path_input = self.query_one("#pyproject_packages", Input)  # type: ignore[attr-defined]
                current_path = package_path_input.value
                if not current_path or "my_awesome_project" in current_path:
                    new_path = self.__get_default_package_path()
                    package_path_input.value = new_path
                    self.config.python_packages_path = new_path
            except Exception:
                # Package path field might not exist
                pass

        except Exception as e:
            logger.debug("Could not update package-related fields: %s", e)

    def __update_github_related_fields(self, github_username: str) -> None:
        """Update URL fields when GitHub username changes.

        Parameters
        ----------
        github_username : str
            The new GitHub username

        """
        if not github_username or github_username.strip() == "":
            return

        username = github_username.strip()
        logger.debug("Updating URL fields for GitHub username: %s", username)

        try:
            # Update homepage URL if it contains "yourusername"
            homepage_input = self.query_one("#pyproject_homepage", Input)  # type: ignore[attr-defined]
            current_homepage = homepage_input.value
            if "yourusername" in current_homepage:
                new_homepage = current_homepage.replace("yourusername", username)
                homepage_input.value = new_homepage
                self.config.python_homepage_url = new_homepage

            # Update source URL if it exists and contains "yourusername"
            try:
                source_input = self.query_one("#pyproject_source", Input)  # type: ignore[attr-defined]
                current_source = source_input.value
                if "yourusername" in current_source:
                    new_source = current_source.replace("yourusername", username)
                    source_input.value = new_source
                    self.config.python_source_url = new_source
            except Exception:
                # Source field might not exist
                pass

            # Update documentation URL if it exists and contains "yourusername"
            try:
                docs_input = self.query_one("#pyproject_documentation", Input)  # type: ignore[attr-defined]
                current_docs = docs_input.value
                if "yourusername" in current_docs:
                    new_docs = current_docs.replace("yourusername", username)
                    docs_input.value = new_docs
                    self.config.python_documentation_url = new_docs
            except Exception:
                # Documentation field might not exist
                pass

        except Exception as e:
            logger.debug("Could not update GitHub-related fields: %s", e)

    def __extract_username_from_url(self, url: str) -> str:
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
            username = github_match.group(1)
            # Validate username (basic check - no spaces, not empty)
            if username and " " not in username and username != "yourusername":
                return username

        return ""

    def __get_default_homepage_url(self) -> str:
        """Get default homepage URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            return f"https://github.com/yourusername/{package_name}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_source_url(self) -> str:
        """Get default source URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            return f"https://github.com/yourusername/{package_name}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_documentation_url(self) -> str:
        """Get default documentation URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            return f"https://github.com/yourusername/{package_name}/README.md"
        return "https://github.com/yourusername/my-awesome-project/README.md"

    def __get_default_package_path(self) -> str:
        """Get default package path based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            # Convert package name to Python package format (replace dashes with underscores)
            package_dir = package_name.replace("-", "_")
            return f"src/{package_dir}"
        return "src/my_awesome_project"
