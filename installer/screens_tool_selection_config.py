"""Tool selection screen configuration management for the Dynamic Dev Container installer.

This module contains the configuration management functionality of the ToolSelectionScreen class,
including Python project configuration forms, tool version management, and configuration display.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any, cast

from textual import log as logger
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from installer.constants import DEBUG_MODE
from installer.tool_manager import ToolManager

if TYPE_CHECKING:
    from textual.widget import Widget

    from installer.config import ProjectConfig

# Constants for version display
MAX_VERSIONS_TO_SHOW = 10
PREVIEW_VERSIONS_COUNT = 5


class ToolSelectionConfigMixin:
    """Configuration management functionality for the Tool Selection screen.

    This mixin requires the following attributes to be present on the class:
    - config: ProjectConfig
    - query_one: Method from Textual Screen class
    - tool_selected: dict[str, bool]
    - tool_version_configurable: dict[str, bool]
    - tool_version_value: dict[str, str]
    """

    # These attributes should be set by the main class
    config: ProjectConfig
    tool_selected: dict[str, bool]
    tool_version_configurable: dict[str, bool]
    tool_version_value: dict[str, str]
    show_python_config: bool
    show_other_config: dict[str, Any]
    _refreshing_config: bool
    _widget_generation: int
    _active_version_inputs: set[str]
    _username_propagated: bool

    def refresh_configuration(self) -> None:
        """Refresh the configuration panel based on selected tools.

        Updates the configuration panel to show relevant settings for
        currently selected tools, including Python project configuration
        and tool version selections.

        """
        if self._refreshing_config:
            logger.debug("Already refreshing configuration, skipping")
            return

        try:
            self._refreshing_config = True
            logger.debug("Refreshing configuration panel")

            config_container = self.query_one("#config-scroll", ScrollableContainer)  # type: ignore[attr-defined]

            # Clear existing configuration widgets
            config_container.remove_children()

            # Check what tools are selected
            selected_tools = [tool for tool, selected in self.tool_selected.items() if selected]

            if not selected_tools:
                no_config_label = Label("Select tools to see configuration options", classes="config-placeholder")
                config_container.mount(no_config_label)
                return

            # Track widgets we're about to mount
            widgets_to_mount: list[Widget] = []

            # Show Python configuration if Python is selected
            if "python" in selected_tools and self.config.install_python_repository:
                self.__create_python_config_widgets(widgets_to_mount)

            # Show tool version configuration for tools that support it
            self.__create_tool_version_widgets(selected_tools, widgets_to_mount)

            # Mount all widgets at once
            if widgets_to_mount:
                config_container.mount(*widgets_to_mount)
                # Set focus to the first input field if one exists
                self.__focus_first_input(config_container)
            else:
                no_config_label = Label("No configuration needed", classes="config-placeholder")
                config_container.mount(no_config_label)

            # Apply any deferred configuration updates (simplified)
            # Configuration updates will be handled by the main class event handlers

            logger.debug("Configuration panel refresh completed")
        except Exception as e:
            logger.error("Error refreshing configuration: %s", e)
            if DEBUG_MODE:
                logger.debug("Configuration refresh error details: %s", traceback.format_exc())
        finally:
            self._refreshing_config = False

    def __create_python_config_widgets(self, widgets_to_mount: list[Widget]) -> None:
        """Create Python configuration widgets."""
        # Python configuration section header
        widgets_to_mount.append(Label("Python Project Configuration", classes="config-section-title"))

        # Project name input
        project_name_value = self.config.python_project_name or self.config.project_name
        project_name_input = Input(
            value=project_name_value,
            placeholder="Enter project name",
            id="py_project_name",
        )
        widgets_to_mount.extend(
            [
                Label("Project Name:", classes="config-label"),
                project_name_input,
            ],
        )

        # Project description input
        project_desc_input = Input(
            value=self.config.python_project_description,
            placeholder="Enter project description",
            id="py_project_description",
        )
        widgets_to_mount.extend(
            [
                Label("Project Description:", classes="config-label"),
                project_desc_input,
            ],
        )

        # Author name input
        author_name_input = Input(
            value=self.config.python_author_name,
            placeholder="Enter author name",
            id="py_author_name",
        )
        widgets_to_mount.extend(
            [
                Label("Author Name:", classes="config-label"),
                author_name_input,
            ],
        )

        # Author email input
        author_email_input = Input(
            value=self.config.python_author_email,
            placeholder="Enter author email",
            id="py_author_email",
        )
        widgets_to_mount.extend(
            [
                Label("Author Email:", classes="config-label"),
                author_email_input,
            ],
        )

        # License selector
        license_radio_set = RadioSet(
            RadioButton("MIT", value=(self.config.python_license == "MIT"), id="mit_radio"),
            RadioButton("Apache-2.0", value=(self.config.python_license == "Apache-2.0"), id="apache_radio"),
            RadioButton("GPL-3.0", value=(self.config.python_license == "GPL-3.0"), id="gpl_radio"),
            RadioButton("BSD-3-Clause", value=(self.config.python_license == "BSD-3-Clause"), id="bsd_radio"),
            RadioButton("Custom", value=(self.config.python_license == "Custom"), id="custom_radio"),
            id="license_selector",
        )
        widgets_to_mount.extend(
            [
                Label("License:", classes="config-label"),
                license_radio_set,
            ],
        )

        # Custom license input (conditional)
        if self.config.python_license == "Custom":
            custom_license_input = Input(
                value="",  # Custom license text would need a separate field
                placeholder="Enter custom license",
                id="py_custom_license",
            )
            widgets_to_mount.extend(
                [
                    Label("Custom License:", classes="config-label"),
                    custom_license_input,
                ],
            )

        # Publishing configuration
        widgets_to_mount.append(Label("Publishing Configuration", classes="config-section-title"))

        # Repository type radio set
        repo_radio_set = RadioSet(
            RadioButton("PyPI", value=(self.config.python_repository_type == "PyPI"), id="pypi_radio"),
            RadioButton(
                "Artifactory",
                value=(self.config.python_repository_type == "Artifactory"),
                id="artifactory_radio",
            ),
            RadioButton("Other", value=(self.config.python_repository_type == "Other"), id="other_radio"),
            id="repository_type",
        )
        widgets_to_mount.extend(
            [
                Label("Repository Type:", classes="config-label"),
                repo_radio_set,
            ],
        )

        # URL fields (conditional based on repository type)
        if self.config.python_repository_type != "PyPI":
            # Repository URL container
            url_container = Container(id="url_container")

            # Repository URL input (use python_publish_url for this)
            repo_url_input = Input(
                value=self.config.python_publish_url,
                placeholder="Enter repository URL",
                id="py_repo_url",
            )
            url_container.mount(Label("Repository URL:", classes="config-label"))
            url_container.mount(repo_url_input)

            # Index URL input
            index_url_input = Input(
                value=self.config.python_index_url,
                placeholder="Enter index URL",
                id="py_index_url",
            )
            url_container.mount(Label("Index URL:", classes="config-label"))
            url_container.mount(index_url_input)

            widgets_to_mount.append(url_container)

        # Package URL generation button
        self.__create_package_url_widgets(widgets_to_mount)

    def __create_package_url_widgets(self, widgets_to_mount: list[Widget]) -> None:
        """Create package URL generation widgets."""
        # Generate Package URLs button
        generate_urls_btn = Button("Generate Package URLs", id="generate_urls", classes="action-button")
        widgets_to_mount.append(generate_urls_btn)

        # Package URLs display section will be added dynamically when URLs are generated

    def __create_tool_version_widgets(self, selected_tools: list[str], widgets_to_mount: list[Widget]) -> None:
        """Create tool version configuration widgets."""
        version_tools = [tool for tool in selected_tools if self.tool_version_configurable.get(tool, False)]

        if not version_tools:
            return

        # Tool versions section header
        widgets_to_mount.append(Label("Tool Versions", classes="config-section-title"))

        for tool in version_tools:
            # Get available versions for this tool
            try:
                available_versions = ToolManager.get_tool_versions(tool)
                if not available_versions:
                    continue

                # Current version value
                current_version = self.tool_version_value.get(tool, available_versions[0] if available_versions else "")

                # Tool version container
                tool_container = Vertical(
                    Label(f"{tool.title()} Version:", classes="config-label"),
                    classes="tool-version-container",
                )

                # Version input with validation
                version_input = Input(
                    value=current_version,
                    placeholder=f"Enter {tool} version",
                    id=f"version_{tool}",
                    classes="version-input",
                )
                tool_container.mount(version_input)

                # Show available versions as a help text
                if len(available_versions) <= MAX_VERSIONS_TO_SHOW:  # Don't show too many versions
                    versions_text = f"Available: {', '.join(available_versions[:PREVIEW_VERSIONS_COUNT])}"
                    if len(available_versions) > PREVIEW_VERSIONS_COUNT:
                        versions_text += f" ... (+{len(available_versions) - PREVIEW_VERSIONS_COUNT} more)"
                    help_text = Static(versions_text, classes="version-help")
                    tool_container.mount(help_text)

                widgets_to_mount.append(tool_container)

            except Exception as e:
                logger.debug("Could not create version widget for %s: %s", tool, e)

    def __focus_first_input(self, config_container: ScrollableContainer) -> None:
        """Set focus to the first input field in the configuration panel."""
        try:
            # Find the first input field
            inputs = config_container.query("Input")
            if inputs:
                first_input = inputs.first()
                if first_input:
                    cast("Input", first_input).focus()
        except Exception as e:
            logger.debug("Could not set focus to first input: %s", e)

    def update_python_package_urls(self) -> None:
        """Update the display of generated Python package URLs.

        Refreshes the package URLs display section to show the most
        current generated URLs based on the current configuration.
        This would need to be implemented with actual package URL data.

        """
        try:
            # Remove existing package URLs container if it exists
            try:
                existing_container = self.query_one("#package_urls_container")  # type: ignore[attr-defined]
                existing_container.remove()
            except Exception as e:
                logger.debug("Package URLs container doesn't exist: %s", e)

            # Package URL display logic would be implemented here
            # when the actual package URL generation is added to the config

        except Exception as e:
            logger.debug("Could not update package URLs display: %s", e)

    def update_license_custom_field_visibility(self) -> None:
        """Show/hide custom license field based on license selection."""
        try:
            config_container = self.query_one("#config-scroll", ScrollableContainer)  # type: ignore[attr-defined]

            # Check if custom license is selected
            is_custom = self.config.python_license == "Custom"

            # Check if custom license input already exists
            try:
                config_container.query_one("#py_custom_license")
                custom_exists = True
            except Exception:
                custom_exists = False

            if is_custom and not custom_exists:
                # Need to add custom license field
                # Find the license selector and add the field after it
                license_selector = config_container.query_one("#license_selector")
                license_selector.parent.mount_after(
                    Label("Custom License:", classes="config-label"),
                    license_selector,
                )
                license_selector.parent.mount_after(
                    Input(
                        value="",  # Custom license text would need a separate field
                        placeholder="Enter custom license",
                        id="py_custom_license",
                    ),
                    license_selector.parent.children[-1],  # After the label we just added
                )
            elif not is_custom and custom_exists:
                # Need to remove custom license field
                try:
                    custom_input = config_container.query_one("#py_custom_license")
                    custom_label = custom_input.parent.children[
                        list(custom_input.parent.children).index(custom_input) - 1
                    ]
                    if hasattr(custom_label, "renderable") and "Custom License:" in str(custom_label.renderable):
                        custom_label.remove()
                    custom_input.remove()
                except Exception as e:
                    logger.debug("Could not remove custom license field: %s", e)

        except Exception as e:
            logger.debug("Could not update custom license field visibility: %s", e)

    def update_url_fields_visibility(self) -> None:
        """Show/hide URL fields based on repository type selection."""
        try:
            config_container = self.query_one("#config-scroll", ScrollableContainer)  # type: ignore[attr-defined]

            # Check if URL container should be visible
            should_show_urls = self.config.python_repository_type != "PyPI"

            # Check if URL container exists
            try:
                url_container = config_container.query_one("#url_container")
                urls_exist = True
            except Exception:
                urls_exist = False

            if should_show_urls and not urls_exist:
                # Need to add URL fields
                # Find the repository type selector and add fields after it
                repo_selector = config_container.query_one("#repository_type")

                url_container = Container(id="url_container")

                # Repository URL input
                repo_url_input = Input(
                    value=self.config.python_publish_url,
                    placeholder="Enter repository URL",
                    id="py_repo_url",
                )
                url_container.mount(Label("Repository URL:", classes="config-label"))
                url_container.mount(repo_url_input)

                # Index URL input
                index_url_input = Input(
                    value=self.config.python_index_url,
                    placeholder="Enter index URL",
                    id="py_index_url",
                )
                url_container.mount(Label("Index URL:", classes="config-label"))
                url_container.mount(index_url_input)

                repo_selector.parent.mount_after(url_container, repo_selector)

            elif not should_show_urls and urls_exist:
                # Need to remove URL fields
                try:
                    url_container = config_container.query_one("#url_container")
                    url_container.remove()
                except Exception as e:
                    logger.debug("Could not remove URL container: %s", e)

        except Exception as e:
            logger.debug("Could not update URL fields visibility: %s", e)
