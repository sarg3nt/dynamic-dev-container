#!/usr/bin/env python3
# cspell:ignore gitui cmctl jdxcode sles noconfirm, nerdctl, openbao kubectx kubens krew pybuild tcss kubebench distros unvalidated
"""Dynamic Dev Container TUI Setup.

A Python Terminal User Interface (TUI) for installing .devcontainer and other files
into a project directory to use the dev container in a new project.

This is a Python conversion of the original install.sh script with enhanced TUI capabilities.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

# Add missing imports for type checking and protocol
from typing import TYPE_CHECKING, Any, cast

# Import configuration classes
from installer.config import ProjectConfig

# Import constants from our installer library
from installer.constants import (
    DEBUG_MODE,
    DEFAULT_WORKER_COUNT,
    SCREEN_CONFIG,
    SCREEN_EXTENSIONS,
    SCREEN_INSTALL,
    SCREEN_SUMMARY,
    SCREEN_TOOLS,
    SCREEN_WELCOME,
    USER_ITEM_MAX,
    USER_ITEM_MIN,
    USER_SCREEN_MAX,
    USER_SCREEN_MIN,
    VERSION_BUTTON_PARTS,
)

# Import debug utilities
from installer.debug_utils import DebugMixin

# Import dependency management
from installer.dependencies import check_and_install_dependencies
from installer.devcontainer_parser import DevContainerParser

# Import file management utilities
from installer.file_manager import FileManager

# Import logging utilities
from installer.logging_utils import get_logger, setup_logging

# Import parser utilities
from installer.mise_parser import MiseParser

# Import screen classes
from installer.screens_navigation import NavigationScreenBase
from installer.screens_welcome import WelcomeScreen

# Import tool management utilities
from installer.tool_manager import ToolManager

# Import protocol definitions
if TYPE_CHECKING:
    from installer.protocols import DevContainerApp

if TYPE_CHECKING:
    from textual.events import Focus, Key  # type: ignore[import,unused-ignore]
    from textual.timer import Timer  # type: ignore[import,unused-ignore]
    from textual.widget import Widget


# Initialize logger for this module
logger = get_logger(__name__)


# Install dependencies first
check_and_install_dependencies()

# Now import the required packages
try:
    from rich.console import Console
    from textual.app import App, ComposeResult
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
        LoadingIndicator,
        Markdown,
        ProgressBar,
        RadioButton,
        RadioSet,
        Static,
    )
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    sys.exit(1)


class ExtensionSelectionScreen(NavigationScreenBase):
    """Screen for Dev Container Extensions configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig, source_dir: Path) -> None:
        """Initialize the Dev Container Extensions screen.

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

        # Get extension sections from devcontainer.json
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        self.extension_sections = DevContainerParser.parse_extension_sections_with_extensions(devcontainer_file)
        logger.debug("Parsed extension sections: %s", list(self.extension_sections.keys()))
        for section_name, extensions in self.extension_sections.items():
            logger.debug(
                "Section '%s' has %s extensions: %s",
                section_name,
                len(extensions),
                [ext[0] for ext in extensions],
            )

        self.section_names = list(self.extension_sections.keys())

        # Insert PSI Header at its correct position (index 3, which is item 4 for users)
        # This matches the expected order: 0=Github, 1=Markdown, 2=Shell/Bash, 3=PSI Header
        psi_header_index = 3
        if len(self.section_names) >= psi_header_index:
            # Insert PSI Header at index 3
            self.section_names.insert(psi_header_index, "PSI Header")
        else:
            # If fewer than 3 sections, append PSI Header at the end
            self.section_names.append("PSI Header")
        logger.debug("Final section order: %s", self.section_names)

        self.current_section = 0
        self.total_sections = len(self.section_names)
        logger.debug("Total sections: %s", self.total_sections)

    def __sanitize_section_id(self, section_name: str) -> str:
        """Sanitize section name for use in HTML IDs.

        Replaces invalid characters with underscores to create valid HTML/CSS IDs.

        Parameters
        ----------
        section_name : str
            The section name to sanitize

        Returns
        -------
        str
            Sanitized ID string safe for use in HTML/CSS

        """
        return section_name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        # Create the EXACT same structure as ToolSelectionScreen using base class
        current_section_name = self.section_names[self.current_section]

        if current_section_name == "PSI Header":
            # For PSI Header, get components directly to match regular extension structure
            title_label, main_layout = self.__create_psi_header_components()

            main_content = Container(
                title_label,
                main_layout,
                # Extension navigation links - using base class method
                self.create_navigation_links_container("extension-links", populate_immediately=True),
                # Use direct button creation like ToolSelectionScreen instead of _create_button_row()
                Horizontal(
                    Button("<< Tool Selection", id="back_btn", classes="nav-button"),
                    Button("Previous Extension", id="prev_section_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Extension",
                        id="next_section_btn",
                        disabled=self.current_section >= self.total_sections - 1,
                    ),
                    Button("Summary >>", id="next_btn", variant="primary", classes="nav-button"),
                    id="button-row",
                ),
                id="main-content",
            )
        else:
            # For extension sections, build structure EXACTLY like ToolSelectionScreen
            extensions = self.extension_sections.get(current_section_name, [])
            section_index = self.current_section + 1
            section_enabled = self.config.selected_extension_sections.get(current_section_name, False)

            # Create checkboxes for extensions in this section
            extension_checkboxes = []
            for extension_id, description in extensions:
                checkbox_id = f"ext_{extension_id.replace('.', '_').replace('-', '_')}"
                is_selected = self.config.selected_extensions.get(extension_id, True)
                # Hide extension checkboxes when section is disabled
                checkbox_classes = "compact"
                if not section_enabled:
                    checkbox_classes += " hidden"
                extension_checkboxes.append(
                    Checkbox(
                        f"{description} ({extension_id})",
                        id=checkbox_id,
                        value=is_selected,
                        classes=checkbox_classes,
                    ),
                )

            section_id = self.__sanitize_section_id(current_section_name)

            main_content = Container(
                Label(f"Dev Container Extensions - {current_section_name}", classes="title"),
                Horizontal(
                    # Left column for extension selection
                    Container(
                        Label("Available Extensions:", classes="column-title"),
                        ScrollableContainer(
                            Checkbox(
                                f"Install {current_section_name} Extensions",
                                id=f"install_{section_id}",
                                value=section_enabled,
                                classes="compact",
                            ),
                            *extension_checkboxes,
                            id="extension-scroll",
                            classes="tools-list",
                        ),
                        id="extension-column",
                        classes="left-column",
                    ),
                    # Right column for configuration
                    Container(
                        Label("Configuration:", classes="column-title"),
                        ScrollableContainer(
                            Label(f"Section {section_index} of {self.total_sections}", classes="compact"),
                            Label(f"Configure {current_section_name} extensions:", classes="compact"),
                            Label("Select extensions to include in your development environment.", classes="compact"),
                            id="config-scroll",
                            classes="config-area",
                        ),
                        id="config-column",
                        classes="right-column",
                    ),
                    id="main-layout",
                ),
                # Extension navigation links - using base class method
                self.create_navigation_links_container("extension-links", populate_immediately=True),
                # Use direct button creation like ToolSelectionScreen instead of _create_button_row()
                Horizontal(
                    Button("<< Tool Selection", id="back_btn", classes="nav-button"),
                    Button("Previous Extension", id="prev_section_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Extension",
                        id="next_section_btn",
                        disabled=self.current_section >= self.total_sections - 1,
                    ),
                    Button("Summary >>", id="next_btn", variant="primary", classes="nav-button"),
                    id="button-row",
                ),
                id="main-content",
            )

        # Use base class method for layout creation - use SAME container ID as tools for identical styling
        yield from self.create_navigation_layout(main_content, "tools-container")

    def __create_psi_header_components(self) -> tuple[Label, Horizontal]:
        """Create the PSI Header configuration components (not wrapped in Container).

        Returns
        -------
        tuple[Label, Horizontal]
            Title label and main layout components

        """
        logger.debug("Creating PSI Header configuration components")

        # Get available languages from devcontainer.json template
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        available_languages = DevContainerParser.parse_psi_header_languages(devcontainer_file)
        logger.debug("Available PSI Header languages: %s", available_languages)

        # Determine which languages should be auto-selected based on selected tools
        auto_selected_languages = self.__get_auto_selected_languages()
        logger.debug("Auto-selected PSI Header languages: %s", auto_selected_languages)

        # Create language checkboxes
        language_checkboxes = self.__create_language_checkboxes(available_languages, auto_selected_languages)
        logger.debug("Created %s language checkboxes", len(language_checkboxes))

        title_label = Label(
            f"Dev Container Extensions - PSI Header Configuration - Section {self.current_section + 1} of {self.total_sections}",
            classes="title",
        )

        # Apply visibility logic for PSI Header config items
        config_classes = "compact"
        config_input_classes = "compact-input"
        if not self.config.install_psi_header:
            config_classes += " hidden"
            config_input_classes += " hidden"

        # Apply hidden class to language checkboxes if PSI Header is disabled
        if not self.config.install_psi_header:
            for checkbox in language_checkboxes:
                checkbox.add_class("hidden")

        # Create informational text (visible when PSI Header is disabled)
        info_classes = "compact"
        if self.config.install_psi_header:
            info_classes += " hidden"

        main_layout = Horizontal(
            # Left column for extension selection (matching ToolSelectionScreen structure)
            Container(
                Label("Extension Installation:", classes="column-title"),
                ScrollableContainer(
                    Checkbox(
                        "Install PSI Header Extension",
                        id="install_psi",
                        value=self.config.install_psi_header,
                        classes="compact",
                    ),
                    id="extension-scroll",
                    classes="tools-list",
                ),
                id="extension-column",
                classes="left-column",
            ),
            # Right column for configuration (matching ToolSelectionScreen structure)
            Container(
                Label("Configuration:", classes="column-title"),
                ScrollableContainer(
                    # Informational text (shown when PSI Header is disabled)
                    Label(
                        f"Section {self.current_section + 1} of {self.total_sections}",
                        classes=info_classes,
                        id="psi_info_section",
                    ),
                    Label("Configure PSI Header extension:", classes=info_classes, id="psi_info_configure"),
                    Label(
                        "Select extensions to include in your development environment.",
                        classes=info_classes,
                        id="psi_info_select",
                    ),
                    # Actual configuration (shown when PSI Header is enabled)
                    Label("Company Name:", classes=config_classes),
                    Input(
                        placeholder="Your Company Name",
                        id="company_name",
                        value=self.config.psi_header_company,
                        classes=config_input_classes,
                    ),
                    Label("Language Templates:", classes=config_classes),
                    Label(
                        "Select languages for custom headers (auto-selected based on your tools):",
                        classes=config_classes,
                    ),
                    *language_checkboxes,
                    id="config-scroll",
                    classes="config-area",
                ),
                id="config-column",
                classes="right-column",
            ),
            id="main-layout",
        )

        return title_label, main_layout

    def __create_extension_section_content(self, section_name: str) -> Container:
        """Create content for a specific extension section."""
        logger.debug("Creating extension section content for: %s", section_name)
        extensions = self.extension_sections.get(section_name, [])
        logger.debug("Found %s extensions for section %s: %s", len(extensions), section_name, extensions)
        section_index = self.current_section + 1

        # Check if this section should be enabled by default
        section_enabled = self.config.selected_extension_sections.get(section_name, False)  # Default to disabled
        logger.debug("Section %s enabled: %s", section_name, section_enabled)

        # Create checkboxes for extensions in this section
        extension_checkboxes = []
        for extension_id, description in extensions:
            checkbox_id = f"ext_{extension_id.replace('.', '_').replace('-', '_')}"
            # Extensions are selected by default when section is enabled, but hidden when section is disabled
            is_selected = self.config.selected_extensions.get(extension_id, True)
            # Hide extension checkboxes when section is disabled
            checkbox_classes = "compact"
            if not section_enabled:
                checkbox_classes += " hidden"
            extension_checkboxes.append(
                Checkbox(
                    f"{description} ({extension_id})",
                    id=checkbox_id,
                    value=is_selected,
                    classes=checkbox_classes,
                ),
            )
            logger.debug("Created checkbox for extension: %s", extension_id)

        # Sanitize section name for use in HTML IDs (replace invalid characters)
        section_id = self.__sanitize_section_id(section_name)

        # Create the exact same structure as ToolSelectionScreen
        container = Container(
            Label(f"Dev Container Extensions - {section_name}", classes="title"),
            Horizontal(
                # Left column for extension selection (matching ToolSelectionScreen structure)
                Container(
                    Label("Available Extensions:", classes="column-title"),
                    ScrollableContainer(
                        Checkbox(
                            f"Install {section_name} Extensions",
                            id=f"install_{section_id}",
                            value=section_enabled,
                            classes="compact",
                        ),
                        *extension_checkboxes,
                        id="extension-scroll",
                        classes="tools-list",
                    ),
                    id="extension-column",
                    classes="left-column",
                ),
                # Right column for configuration (matching ToolSelectionScreen structure)
                Container(
                    Label("Configuration:", classes="column-title"),
                    ScrollableContainer(
                        Label(f"Section {section_index} of {self.total_sections}", classes="compact"),
                        Label(f"Configure {section_name} extensions:", classes="compact"),
                        Label("Select extensions to include in your development environment.", classes="compact"),
                        id="config-scroll",
                        classes="config-area",
                    ),
                    id="config-column",
                    classes="right-column",
                ),
                id="main-layout",
            ),
        )

        logger.debug("Creating container for section %s with %s checkboxes", section_name, len(extension_checkboxes))
        return container

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("ExtensionSelectionScreen mounted - Debug functionality available (Ctrl+D)")

        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus to the first relevant input based on current section
        try:
            if self.current_section == 0:  # PSI Header section
                self.query_one("#install_psi", Checkbox).focus()
            else:
                # Focus on section install checkbox for extension sections
                section_name = self.section_names[self.current_section]
                section_id = f"install_{self.__sanitize_section_id(section_name)}"
                self.query_one(f"#{section_id}", Checkbox).focus()
        except Exception:
            logger.debug("Could not set focus to first checkbox")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next_btn":
            self.save_config()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "next_section_btn":
            self.save_current_section()
            self.next_section()
        elif event.button.id == "prev_section_btn":
            self.save_current_section()
            self.previous_section()
        elif event.button.id == "copy_debug_btn":
            self.__copy_debug_output()
        # Handle extension link clicks
        elif event.button.id and event.button.id.startswith("extension_link_"):
            # Extract section index from button ID: "extension_link_{index}"
            try:
                section_index = int(event.button.id.split("_")[-1])
                logger.debug(
                    "EXTENSION CLICK DEBUG: button_id=%s, section_index=%d, current_section=%d",
                    event.button.id,
                    section_index,
                    self.current_section,
                )
                if 0 <= section_index < len(self.section_names) and section_index != self.current_section:
                    section_name = self.section_names[section_index]
                    logger.debug(
                        "EXTENSION CLICK DEBUG: Switching from section %d (%s) to section %d (%s)",
                        self.current_section,
                        self.section_names[self.current_section],
                        section_index,
                        section_name,
                    )
                    self.save_current_section()
                    self.current_section = section_index
                    self.__refresh_content()
                    # Navigation links will be refreshed automatically in _complete_content_refresh
                else:
                    logger.debug("EXTENSION CLICK DEBUG: No section switch needed (same section or invalid index)")
            except (ValueError, IndexError) as e:
                logger.debug("Invalid extension link button ID '%s': %s", event.button.id, e)
            return

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox change events."""
        checkbox_id = event.checkbox.id or ""
        logger.debug("Checkbox changed: %s = %s", checkbox_id, event.checkbox.value)

        # Handle PSI Header install checkbox
        if checkbox_id == "install_psi":
            logger.debug("PSI Header install checkbox changed to: %s", event.checkbox.value)
            self.__toggle_psi_config_visibility(event.checkbox.value)
            # Save the configuration immediately
            self.save_current_section()
            return

        # Handle section install checkbox changes
        if checkbox_id.startswith("install_") and checkbox_id != "install_psi":
            section_name = self.section_names[self.current_section]
            expected_id = f"install_{self.__sanitize_section_id(section_name)}"

            if checkbox_id == expected_id:
                self.__toggle_extension_visibility(event.checkbox.value, section_name)
                # Save the current section immediately to update config
                self.save_current_section()

    def __toggle_extension_visibility(self, show_extensions: bool, section_name: str) -> None:
        """Show or hide extension checkboxes based on section checkbox state."""
        try:
            # Toggle visibility and state of individual extension checkboxes
            extensions = self.extension_sections.get(section_name, [])
            for extension_id, _description in extensions:
                checkbox_id = f"ext_{extension_id.replace('.', '_').replace('-', '_')}"
                try:
                    checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                    if show_extensions:
                        # When enabling, show checkbox and check it by default
                        checkbox.remove_class("hidden")
                        checkbox.value = True
                        self.config.selected_extensions[extension_id] = True
                    else:
                        # When disabling, hide checkbox and uncheck it
                        checkbox.add_class("hidden")
                        checkbox.value = False
                        self.config.selected_extensions[extension_id] = False
                except NoMatches:
                    continue

        except Exception as e:
            logger.debug("Error toggling extension visibility: %s", e)

    def __toggle_psi_config_visibility(self, show_config: bool) -> None:
        """Show or hide PSI Header configuration options based on checkbox state.

        Parameters
        ----------
        show_config : bool
            Whether to show or hide the PSI Header configuration options

        """
        try:
            # Toggle informational text (opposite of config)
            info_items = ["#psi_info_section", "#psi_info_configure", "#psi_info_select"]
            for item_id in info_items:
                try:
                    item = self.query_one(item_id)
                    if show_config:
                        item.add_class("hidden")  # Hide info when showing config
                    else:
                        item.remove_class("hidden")  # Show info when hiding config
                except NoMatches:
                    continue

            # Toggle individual config items
            config_items = [
                "#company_name",  # Input field
            ]

            # Toggle config labels and input
            for item_id in config_items:
                try:
                    item = self.query_one(item_id)
                    if show_config:
                        item.remove_class("hidden")
                    else:
                        item.add_class("hidden")
                except NoMatches:
                    continue

            # Toggle all labels with "compact" class in the config scroll area (except info labels)
            try:
                config_scroll = self.query_one("#config-scroll")
                for label in config_scroll.query("Label.compact"):
                    # Skip the informational labels
                    if label.id and label.id.startswith("psi_info_"):
                        continue
                    if show_config:
                        label.remove_class("hidden")
                    else:
                        label.add_class("hidden")
            except NoMatches:
                pass

            # Toggle language checkboxes
            try:
                config_scroll = self.query_one("#config-scroll")
                for checkbox in config_scroll.query("Checkbox"):
                    # Skip the main install checkbox
                    if checkbox.id != "install_psi":
                        if show_config:
                            checkbox.remove_class("hidden")
                        else:
                            checkbox.add_class("hidden")
            except NoMatches:
                pass

        except NoMatches:
            logger.debug("PSI config container not found")

    def save_current_section(self) -> None:
        """Save the configuration for the current section."""
        current_section_name = self.section_names[self.current_section]

        if current_section_name == "PSI Header":
            self.__save_psi_header_config()
        else:
            self.__save_extension_section_config(current_section_name)

    def __save_psi_header_config(self) -> None:
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

    def __save_extension_section_config(self, section_name: str) -> None:
        """Save configuration for an extension section."""
        # Save section enabled/disabled state
        section_id = f"install_{self.__sanitize_section_id(section_name)}"
        try:
            section_checkbox = self.query_one(f"#{section_id}", Checkbox)
            self.config.selected_extension_sections[section_name] = section_checkbox.value
        except NoMatches:
            self.config.selected_extension_sections[section_name] = True

        # Save individual extension selections
        extensions = self.extension_sections.get(section_name, [])
        for extension_id, _description in extensions:
            checkbox_id = f"ext_{extension_id.replace('.', '_').replace('-', '_')}"
            try:
                checkbox = self.query_one(f"#{checkbox_id}", Checkbox)
                self.config.selected_extensions[extension_id] = checkbox.value
            except NoMatches:
                self.config.selected_extensions[extension_id] = True

    def next_section(self) -> None:
        """Move to the next section."""
        if self.current_section < self.total_sections - 1:
            self.current_section += 1
            self.__refresh_content()

    def previous_section(self) -> None:
        """Move to the previous section."""
        if self.current_section > 0:
            self.current_section -= 1
            self.__refresh_content()

    def __refresh_content(self) -> None:
        """Refresh the content for the current section."""
        logger.debug("Refreshing content for section %s", self.current_section)

        # Find the existing main-content container and replace its contents - EXACTLY like ToolSelectionScreen
        main_container = self.query_one("#main-content")
        logger.debug("Found main-content container, removing children")

        # Remove all children from the container
        main_container.remove_children()

        # Wait for the removal to complete
        self.call_after_refresh(self.__mount_fresh_content)

    def __mount_fresh_content(self) -> None:
        """Mount fresh content after removal is complete - EXACTLY like compose method."""
        main_container = self.query_one("#main-content")

        # Remove all children from the main-content container - FORCE COMPLETE REMOVAL
        main_container.remove_children()

        # Use call_later instead of call_after_refresh to ensure callback is executed
        self.call_later(self.__complete_content_refresh)

    def __complete_content_refresh(self) -> None:
        """Complete the content refresh after removal is done."""
        main_container = self.query_one("#main-content")

        # Verify container is actually empty
        existing_children = main_container.children
        if existing_children:
            logger.debug(
                "WARNING: Container still has %d children after removal: %s",
                len(existing_children),
                [child.id for child in existing_children],
            )
            # Force remove any remaining children
            for child in list(existing_children):
                try:
                    child.remove()
                except Exception as e:
                    logger.debug("Error removing child %s: %s", child.id, e)

        # Recreate the EXACT same structure as compose method
        current_section_name = self.section_names[self.current_section]

        if current_section_name == "PSI Header":
            # For PSI Header, get components directly to match regular extension structure
            title_label, main_layout = self.__create_psi_header_components()

            # Create structure EXACTLY like regular extensions (no extra Container wrapper)
            content_widget = Container(
                title_label,
                main_layout,
                # Extension navigation links - create with immediate population
                self.create_navigation_links_container("extension-links", populate_immediately=True),
                # Use direct button creation like ToolSelectionScreen
                Horizontal(
                    Button("<< Tool Selection", id="back_btn", classes="nav-button"),
                    Button("Previous Extension", id="prev_section_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Extension",
                        id="next_section_btn",
                        disabled=self.current_section >= self.total_sections - 1,
                    ),
                    Button("Summary >>", id="next_btn", variant="primary", classes="nav-button"),
                    id="button-row",
                ),
            )
            main_container.mount(content_widget)
        else:
            # For extension sections, build structure EXACTLY like compose method
            extensions = self.extension_sections.get(current_section_name, [])
            section_index = self.current_section + 1
            section_enabled = self.config.selected_extension_sections.get(current_section_name, False)

            # Create checkboxes for extensions in this section
            extension_checkboxes = []
            for extension_id, description in extensions:
                checkbox_id = f"ext_{extension_id.replace('.', '_').replace('-', '_')}"
                is_selected = self.config.selected_extensions.get(extension_id, True)
                # Hide extension checkboxes when section is disabled
                checkbox_classes = "compact"
                if not section_enabled:
                    checkbox_classes += " hidden"
                extension_checkboxes.append(
                    Checkbox(
                        f"{description} ({extension_id})",
                        id=checkbox_id,
                        value=is_selected,
                        classes=checkbox_classes,
                    ),
                )

            section_id = self.__sanitize_section_id(current_section_name)

            # Create the full layout structure - same as compose method
            content_widget = Container(
                Label(f"Dev Container Extensions - {current_section_name}", classes="title"),
                Horizontal(
                    # Left column for extension selection
                    Container(
                        Label("Available Extensions:", classes="column-title"),
                        ScrollableContainer(
                            Checkbox(
                                f"Install {current_section_name} Extensions",
                                id=f"install_{section_id}",
                                value=section_enabled,
                                classes="compact",
                            ),
                            *extension_checkboxes,
                            id="extension-scroll",
                            classes="tools-list",
                        ),
                        id="extension-column",
                        classes="left-column",
                    ),
                    # Right column for configuration
                    Container(
                        Label("Configuration:", classes="column-title"),
                        ScrollableContainer(
                            Label(f"Section {section_index} of {self.total_sections}", classes="compact"),
                            Label(f"Configure {current_section_name} extensions:", classes="compact"),
                            Label(
                                "Select extensions to include in your development environment.",
                                classes="compact",
                            ),
                            id="config-scroll",
                            classes="config-area",
                        ),
                        id="config-column",
                        classes="right-column",
                    ),
                    id="main-layout",
                ),
                # Extension navigation links - create with immediate population
                self.create_navigation_links_container("extension-links", populate_immediately=True),
                # Use direct button creation like ToolSelectionScreen
                Horizontal(
                    Button("<< Tool Selection", id="back_btn", classes="nav-button"),
                    Button("Previous Extension", id="prev_section_btn", disabled=self.current_section == 0),
                    Button(
                        "Next Extension",
                        id="next_section_btn",
                        disabled=self.current_section >= self.total_sections - 1,
                    ),
                    Button("Summary >>", id="next_btn", variant="primary", classes="nav-button"),
                    id="button-row",
                ),
            )
            main_container.mount(content_widget)

        # Navigation links are already populated during container creation
        logger.debug("Content refresh completed successfully")

    def __show_error_screen(self, error_message: str) -> None:
        """Show an error screen when all else fails."""
        logger.debug("Showing error screen: %s", error_message)
        try:
            # Create a simple error container
            error_container = Container(
                Label("Extension Configuration Error", classes="title"),
                Label(f"Section: {self.current_section + 1} of {self.total_sections}"),
                Label(f"Error: {error_message}"),
                Label("Please try navigating to a different section or restart the application."),
                Horizontal(
                    Button("<< Tool Selection", id="back_btn", classes="nav-button"),
                    Button("Summary >>", id="next_btn", variant="primary", classes="nav-button"),
                    id="button-row",
                ),
                id="tools-container",
            )

            # Try to mount the error container
            self.mount(error_container)
        except Exception as mount_error:
            logger.debug("Even error screen failed to mount: %s", mount_error)

    def save_config(self) -> None:
        """Save Dev Container Extensions configuration."""
        # Save current section first
        self.save_current_section()

        # Continue to next screen
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_extensions)
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

        Navigates back to the tool selection screen in the configuration workflow.

        """
        # Navigate back to tool selection screen
        self.app.pop_screen()
        self.app.show_tool_selection()  # type: ignore[attr-defined]

    def action_toggle_debug(self) -> None:
        """Toggle debug panel visibility.

        Shows or hides the debug output panel for viewing captured log messages.
        If the panel exists, it is removed. If it doesn't exist, it is created.

        """
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self.__rebuild_with_debug_panel()

    def __get_auto_selected_languages(self) -> set[str]:
        """Get languages that should be auto-selected based on selected tools.

        Analyzes the selected development tools and returns a set of language
        identifiers that should be automatically selected for PSI Header templates.

        Returns
        -------
        set[str]
            Set of language identifiers to auto-select (e.g., 'python', 'go', 'javascript')

        """
        auto_selected = set()

        # Get language mappings from .mise.toml comments
        tool_language_mapping = self.__get_tool_language_mapping()

        # Map selected tools to their corresponding languages
        for tool_name, is_selected in self.config.tool_selected.items():
            if is_selected and tool_name in tool_language_mapping:
                language = tool_language_mapping[tool_name]
                auto_selected.add(language)

        # Map selected extension sections to their corresponding PSI header languages
        extension_language_mapping = {
            "Markdown": "markdown",
            "Shell/Bash": "shellscript",
        }

        for section_name, is_selected in self.config.selected_extension_sections.items():
            if is_selected and section_name in extension_language_mapping:
                language = extension_language_mapping[section_name]
                auto_selected.add(language)

        logger.debug("Auto-selected languages for PSI Header: %s", auto_selected)
        return auto_selected

    def __create_language_checkboxes(
        self,
        available_languages: list[tuple[str, str]],
        auto_selected_languages: set[str],
    ) -> list[Checkbox]:
        """Create checkboxes for PSI header language selection.

        Parameters
        ----------
        available_languages : list[tuple[str, str]]
            List of (language_id, display_name) tuples for available languages
        auto_selected_languages : set[str]
            Set of language IDs that should be pre-selected

        Returns
        -------
        list[Checkbox]
            List of checkbox widgets for language selection

        """
        checkboxes = []

        for lang_id, display_name in available_languages:
            # Check if this language is already configured
            is_configured = any(template_lang_id == lang_id for template_lang_id, _ in self.config.psi_header_templates)

            # Auto-select if it's in the auto-selected set or already configured
            is_selected = lang_id in auto_selected_languages or is_configured

            checkbox_id = f"lang_{lang_id}"

            # Create the checkbox
            checkbox = Checkbox(display_name, id=checkbox_id, value=is_selected, classes="compact")
            checkboxes.append(checkbox)

        return checkboxes

    def __get_tool_language_mapping(self) -> dict[str, str]:
        """Get mapping of tools to their primary programming languages.

        Reads the .mise.toml file and extracts language mappings from #language: comments.
        Falls back to hardcoded mappings for common tools without language comments.

        Returns
        -------
        dict[str, str]
            Dictionary mapping tool names to language identifiers

        """
        mapping = {}

        # Read language mappings from .mise.toml comments
        mise_file = self.source_dir / ".mise.toml"
        if mise_file.exists():
            with open(mise_file, encoding="utf-8") as f:
                content = f.read()

            for line in content.split("\n"):
                # Look for lines with tool definitions and language comments
                # Expected format: tool_name = 'version' # description #language:language_name
                if "=" in line and "#language:" in line:
                    # Extract tool name (before the =)
                    tool_part = line.split("=")[0].strip()
                    if tool_part and not tool_part.startswith("#"):
                        # Extract language from #language: comment
                        language_match = re.search(r"#language:(\w+)", line)
                        if language_match:
                            language = language_match.group(1)
                            mapping[tool_part] = language

        # Add fallback mappings for common tools that might not have language comments
        fallback_mapping = {
            "python": "python",
            "node": "javascript",
            "go": "go",
            "rust": "rust",
            "java": "java",
            "dotnet": "csharp",
        }

        # Use fallback only if not already mapped from comments
        for tool, language in fallback_mapping.items():
            if tool not in mapping:
                mapping[tool] = language

        logger.debug("Tool language mapping: %s", mapping)
        return mapping


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


class ProjectConfigScreen(Screen[None], DebugMixin):
    """Screen for project configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
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
                id="project-scroll",
            ),
            Horizontal(
                Button("<< Welcome", id="back_btn", classes="nav-button"),
                Button("Tool Selection >>", id="next_btn", classes="nav-button"),
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
            self.__copy_debug_output()

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

        Navigates back to the welcome screen.

        """
        self.app.push_screen(WelcomeScreen())

    def action_toggle_debug(self) -> None:
        """Toggle debug panel visibility.

        Shows or hides the debug output panel for viewing captured log messages.
        If the panel exists, it is removed. If it doesn't exist, it is created.

        """
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self.__rebuild_with_debug_panel()

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
        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_project_config)
        self.app.pop_screen()


class ToolSelectionScreen(NavigationScreenBase):
    """Screen for selecting development tools."""

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
        """Called when the screen is mounted."""
        logger.debug("ToolSelectionScreen mounted - Debug functionality available (Ctrl+D)")

        # Check if background loading is complete
        if not ToolManager.is_loading_complete():
            self.__show_loading_screen()
        else:
            self.__show_tools_screen()

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
        try:
            tools_header = self.query_one("#tools-header", Horizontal)
            current_widgets = list(tools_header.children)

            # Check if Select All button currently exists
            has_select_all_btn = any(
                hasattr(widget, "id") and widget.id == "select_all_tools" for widget in current_widgets
            )

            should_have_select_all = len(tools) > 1

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

        # Update configuration panel
        self.refresh_configuration()

        # Set focus to first tool if we rebuilt the tools
        if needs_rebuild and tools:
            try:
                first_tool = tools[0]
                first_checkbox = self.query_one(f"#tool_{first_tool}", Checkbox)
                first_checkbox.focus()
            except Exception:
                logger.debug("Could not set focus to first tool checkbox in refresh_tools")

    def __create_version_buttons(
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
        parent_container : Container
            The container to mount the buttons to
        version_limit : int | None
            Maximum number of versions to show, None for all

        """
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

    def __refresh_python_repository_settings(self) -> None:
        """Refresh just the Python repository settings in the left column.

        Updates the Python repository configuration display without rebuilding
        the entire tools interface.

        """
        # Simply refresh the entire tools display, but with better duplicate prevention
        self.refresh_tools()

    def refresh_configuration(self) -> None:
        """Refresh the configuration panel based on selected tools.

        Updates the right-side configuration panel to show relevant settings
        for the currently selected tools, preventing concurrent refresh calls.

        """
        # Prevent concurrent calls
        if self._refreshing_config:
            return

        self._refreshing_config = True

        try:
            # Increment generation counter to make IDs unique
            self._widget_generation += 1
            # Clear active version inputs tracking
            self._active_version_inputs.clear()

            config_container = self.query_one("#config-scroll", ScrollableContainer)

            # Clear all children first - this ensures no duplicate IDs
            config_container.remove_children()

            # Force a refresh cycle to ensure widgets are completely removed
            self.call_after_refresh(self.__complete_refresh_configuration)
        except Exception as e:
            logger.error("Error in refresh_configuration: %s", e)
            self._refreshing_config = False

    def __complete_refresh_configuration(self) -> None:
        """Complete the configuration refresh after widgets are cleared."""
        try:
            config_container = self.query_one("#config-scroll", ScrollableContainer)

            # Check which tools are selected and need configuration
            if not self.sections:
                config_container.mount(Label("No tools available", classes="compact muted"))
                return

            current_section = self.sections[self.current_section]
            tools_in_current_section = MiseParser.get_section_tools(Path(".mise.toml"), current_section)

            # Only show tools that are BOTH selected AND in the current section
            selected_tools_in_section = [
                tool for tool in tools_in_current_section if self.tool_selected.get(tool, False)
            ]

            # Also show summary of ALL selected tools across all sections
            all_selected_tools = [tool for tool, selected in self.tool_selected.items() if selected]

            if not selected_tools_in_section and not all_selected_tools:
                config_container.mount(Label("Select tools to see configuration options", classes="compact muted"))
                return

            # Show current section configuration first
            if selected_tools_in_section and "python" in selected_tools_in_section:
                # Python version configuration (moved to top)
                config_container.mount(Label("Python Version:", classes="compact section-header"))
                python_version = self.tool_version_value.get("python", "latest")

                # Create a horizontal container for Python version
                python_version_container = Horizontal(classes="tool-version-row")
                config_container.mount(python_version_container)

                # Tool name label
                python_version_container.mount(Label("python:", classes="compact tool-label"))

                # Version buttons for Python
                self.__create_version_buttons("python", python_version_container, 4)

                # Version input field
                version_id = f"version_python_gen_{self._widget_generation}"
                self._active_version_inputs.add(version_id)
                config_container.mount(
                    Input(
                        value=python_version,
                        placeholder="version or 'latest'",
                        id=version_id,
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
                            id="pyproject_name",
                            classes="compact-input",
                        ),
                    )

                    # Project description
                    config_container.mount(Label("Description:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_project_description or "A brief description of your project",
                            placeholder="Enter project description",
                            id="pyproject_description",
                            classes="compact-input",
                        ),
                    )

                    # Required Python version
                    config_container.mount(Label("Required Python Version:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_requires_python or ">=3.12",
                            placeholder="e.g., >=3.12",
                            id="pyproject_requires_python",
                            classes="compact-input",
                        ),
                    )

                    # Author name
                    config_container.mount(Label("Author Name:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_author_name or "Your Name",
                            placeholder="Enter author name",
                            id="pyproject_author_name",
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
                            value=self.config.python_homepage_url or self.__get_default_homepage_url(),
                            placeholder="Enter homepage URL",
                            id="pyproject_homepage",
                            classes="compact-input",
                        ),
                    )

                    # Source URL
                    config_container.mount(Label("Source URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_source_url or self.__get_default_source_url(),
                            placeholder="Enter source repository URL",
                            id="pyproject_source",
                            classes="compact-input",
                        ),
                    )

                    # Documentation URL
                    config_container.mount(Label("Documentation URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_documentation_url or self.__get_default_documentation_url(),
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
                            value=self.config.python_packages_path or self.__get_default_package_path(),
                            placeholder="Enter package path (e.g., src/package_name)",
                            id="pyproject_packages",
                            classes="compact-input",
                        ),
                    )

                    # Repository publishing section
                    config_container.mount(Label("Repository Publishing:", classes="compact subsection-header"))

                    # Repository type selection (improved order: Type -> Index URL -> Publish URL)
                    config_container.mount(Label("Repository Type:", classes="compact"))
                    current_repo_type = self.config.python_repository_type or "PyPI"
                    python_repo_container = Container(
                        RadioSet(
                            RadioButton(
                                "PyPI",
                                id="py_repo_pypi",
                                value=(current_repo_type == "PyPI"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Artifactory",
                                id="py_repo_artifactory",
                                value=(current_repo_type == "Artifactory"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Nexus",
                                id="py_repo_nexus",
                                value=(current_repo_type == "Nexus"),
                                classes="compact",
                            ),
                            RadioButton(
                                "Custom",
                                id="py_repo_custom",
                                value=(current_repo_type == "Custom"),
                                classes="compact",
                            ),
                            id="py_repo_radioset",
                        ),
                        classes="compact-group",
                    )
                    config_container.mount(python_repo_container)

                    # Package index URL (moved up to be right after Repository Type)
                    config_container.mount(Label("Package Index URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_index_url or "https://pypi.org/simple/",
                            placeholder="Enter package index URL",
                            id="pyproject_index_url",
                            classes="compact-input",
                        ),
                    )

                    # Publish URL (moved down to be after Index URL)
                    config_container.mount(Label("Publish URL:", classes="compact"))
                    config_container.mount(
                        Input(
                            value=self.config.python_publish_url or "https://upload.pypi.org/legacy/",
                            placeholder="Enter publish URL",
                            id="py_publish_url",
                            classes="compact-input",
                        ),
                    )

            # Clean up any existing version inputs before creating new ones
            self.__cleanup_version_inputs()

            # Show version configuration ONLY for configurable tools selected in the CURRENT section
            # (not all sections) to keep the interface section-specific
            # Exclude Python since it's handled separately above
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

                    # Mount the tool version container to config FIRST
                    config_container.mount(tool_version_container)

                    # Now mount child widgets to the mounted container
                    # Tool name label
                    tool_version_container.mount(Label(f"{tool}:", classes="compact tool-label"))

                    # Version buttons - get available versions for this tool dynamically
                    self.__create_version_buttons(tool, tool_version_container)

                    # Use generation-based ID to ensure uniqueness
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    self._active_version_inputs.add(version_id)
                    config_container.mount(
                        Input(
                            value=current_version,
                            placeholder="version or 'latest'",
                            id=version_id,
                            classes="version-input",
                        ),
                    )  # Show summary of ALL selected tools across sections

        except Exception as e:
            logger.error("Error in _complete_refresh_configuration: %s", e)
        finally:
            self._refreshing_config = False

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
            tool = event.checkbox.id[5:]  # Remove "tool_" prefix
            self.tool_selected[tool] = event.value

            # If Python tool was toggled, refresh tools display to show/hide repository config
            if tool == "python":
                self.refresh_tools()
            else:
                # Update configuration panel when selections change
                self.refresh_configuration()
        elif event.checkbox.id == "py_repo_enabled":
            # Handle Python repository configuration enable/disable
            self.config.install_python_repository = event.value
            # Refresh repository settings without recreating all tools
            self.__refresh_python_repository_settings()
        elif event.checkbox.id.startswith("py_repo_"):
            # Handle Python repository type selection
            if event.value:
                # Uncheck other repository types
                for repo_type in ["py_repo_pypi", "py_repo_artifactory", "py_repo_custom"]:
                    if repo_type != event.checkbox.id:
                        try:
                            checkbox = self.query_one(f"#{repo_type}", Checkbox)
                            checkbox.value = False
                        except Exception as e:
                            # Only log checkbox errors in debug mode
                            logger.debug(
                                "Checkbox '%s' not found during repository type selection: %s",
                                repo_type,
                                e,
                            )

                # Update URL fields based on repository type
                try:
                    publish_input = self.query_one("#py_publish_url", Input)
                    index_input = self.query_one("#py_index_url", Input)

                    if event.checkbox.id == "py_repo_pypi":
                        publish_input.value = "https://upload.pypi.org/legacy/"
                        index_input.value = "https://pypi.org/simple/"
                    elif event.checkbox.id == "py_repo_artifactory":
                        publish_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi-local"
                        index_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi/simple"
                    elif event.checkbox.id == "py_repo_custom":
                        publish_input.value = "https://your-custom-repo.com/upload/"
                        index_input.value = "https://your-custom-repo.com/simple/"

                    # Update the config immediately
                    self.config.python_publish_url = publish_input.value
                    self.config.python_index_url = index_input.value

                except Exception as e:
                    logger.debug("Could not update Python URL fields: %s", e)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio set changes for Python repository type.

        Parameters
        ----------
        event : RadioSet.Changed
            The radio set change event

        """
        if event.radio_set.id == "py_repo_radioset":
            try:
                publish_input = self.query_one("#py_publish_url", Input)
                index_input = self.query_one("#pyproject_index_url", Input)

                if event.pressed.id == "py_repo_pypi":
                    publish_input.value = "https://upload.pypi.org/legacy/"
                    index_input.value = "https://pypi.org/simple/"
                elif event.pressed.id == "py_repo_artifactory":
                    publish_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi-local"
                    index_input.value = "https://your-company.jfrog.io/artifactory/api/pypi/pypi/simple"
                elif event.pressed.id == "py_repo_nexus":
                    publish_input.value = "https://nexus.your-company.com/repository/pypi-hosted/"
                    index_input.value = "https://nexus.your-company.com/repository/pypi-group/simple"
                elif event.pressed.id == "py_repo_custom":
                    publish_input.value = "https://your-custom-repo.com/upload/"
                    index_input.value = "https://your-custom-repo.com/simple/"

                # Update the config immediately
                self.config.python_publish_url = publish_input.value
                self.config.python_index_url = index_input.value

            except Exception as e:
                logger.debug("Could not update Python URL fields: %s", e)

    def __cleanup_version_inputs(self) -> None:
        """Remove any existing version input widgets to prevent duplicates."""
        # Silently clean up version inputs - only log if in debug mode
        if DEBUG_MODE:
            logger.debug("Cleaning up version input widgets")

        try:
            # Find and remove all version input widgets
            for tool in list(self.tool_version_configurable.keys()):
                try:
                    version_widget = self.query_one(f"#version_{tool}", Input)
                    version_widget.remove()
                    if DEBUG_MODE:
                        logger.debug("Removed version widget for tool: %s", tool)
                except Exception as e:
                    # Don't log missing widgets - this is expected behavior
                    if DEBUG_MODE:
                        logger.debug("Version widget for tool %s not found during cleanup: %s", tool, e)
        except Exception as e:
            if DEBUG_MODE:
                logger.debug("Error during version input cleanup: %s", e)

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
            # Parse generation-based format: version_{tool}_gen_{generation}
            tool = (
                event.input.id.split("_gen_")[0][8:] if "_gen_" in event.input.id else event.input.id[8:]
            )  # Remove "version_" prefix
            self.tool_version_value[tool] = event.value
        elif event.input.id == "py_index_url":
            self.config.python_index_url = event.value
        elif event.input.id == "py_publish_url":
            self.config.python_publish_url = event.value
        elif event.input.id == "pyproject_name":
            # Update package name and related fields when package name changes
            logger.debug("Package name input changed to: %s", event.value)
            self.config.python_project_name = event.value
            # Use call_later to ensure all widgets are mounted before updating
            self.call_later(self.__update_package_related_fields, event.value)
        elif event.input.id == "github_username":
            # Handle GitHub username changes - update URL fields immediately on focus loss
            logger.debug("GitHub username input changed to: %s", event.value)
            self.config.python_github_username = event.value
            # Update related URL fields immediately when GitHub username changes
            self.call_later(self.__update_github_related_fields, event.value)
        elif event.input.id == "pyproject_homepage":
            # Handle Homepage URL changes - rely on focus-loss detection for immediate processing
            # Store the value but don't set timer - let focus loss handle the propagation
            logger.debug("Homepage URL input changed to: %s", event.value)
            # The actual username propagation will happen on focus loss via _process_input_on_focus_loss()

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
                self.__process_input_on_focus_loss(previous_input_id)

            # Update tracked input
            if current_input_id:
                self._last_focused_input = current_input_id

    def __process_input_on_focus_loss(self, input_id: str) -> None:
        """Process specific inputs when they lose focus.

        Parameters
        ----------
        input_id : str
            The ID of the input that lost focus

        """
        try:
            if input_id == "github_username":
                # Process GitHub username immediately on focus loss
                github_input = self.query_one("#github_username", Input)
                github_value = github_input.value.strip()
                if github_value:
                    logger.debug("Processing GitHub username on focus loss: %s", github_value)
                    self.config.python_github_username = github_value
                    self.__update_github_related_fields(github_value)

            elif input_id == "pyproject_homepage":
                # Process homepage URL immediately on focus loss (instead of timer)
                if not self._username_propagated:
                    homepage_input = self.query_one("#pyproject_homepage", Input)
                    homepage_value = homepage_input.value.strip()
                    if homepage_value:
                        logger.debug("Processing homepage URL on focus loss: %s", homepage_value)
                        # Cancel any existing timer since we're processing immediately
                        if hasattr(self, "_username_timer"):
                            self._username_timer.stop()
                        self.__check_and_propagate_username(homepage_value)

        except Exception as e:
            logger.debug("Error processing input on focus loss (%s): %s", input_id, e)

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
            # Process Homepage URL immediately when Enter is pressed
            try:
                homepage_input = self.query_one("#pyproject_homepage", Input)
                homepage_value = homepage_input.value.strip()
                if homepage_value and not self._username_propagated:
                    logger.debug("Processing homepage URL on Enter key: %s", homepage_value)
                    self.__check_and_propagate_username(homepage_value)
            except Exception as e:
                logger.debug("Error processing homepage URL on Enter: %s", e)

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
            logger.debug("URL not complete enough for propagation")
            return

        try:
            # Extract username from the homepage URL
            username = self.__extract_username_from_url(homepage_url)
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

            # Get other URL fields
            source_input = self.query_one("#pyproject_source", Input)
            documentation_input = self.query_one("#pyproject_documentation", Input)

            # Update source URL if it still uses template username
            if "yourusername" in source_input.value:
                repo_name = url_match.group(2)
                new_source = f"https://github.com/{username}/{repo_name}"
                source_input.value = new_source
                logger.debug("Updated source URL to: %s", new_source)

            # Update documentation URL
            if (
                not documentation_input.value.strip()
                or "yourusername" in documentation_input.value
                or documentation_input.value == self.__get_default_documentation_url()
            ):
                repo_name = url_match.group(2)
                new_documentation = f"https://github.com/{username}/{repo_name}/README.md"
                documentation_input.value = new_documentation
                logger.debug("Updated documentation URL to: %s", new_documentation)

            # Mark that username propagation has happened
            self._username_propagated = True
            logger.debug("Username propagation completed, future changes will not propagate")

        except Exception as e:
            logger.debug("Could not check/propagate username: %s", e)
            logger.debug("Traceback: %s", traceback.format_exc())

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
            # Convert package name to valid formats
            if package_name and package_name.strip():
                package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
                package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            else:
                # Use defaults for empty package name
                package_name_clean = "my_awesome_project"
                package_name_url = "my-awesome-project"

            # Update Homepage URL if it still has the default value
            homepage_input = self.query_one("#pyproject_homepage", Input)
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
                logger.debug("Updated homepage URL to: %s", new_url)

            # Update Source URL if it still has the default value
            source_input = self.query_one("#pyproject_source", Input)
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
                logger.debug("Updated source URL to: %s", new_url)

            # Update Documentation URL if it still has the default value
            documentation_input = self.query_one("#pyproject_documentation", Input)
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
                logger.debug("Updated documentation URL to: %s", new_url)

            # Update Package Path if it still has the default value
            packages_input = self.query_one("#pyproject_packages", Input)
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
                logger.debug("Updated package path to: %s", new_path)

        except Exception as e:
            # Log errors for debugging
            logger.debug("Could not update package-related fields: %s", e)
            logger.debug("Traceback: %s", traceback.format_exc())

    def __get_default_homepage_url(self) -> str:
        """Get default homepage URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_source_url(self) -> str:
        """Get default source URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_documentation_url(self) -> str:
        """Get default documentation URL based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}/README.md"
        return "https://github.com/yourusername/my-awesome-project/README.md"

    def __update_github_related_fields(self, github_username: str) -> None:
        """Update URL fields when GitHub username changes.

        Parameters
        ----------
        github_username : str
            The new GitHub username

        """
        if not github_username or github_username.strip() == "":
            logger.debug("GitHub username is empty, skipping URL updates")
            return

        username = github_username.strip()
        logger.debug("Updating URL fields for GitHub username: %s", username)

        try:
            # Get the current project name for URL construction
            project_name = self.config.python_project_name
            if not project_name or project_name == "my-awesome-project":
                project_name = "my-awesome-project"  # Fallback

            # Clean project name for URL
            project_name_url = project_name.lower().replace("_", "-").replace(" ", "-")

            # Get URL input fields
            try:
                homepage_input = self.query_one("#pyproject_homepage", Input)
            except NoMatches:
                homepage_input = None

            try:
                source_input = self.query_one("#pyproject_source", Input)
            except NoMatches:
                source_input = None

            try:
                documentation_input = self.query_one("#pyproject_documentation", Input)
            except NoMatches:
                documentation_input = None

            # Update Homepage URL if it still has default/template values
            if homepage_input:
                current_homepage = homepage_input.value
                if (
                    not current_homepage.strip()
                    or "yourusername" in current_homepage
                    or current_homepage == "https://github.com/yourusername/my-awesome-project"
                    or current_homepage.startswith("https://github.com/yourusername/")
                ):
                    new_homepage = f"https://github.com/{username}/{project_name_url}"
                    homepage_input.value = new_homepage
                    logger.debug("Updated homepage URL to: %s", new_homepage)

            # Update Source URL if it still has default/template values
            if source_input:
                current_source = source_input.value
                if (
                    not current_source.strip()
                    or "yourusername" in current_source
                    or current_source == "https://github.com/yourusername/my-awesome-project"
                    or current_source.startswith("https://github.com/yourusername/")
                ):
                    new_source = f"https://github.com/{username}/{project_name_url}"
                    source_input.value = new_source
                    logger.debug("Updated source URL to: %s", new_source)

            # Update Documentation URL if it still has default/template values
            if documentation_input:
                current_docs = documentation_input.value
                if (
                    not current_docs.strip()
                    or "yourusername" in current_docs
                    or current_docs == "https://github.com/yourusername/my-awesome-project/README.md"
                    or current_docs.startswith("https://github.com/yourusername/")
                ):
                    new_docs = f"https://github.com/{username}/{project_name_url}/README.md"
                    documentation_input.value = new_docs
                    logger.debug("Updated documentation URL to: %s", new_docs)

        except Exception as e:
            logger.debug("Error updating GitHub-related fields: %s", e)

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
            return github_match.group(1)

        return ""

    def __get_default_package_path(self) -> str:
        """Get default package path based on current package name."""
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
            return f"src/{package_name_clean}"
        return "src/my_awesome_project"

    def __select_all_tools(self) -> None:
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
            # Extract tool and version from button ID: "version_btn_{tool}_{safe_version}"
            parts = button_id.split("_")
            if len(parts) >= VERSION_BUTTON_PARTS:
                tool = parts[2]
                safe_version = "_".join(parts[3:])  # Handle safe versions that have underscores
                # Convert safe version back to original version (replace underscores with dots)
                version = safe_version.replace("_", ".")

                # Update the tool version value
                self.tool_version_value[tool] = version

                # Update the version input field if it exists
                try:
                    version_id = f"version_{tool}_gen_{self._widget_generation}"
                    if version_id in self._active_version_inputs:
                        version_input = self.query_one(f"#{version_id}", Input)
                        version_input.value = version
                except Exception as e:
                    logger.debug("Version input widget '%s' not found for tool '%s': %s", version_id, tool, e)
            return

        # Handle section link clicks
        if button_id.startswith("section_link_"):
            # Extract section index from button ID: "section_link_{index}"
            try:
                section_index = int(button_id.split("_")[-1])
                logger.debug(
                    "SECTION CLICK DEBUG: button_id=%s, section_index=%d, current_section=%d",
                    button_id,
                    section_index,
                    self.current_section,
                )
                if 0 <= section_index < len(self.sections) and section_index != self.current_section:
                    section_name = self.sections[section_index]
                    logger.debug(
                        "SECTION CLICK DEBUG: Switching from section %d (%s) to section %d (%s)",
                        self.current_section,
                        self.sections[self.current_section],
                        section_index,
                        section_name,
                    )
                    self.save_current_section()
                    self.current_section = section_index
                    self.refresh_controls()
                    self.refresh_tools()
                    self.refresh_navigation_links("section-links", "section_link", "Tools")
                else:
                    logger.debug("SECTION CLICK DEBUG: No section switch needed (same section or invalid index)")
            except (ValueError, IndexError) as e:
                logger.debug("Invalid section link button ID '%s': %s", button_id, e)
            return

        if button_id == "back_btn":
            self.action_back()
        elif button_id == "prev_btn":
            self.save_current_section()
            self.current_section = max(0, self.current_section - 1)
            self.refresh_controls()
            self.refresh_tools()
        elif button_id == "next_section_btn":
            self.save_current_section()
            self.current_section = min(len(self.sections) - 1, self.current_section + 1)
            self.refresh_controls()
            self.refresh_tools()
        elif button_id == "next_btn":
            self.save_current_section()
            self.finalize_selection()
        elif button_id == "select_all_tools":
            self.__select_all_tools()
        elif button_id == "copy_debug_btn":
            self.__copy_debug_output()

    def refresh_controls(self) -> None:
        """Refresh button states.

        Updates the navigation button states (enabled/disabled) and screen titles
        based on the current section position and available sections.

        """
        prev_btn = self.query_one("#prev_btn", Button)
        next_section_btn = self.query_one("#next_section_btn", Button)

        prev_btn.disabled = self.current_section == 0
        next_section_btn.disabled = self.current_section >= len(self.sections) - 1

        # Update title and subtitle
        title_label = self.query_one("Label", Label)
        title_label.update(
            f"Development Tools - {self.sections[self.current_section]} - Section {self.current_section + 1} of {len(self.sections)}",
        )

        # Update subtitle showing section progress
        try:
            subtitle_label = self.query_one("Label.subtitle", Label)
            subtitle_label.update(f"Section {self.current_section + 1} of {len(self.sections)}")
        except Exception as e:
            logger.debug("Subtitle label not found during section update: %s", e)

        # Refresh section links to show current selection
        self.refresh_navigation_links("section-links", "section_link", "Tools")

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
        """Finalize tool selection and continue."""
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
        self.app.push_screen(ProjectConfigScreen(self.config))


class SummaryScreen(Screen[None], DebugMixin):
    """Summary screen showing final configuration."""

    BINDINGS = [
        Binding("enter", "install", "Install"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize the Summary screen.

        Parameters
        ----------
        config : ProjectConfig
            Project configuration data

        """
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        logger.debug("SummaryScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        summary_text = self.generate_summary()

        yield Header()
        yield Container(
            Label("Configuration Summary", classes="title"),
            ScrollableContainer(
                Markdown(summary_text),
                id="summary-scroll",
            ),
            Horizontal(
                Button("<< Dev Container Extensions", id="back_btn", classes="nav-button"),
                Button("Install", id="install_btn", variant="primary", classes="nav-button"),
                id="button-row",
            ),
            id="summary-container",
        )
        yield Footer()

    def generate_summary(self) -> str:
        """Generate a markdown summary of the project configuration.

        Creates a formatted markdown string containing project settings,
        selected development tools, and configuration details for display
        in the summary screen.

        Returns
        -------
        str
            Formatted markdown text summarizing the project configuration

        """
        summary = "## Project Settings\n\n"
        summary += f"- **Name:** {self.config.project_name}\n"
        summary += f"- **Display Name:** {self.config.display_name}\n"
        summary += f"- **Container:** {self.config.container_name}\n"

        if self.config.docker_exec_command:
            summary += f"- **Exec Command:** {self.config.docker_exec_command}\n"

        # Count selected tools
        selected_tools = [tool for tool, selected in self.config.tool_selected.items() if selected]

        if selected_tools:
            summary += f"\n## Development Tools ({len(selected_tools)} selected)\n\n"
            for tool in selected_tools:
                version = self.config.tool_version_value.get(tool, "latest")
                if version and version != "latest":
                    summary += f"- **{tool}** ({version})\n"
                else:
                    summary += f"- **{tool}** (latest)\n"
        else:
            summary += "\n## Development Tools\nNone selected\n"

        # Python Configuration
        if self.config.install_python_tools:
            summary += "\n## Python Configuration\n\n"
            summary += f"- **Repository Type:** {self.config.python_repository_type}\n"
            summary += f"- **Publish URL:** {self.config.python_publish_url}\n"
            if self.config.python_index_url:
                summary += f"- **Index URL:** {self.config.python_index_url}\n"
            if self.config.python_extra_index_url:
                summary += f"- **Extra Index URL:** {self.config.python_extra_index_url}\n"

            # Python project metadata
            if self.config.python_project_name:
                summary += "\n### Python Project Details\n"
                summary += f"- **Project Name:** {self.config.python_project_name}\n"
                if self.config.python_project_description:
                    summary += f"- **Description:** {self.config.python_project_description}\n"
                if self.config.python_author_name:
                    summary += f"- **Author:** {self.config.python_author_name}\n"
                if self.config.python_author_email:
                    summary += f"- **Email:** {self.config.python_author_email}\n"
                if self.config.python_github_username:
                    summary += f"- **GitHub User:** {self.config.python_github_username}\n"
                if self.config.python_github_project:
                    summary += f"- **GitHub Project:** {self.config.python_github_project}\n"
                if self.config.python_license:
                    summary += f"- **License:** {self.config.python_license}\n"
                if self.config.python_keywords:
                    summary += f"- **Keywords:** {self.config.python_keywords}\n"

        # Dev Container Extensions
        extension_summary_added = False

        # PSI Header
        if self.config.install_psi_header:
            if not extension_summary_added:
                summary += "\n## Dev Container Extensions\n\n"
                extension_summary_added = True
            summary += "### PSI Header\n"
            if self.config.psi_header_company:
                summary += f"- **Company:** {self.config.psi_header_company}\n"
            if self.config.psi_header_templates:
                template_names = [name for _, name in self.config.psi_header_templates]
                summary += f"- **Language Templates:** {', '.join(template_names)}\n"
            summary += "\n"

        # Other extension sections
        for section_name, is_enabled in self.config.selected_extension_sections.items():
            if is_enabled:
                if not extension_summary_added:
                    summary += "\n## Dev Container Extensions\n\n"
                    extension_summary_added = True
                summary += f"### {section_name}\n"

                # List selected extensions for this section
                section_extensions = []
                for ext_id, is_selected in self.config.selected_extensions.items():
                    if is_selected:
                        # This is a simplified check - in a full implementation, we'd need to
                        # track which extensions belong to which sections
                        section_extensions.append(ext_id)

                if section_extensions:
                    summary += f"- **Extensions:** {len(section_extensions)} extensions selected\n"
                summary += "\n"

        summary += "\n---\n\n**Proceed with installation?**"

        return summary

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "install_btn":
            self.action_install()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self.__copy_debug_output()

    def action_install(self) -> None:
        """Start the installation process."""
        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_summary)
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_back(self) -> None:
        """Go to previous step."""
        # Navigate back to PSI Header configuration screen
        self.app.pop_screen()  # Remove Summary screen
        # Cast to actual app type to access show_extension_config method
        app = cast("DynamicDevContainerApp", self.app)
        app.show_extension_config()  # Show Extensions screen

    def action_toggle_debug(self) -> None:
        """Toggle debug mode."""
        # Check if debug panel already exists
        try:
            debug_container = self.query_one("#debug_container")
            # Remove existing debug panel
            debug_container.remove()
        except Exception:
            # Debug panel doesn't exist, create it
            self.__rebuild_with_debug_panel()


class InstallationScreen(Screen[None]):
    """Screen showing installation progress."""

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
        self.progress_step = 0
        self.total_steps = 6

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()
        yield Container(
            Label("Installing Dev Container Configuration...", classes="title"),
            ProgressBar(total=self.total_steps, id="progress"),
            Label("Initializing...", id="status"),
            id="install-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        """Start installation when screen is mounted."""
        self.call_after_refresh(self.start_installation)

    def start_installation(self) -> None:
        """Start the installation process."""
        try:
            self.update_progress("Creating project directory...")
            self.create_project_directory()

            self.update_progress("Copying files and directories...")
            self.copy_files()

            self.update_progress("Generating .mise.toml...")
            self.generate_mise_toml()

            self.update_progress("Generating devcontainer.json...")
            self.generate_devcontainer_json()

            self.update_progress("Updating dev.sh...")
            self.update_dev_sh()

            self.update_progress("Configuring project settings...")
            if self.config.install_python_tools:
                self.update_pyproject_toml()
                self.configure_python_repository_settings()

            if self.config.install_psi_header:
                self.configure_psi_header()

            self.update_progress("Installation completed successfully!")
            self.show_completion()

        except Exception as e:
            self.query_one("#status", Label).update(f"Error: {str(e)}")
            self.notify(f"Installation failed: {str(e)}", severity="error")

    def update_progress(self, status: str) -> None:
        """Update progress bar and status.

        Parameters
        ----------
        status : str
            Progress status message

        """
        self.progress_step += 1
        progress_bar = self.query_one("#progress", ProgressBar)
        status_label = self.query_one("#status", Label)

        progress_bar.update(progress=self.progress_step)
        status_label.update(status)

    def create_project_directory(self) -> None:
        """Create the project directory structure if it doesn't exist.

        Creates the directory specified in config.project_path including
        any necessary parent directories using mkdir with parents=True.
        """
        project_path = Path(self.config.project_path)
        project_path.mkdir(parents=True, exist_ok=True)

    def copy_files(self) -> None:
        """Copy source files and directories to the target project location.

        Copies all necessary files from the source directory to the configured
        project path using FileManager. Includes Python-specific files if
        Python tools are enabled in the configuration.
        """
        source_dir = self.source_dir
        target_dir = Path(self.config.project_path)

        FileManager.copy_files_and_directories(
            source_dir,
            target_dir,
            include_python=self.config.install_python_tools,
        )

    def generate_mise_toml(self) -> None:
        """Generate a customized .mise.toml file based on selected tools.

        Reads the source .mise.toml template and creates a new version
        containing only the tools that were selected during configuration.
        Filters tools based on user selections and includes appropriate
        environment and tool sections.
        """
        source_file = self.source_dir / ".mise.toml"
        target_file = Path(self.config.project_path) / ".mise.toml"

        if not source_file.exists():
            return

        # Read original file
        with open(source_file) as f:
            content = f.read()

        # Generate new content
        lines = []
        lines.append("# Generated by Dynamic Dev Container Setup")
        lines.append("")

        # Add environment section
        in_env = False
        for line in content.split("\n"):
            if line.strip() == "#### Begin Environment":
                in_env = True
                continue
            if line.strip() == "#### End Environment":
                in_env = False
                continue
            if in_env:
                lines.append(line)

        lines.append("")
        lines.append("[tools]")
        lines.append("")

        # Add selected tools by section
        sections, _, _, _ = MiseParser.parse_mise_sections(source_file)

        for section in sections:
            section_tools = MiseParser.get_section_tools(source_file, section)
            selected_tools = [tool for tool in section_tools if self.config.tool_selected.get(tool, False)]

            if selected_tools:
                lines.append(f"#### Begin {section} ####")
                for tool in selected_tools:
                    version = self.config.tool_version_value.get(tool, "latest")
                    lines.append(f"{tool} = '{version}'")
                lines.append(f"#### End {section} ####")
                lines.append("")

        # Add alias and settings sections from original
        in_alias = False
        in_settings = False

        for line in content.split("\n"):
            if line.strip() == "[alias]":
                in_alias = True
                lines.append("")
                lines.append(line)
                continue
            if line.strip() == "[settings]":
                in_settings = True
                lines.append("")
                lines.append(line)
                continue
            if line.strip().startswith("[") and (in_alias or in_settings):
                in_alias = False
                in_settings = False
                continue
            if in_alias or in_settings:
                lines.append(line)

        # Write new file
        with open(target_file, "w") as f:
            f.write("\n".join(lines))

    def generate_devcontainer_json(self) -> None:
        """Generate a customized devcontainer.json file based on configuration.

        Creates a devcontainer.json file from the template by replacing
        placeholder values with user-configured settings including project
        name, display name, container name, and other customizations.

        Raises
        ------
        Exception
            If the source devcontainer.json template file is not found

        """
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        target_file = Path(self.config.project_path) / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            msg = f"Source devcontainer.json not found at {source_file}"
            raise Exception(msg)

        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Read the source file as text (preserving all comments and formatting)
        with open(source_file, encoding="utf-8") as f:
            content = f.read()

        # Step 1: Update container references (name, runArgs, mounts) ONLY
        content = self.__update_container_references_only(content)

        # Step 2: Remove sections for tools that are NOT selected
        content = self.__remove_unselected_tool_sections(content)

        # Step 3: Add PSI Header extension if selected
        if self.config.install_psi_header:
            content = self.__ensure_psi_header_section(content)
        else:
            content = self.__remove_psi_header_section(content)

        # Step 4: Update containerEnv with Hatch environment variables if Python repository is configured
        if self.config.install_python_repository:
            content = self.__update_container_env_hatch_vars(content)

        # Write the result
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

    def __update_container_references_only(self, content: str) -> str:
        """Update ONLY container references, preserving everything else exactly."""

        # Update display name
        content = re.sub(
            r'"name":\s*"[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r'"runArgs":\s*\[\s*"--name=[^"]*"\s*\]',
            f'"runArgs": ["--name={self.config.container_name}"]',
            content,
        )

        # Update mount sources in mounts array
        content = re.sub(
            r'"source":\s*"[^"]*-shellhistory"',
            f'"source": "{self.config.container_name}-shellhistory"',
            content,
        )
        return re.sub(
            r'"source":\s*"[^"]*-plugins"',
            f'"source": "{self.config.container_name}-plugins"',
            content,
        )

    def __remove_unselected_tool_sections(self, content: str) -> str:
        """Remove entire sections for tools that are NOT selected."""

        # Create dynamic section-tool mapping
        devcontainer_file = self.source_dir / ".devcontainer" / "devcontainer.json"
        mise_file = self.source_dir / ".mise.toml"
        section_tool_mapping = DevContainerParser.create_section_tool_mapping(mise_file, devcontainer_file)

        # Get extension and settings sections from devcontainer.json
        extension_sections = DevContainerParser.parse_extension_sections(devcontainer_file)
        settings_sections = DevContainerParser.parse_settings_sections(devcontainer_file)

        # Check which sections should be included based on tool selections
        for section_name in extension_sections:
            tools_in_section = section_tool_mapping.get(section_name, [])

            # Check if any tools in this section are selected
            section_selected = False
            for tool in tools_in_section:
                if self.config.tool_selected.get(tool, False):
                    section_selected = True
                    break

            # Special handling for conditional sections
            if section_name == "Node Development":
                section_selected = section_selected and self.config.include_js_extensions
            elif section_name == "Markdown":
                section_selected = self.config.include_markdown_extensions
            elif section_name == "Shell/Bash":
                section_selected = self.config.include_shell_extensions

            # Remove section if not selected
            if not section_selected:
                content = self.__remove_section(content, section_name, "extensions")

        # Handle user-configurable extension sections (Github, Markdown, Shell/Bash, etc.)
        # These are sections that are not tied to specific development tools
        for section_name, is_selected in self.config.selected_extension_sections.items():
            if not is_selected:
                content = self.__remove_section(content, section_name, "extensions")
                # Also remove corresponding settings section if it exists
                content = self.__remove_section(content, f"{section_name} Settings", "settings")

        # Check settings sections
        for section_name in settings_sections:
            tools_in_section = section_tool_mapping.get(section_name, [])

            # Check if any tools in this section are selected
            section_selected = False
            for tool in tools_in_section:
                if self.config.tool_selected.get(tool, False):
                    section_selected = True
                    break

            # Special handling for conditional sections
            if section_name == "Node Development":
                section_selected = section_selected and self.config.include_js_extensions
            elif section_name == "Markdown":
                section_selected = self.config.include_markdown_extensions
            elif section_name == "Shell/Bash":
                section_selected = self.config.include_shell_extensions

            # Remove settings section if not selected
            if not section_selected:
                content = self.__remove_section(content, f"{section_name} Settings", "settings")

        return content

    def __remove_section(self, content: str, section_name: str, _section_type: str) -> str:
        """Remove a section between begin/end markers and fix trailing commas."""
        begin_pattern = f"// #### Begin {section_name} ####"
        end_pattern = f"// #### End {section_name} ####"

        # Find the section and remove it
        lines = content.split("\n")
        result_lines = []
        in_section = False

        for line in lines:
            if begin_pattern in line:
                in_section = True
                continue
            if end_pattern in line:
                in_section = False
                continue
            if not in_section:
                result_lines.append(line)

        # Fix trailing commas after section removal
        content = "\n".join(result_lines)
        return self.__fix_trailing_commas(content)

    def __fix_trailing_commas(self, content: str) -> str:
        """Fix trailing commas in JSON that would be invalid after section removal."""
        lines = content.split("\n")
        result_lines = []

        for _i, line in enumerate(lines):
            result_lines.append(line)

            # Check if this line ends with a comment like "// #### End Core VS Code Settings ####"
            # and the next non-empty line starts a new section
            if "// #### End Core VS Code Settings ####" in line:
                # Look back to find the last property line and ensure it has a comma
                for j in range(len(result_lines) - 2, -1, -1):  # Go backwards
                    prev_line = result_lines[j].strip()
                    if prev_line and not prev_line.startswith("//") and not prev_line.startswith("/*"):
                        # This is a property line - ensure it ends with comma
                        if not prev_line.endswith(",") and not prev_line.endswith("{") and not prev_line.endswith("["):
                            result_lines[j] = result_lines[j] + ","
                        break

        # Handle trailing commas before closing braces and fix block comment issues
        final_lines = []
        for i, line in enumerate(result_lines):
            # Check for situations where we need to add comma before block comment
            if line.strip() == "}," and i < len(result_lines) - 1:
                # Look ahead to see if next line is a block comment
                next_line = result_lines[i + 1].strip() if i + 1 < len(result_lines) else ""
                if next_line.startswith("/*"):
                    # The comma is already there, this is good
                    final_lines.append(line)
                else:
                    final_lines.append(line)
            elif line.strip().endswith(","):
                # Look ahead to see what comes next
                next_significant_line = None
                for j in range(i + 1, len(result_lines)):
                    if result_lines[j].strip():  # Non-empty line
                        next_significant_line = result_lines[j].strip()
                        break

                # If the next significant line closes an object/array, remove the comma
                if next_significant_line and next_significant_line.startswith(("}", "]")):
                    final_lines.append(line.rstrip(","))
                else:
                    final_lines.append(line)
            else:
                final_lines.append(line)

        return "\n".join(final_lines)

    def __ensure_psi_header_section(self, content: str) -> str:
        """Ensure PSI Header section is present and update templates with actual content."""
        # If PSI Header is configured, replace template placeholders with actual content
        if self.config.psi_header_templates:
            content = self.__update_psi_header_templates(content)
        return content

    def __get_psi_languages_for_selected_tools(self) -> list[tuple[str, str]]:
        """Get PSI header languages that should be included based on selected tools."""
        # Base languages to include if PSI header is enabled
        base_languages = [("*", "Default")]

        # If user selected specific PSI header templates, include those
        if self.config.psi_header_templates:
            return self.config.psi_header_templates

        # Otherwise, automatically include languages based on selected tools
        languages_to_include = base_languages.copy()

        # Map tools to their corresponding PSI header languages
        tool_language_mapping = {
            # Go Development
            "golang": ("go", "Go"),
            "golangci-lint": ("go", "Go"),
            "goreleaser": ("go", "Go"),
            # .NET Development
            "dotnet": ("csharp", "C#"),
            # Node Development
            "node": ("javascript", "JavaScript"),
            "pnpm": ("javascript", "JavaScript"),
            "yarn": ("javascript", "JavaScript"),
            "deno": ("typescript", "TypeScript"),
            "bun": ("javascript", "JavaScript"),
            # Python
            "python": ("python", "Python"),
            # PowerShell
            "powershell": ("powershell", "PowerShell"),
            # HashiCorp Tools (use terraform language)
            "opentofu": ("terraform", "Terraform/OpenTofu"),
            "openbao": ("terraform", "Terraform/OpenTofu"),
            "packer": ("terraform", "Terraform/OpenTofu"),
        }

        # Check which tools are selected and add their languages
        included_languages = set()
        for tool_name, is_selected in self.config.tool_selected.items():
            if is_selected and tool_name in tool_language_mapping:
                lang_id, lang_name = tool_language_mapping[tool_name]
                if lang_id not in included_languages:
                    languages_to_include.append((lang_id, lang_name))
                    included_languages.add(lang_id)

        # Always include common languages if any development tools are selected
        if any(self.config.tool_selected.values()):
            common_languages = [
                ("shellscript", "Shell Script"),
                ("markdown", "Markdown"),
            ]
            for lang_id, lang_name in common_languages:
                if lang_id not in included_languages:
                    languages_to_include.append((lang_id, lang_name))
                    included_languages.add(lang_id)

        return languages_to_include

    def __update_psi_header_templates(self, content: str) -> str:
        """Update PSI header templates with actual template content from user configuration."""

        # Generate the template content for each configured language
        template_entries = []

        # Get all languages that should have templates based on selected tools
        languages_to_include = self.__get_psi_languages_for_selected_tools()

        for lang_id, _lang_name in languages_to_include:
            # Create the default template content similar to bash script
            current_year = datetime.now(tz=UTC).year
            company = self.config.psi_header_company or "My Company"

            # Generate template text based on language
            if lang_id == "powershell":
                # PowerShell has special .DESCRIPTION format
                template_lines = [
                    ".DESCRIPTION",
                    f"Copyright © {current_year} {company}. All rights reserved.",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]
            else:
                # Standard template for other languages
                template_lines = [
                    f"Copyright © {current_year} {company}. All rights reserved.",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]

            template_entry = {
                "language": lang_id,
                "template": template_lines,
            }
            template_entries.append(template_entry)

        # If no custom templates, add a default one
        if not template_entries:
            current_year = datetime.now(tz=UTC).year
            company = self.config.psi_header_company or "My Company"
            default_template = {
                "language": "*",
                "template": [f"Copyright © {current_year} {company}. All rights reserved."],
            }
            template_entries.append(default_template)

        # Now replace the "psi-header.templates" section in the content
        # Find the templates array and replace it with our generated content
        lines = content.split("\n")
        result_lines = []
        templates_indent = ""

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for the start of psi-header.templates section
            if '"psi-header.templates": [' in line:
                templates_indent = line[: line.find('"psi-header.templates"')]
                result_lines.append(line)  # Add the opening line

                # Skip until we find the closing bracket for this array
                i += 1
                bracket_count = 1
                while i < len(lines) and bracket_count > 0:
                    line = lines[i]
                    # Count brackets to find the end of the array
                    bracket_count += line.count("[") - line.count("]")
                    if bracket_count == 0:
                        # This is the closing line, we'll replace everything before it
                        break
                    i += 1

                # Now insert our custom templates
                for j, template_entry in enumerate(template_entries):
                    result_lines.append(f"{templates_indent}          {{")
                    result_lines.append(f'{templates_indent}            "language": "{template_entry["language"]}",')

                    # Format the template array
                    template_json = json.dumps(template_entry["template"], ensure_ascii=False)
                    result_lines.append(f'{templates_indent}            "template": {template_json}')

                    # Add closing brace with comma if not the last entry
                    if j < len(template_entries) - 1:
                        result_lines.append(f"{templates_indent}          }},")
                    else:
                        result_lines.append(f"{templates_indent}          }}")

                # Add the closing bracket line
                if i < len(lines):
                    result_lines.append(lines[i])
            else:
                result_lines.append(line)

            i += 1

        return "\n".join(result_lines)

    def __remove_psi_header_section(self, content: str) -> str:
        """Remove PSI Header section if not selected."""
        content = self.__remove_section(content, "PSI Header", "extensions")
        return self.__remove_section(content, "PSI Header Settings", "settings")

    def __update_container_env_hatch_vars(self, content: str) -> str:
        """Update containerEnv section to include Hatch environment variables."""
        if not self.config.install_python_repository:
            return content

        # Find the containerEnv section
        lines = content.split("\n")
        result_lines = []
        in_container_env = False
        container_env_indent = ""
        added_hatch_vars = False

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for containerEnv section start
            if '"containerEnv":' in line and "{" in line:
                in_container_env = True
                container_env_indent = line[: line.find('"containerEnv"')]
                result_lines.append(line)
                i += 1
                continue

            # If we're in containerEnv section, look for the closing brace
            if in_container_env:
                # Check if this is the end of containerEnv (closing brace with same indentation)
                if line.strip() == "}," or (
                    line.strip() == "}" and i + 1 < len(lines) and lines[i + 1].strip().startswith(",")
                ):
                    # Add Hatch environment variables before the closing brace
                    if not added_hatch_vars:
                        # Add comma to previous line if it doesn't have one and it's not a comment
                        if (
                            result_lines
                            and not result_lines[-1].rstrip().endswith(",")
                            and not result_lines[-1].strip().startswith("//")
                        ):
                            result_lines[-1] = result_lines[-1].rstrip() + ","

                        # Add comment and variables with proper indentation
                        result_lines.append(
                            f"{container_env_indent}    // Python Package Publishing Environment Variables",
                        )
                        result_lines.append(
                            f'{container_env_indent}    "HATCH_INDEX_USER": "${{localEnv:HATCH_INDEX_USER}}",',
                        )
                        result_lines.append(
                            f'{container_env_indent}    "HATCH_INDEX_AUTH": "${{localEnv:HATCH_INDEX_AUTH}}",',
                        )

                        # Add HATCH_INDEX_REPO with the user's configured URL (no trailing comma on last item)
                        if self.config.python_publish_url:
                            result_lines.append(
                                f'{container_env_indent}    "HATCH_INDEX_REPO": "{self.config.python_publish_url}"',
                            )

                        added_hatch_vars = True

                    # Add the closing brace
                    result_lines.append(line)
                    in_container_env = False
                    i += 1
                    continue

                # Check if Hatch variables already exist (to avoid duplicates)
                if "HATCH_INDEX_USER" in line or "HATCH_INDEX_AUTH" in line or "HATCH_INDEX_REPO" in line:
                    # Skip existing Hatch variables to replace them
                    i += 1
                    continue

            result_lines.append(line)
            i += 1

        return "\n".join(result_lines)

    def __update_container_references_in_content(self, content: str) -> str:
        """Update container name references in the content using regex."""

        # Update name
        content = re.sub(
            r'"name": "[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r'"runArgs": \["--name=[^"]*"\]',
            f'"runArgs": ["--name={self.config.container_name}"]',
            content,
        )

        # Update mount sources
        content = re.sub(
            r'"source": "dynamic-dev-container-shellhistory"',
            f'"source": "{self.config.container_name}-shellhistory"',
            content,
        )
        return re.sub(
            r'"source": "dynamic-dev-container-plugins"',
            f'"source": "{self.config.container_name}-plugins"',
            content,
        )

    def __update_container_references(self, file_path: Path) -> None:
        """Update container name references in the file using sed-like replacements."""
        with open(file_path) as f:
            content = f.read()

        # Update name
        content = re.sub(
            r'"name": "[^"]*"',
            f'"name": "{self.config.display_name}"',
            content,
        )

        # Update runArgs container name
        content = re.sub(
            r"--name=dynamic-dev-container",
            f"--name={self.config.container_name}",
            content,
        )

        # Update mount sources
        content = re.sub(
            r"dynamic-dev-container-shellhistory",
            f"{self.config.container_name}-shellhistory",
            content,
        )
        content = re.sub(
            r"dynamic-dev-container-plugins",
            f"{self.config.container_name}-plugins",
            content,
        )

        with open(file_path, "w") as f:
            f.write(content)

    def __append_remaining_devcontainer_content(self, temp_file: Path, source_file: Path) -> None:
        """Append the remaining content after extensions array from source file."""
        with open(source_file) as f:
            lines = f.readlines()

        # Find where extensions array ends and get the rest
        extensions_end_found = False
        remaining_lines = []
        in_extensions = False

        for line in lines:
            if '"extensions": [' in line:
                in_extensions = True
                continue
            if in_extensions and line.strip() == "],":
                # Found end of extensions array, start collecting remaining content
                extensions_end_found = True
                remaining_lines.append("      ],\n")
                continue
            if extensions_end_found:
                remaining_lines.append(line)

        # Append remaining content to temp file
        with open(temp_file, "a") as f:
            f.writelines(remaining_lines)

    def __extract_devcontainer_section(self, start_marker: str, end_marker: str) -> list[str]:
        """Extract a section from the devcontainer.json file."""
        source_file = self.source_dir / ".devcontainer" / "devcontainer.json"

        if not source_file.exists():
            return []

        with open(source_file) as f:
            lines = f.readlines()

        result = []
        in_section = False

        for line in lines:
            if start_marker in line:
                in_section = True
                continue
            if end_marker in line:
                break
            if in_section:
                # Extract extension lines - look for quoted strings that may have comments
                stripped = line.strip()
                if stripped.startswith('"') and ("," in stripped or stripped.endswith('"')):
                    # Extract the extension ID from the quoted string
                    # Handle format: "extension.id", // comment
                    extension_part = stripped.split(",")[0] if "," in stripped else stripped

                    # Remove quotes to get extension ID
                    extension_id = extension_part.strip('"')
                    if extension_id:  # Only add non-empty extension IDs
                        result.append(extension_id)

        return result

    def __generate_psi_header_settings(self) -> dict[str, Any]:
        """Generate PSI Header specific settings."""
        if not self.config.install_psi_header:
            return {}

        settings: dict[str, Any] = {}

        # Company configuration
        if self.config.psi_header_company:
            settings["psi-header.config"] = {
                "company": self.config.psi_header_company,
            }

        # Changes tracking configuration
        settings["psi-header.changes-tracking"] = {
            "autoHeader": "autoSave",
            "exclude": ["json"],
            "excludeGlob": ["**/.git/**"],
        }

        # Project creation year
        current_year = str(datetime.now(tz=UTC).year)
        settings["psi-header.variables"] = [["projectCreationYear", current_year]]

        # Language configurations
        lang_configs: list[dict[str, Any]] = []

        # Default configuration for all languages
        lang_configs.append(
            {
                "language": "*",
                "begin": "",
                "end": "",
                "prefix": "// ",
            },
        )

        # Add language-specific configurations based on selected tools and templates
        if self.config.psi_header_templates:
            for lang_id, _lang_name in self.config.psi_header_templates:
                template_lines = [
                    f"Copyright (c) {self.config.psi_header_company or 'Company'} - All Rights Reserved",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ]

                lang_config: dict[str, Any] = {
                    "language": lang_id,
                    "template": template_lines,
                }

                # Language-specific configurations
                if lang_id == "python":
                    lang_config.update(
                        {
                            "begin": '"""',
                            "end": '"""',
                            "prefix": "",
                        },
                    )
                elif lang_id in ["shellscript", "bash"]:
                    lang_config.update(
                        {
                            "begin": "",
                            "end": "",
                            "prefix": "# ",
                        },
                    )
                elif lang_id in ["html", "xml"]:
                    lang_config.update(
                        {
                            "begin": "<!--",
                            "end": "-->",
                            "prefix": "",
                        },
                    )
                elif lang_id == "css":
                    lang_config.update(
                        {
                            "begin": "/*",
                            "end": "*/",
                            "prefix": "",
                        },
                    )
                else:
                    # Default for most languages (JavaScript, TypeScript, Go, etc.)
                    lang_config.update(
                        {
                            "begin": "",
                            "end": "",
                            "prefix": "// ",
                        },
                    )

                lang_configs.append(lang_config)

        settings["psi-header.lang-config"] = lang_configs

        return settings

    def update_dev_sh(self) -> None:
        """Update dev.sh with project settings."""
        source_file = self.source_dir / "dev.sh"
        target_file = Path(self.config.project_path) / "dev.sh"

        if not source_file.exists():
            return

        with open(source_file) as f:
            content = f.read()

        # Replace variables
        content = re.sub(
            r'docker_exec_command="[^"]*"',
            f'docker_exec_command="{self.config.docker_exec_command}"',
            content,
        )
        content = re.sub(
            r'project_name="[^"]*"',
            f'project_name="{self.config.project_name}"',
            content,
        )
        content = re.sub(
            r'container_name="[^"]*"',
            f'container_name="{self.config.container_name}"',
            content,
        )

        with open(target_file, "w") as f:
            f.write(content)

        # Make executable
        os.chmod(target_file, 0o744)

    def update_pyproject_toml(self) -> None:
        """Update pyproject.toml with Python project configuration."""
        target_file = Path(self.config.project_path) / "pyproject.toml"

        if not target_file.exists():
            return

        # Read and update pyproject.toml
        with open(target_file) as f:
            content = f.read()

        # Replace project name
        if self.config.python_project_name:
            content = re.sub(
                r'name = "my-awesome-project"',
                f'name = "{self.config.python_project_name}"',
                content,
            )

        # Replace description
        if self.config.python_project_description:
            content = re.sub(
                r'description = "A brief description of your project"',
                f'description = "{self.config.python_project_description}"',
                content,
            )

        # Replace required Python version
        if self.config.python_requires_python:
            content = re.sub(
                r'requires-python = ">=3\.12"',
                f'requires-python = "{self.config.python_requires_python}"',
                content,
            )

        # Replace author information
        if self.config.python_author_name and self.config.python_author_email:
            content = re.sub(
                r'\{ name = "Your Name", email = "your\.email@example\.com" \}',
                f'{{ name = "{self.config.python_author_name}", email = "{self.config.python_author_email}" }}',
                content,
            )
        elif self.config.python_author_name:
            content = re.sub(
                r'\{ name = "Your Name", email = "your\.email@example\.com" \}',
                f'{{ name = "{self.config.python_author_name}" }}',
                content,
            )

        # Replace project URLs
        if self.config.python_homepage_url:
            content = re.sub(
                r'Homepage = "https://github\.com/yourusername/my-awesome-project"',
                f'Homepage = "{self.config.python_homepage_url}"',
                content,
            )

        if self.config.python_source_url:
            content = re.sub(
                r'Source = "https://github\.com/yourusername/my-awesome-project"',
                f'Source = "{self.config.python_source_url}"',
                content,
            )

        # Replace package index URL
        if self.config.python_index_url:
            content = re.sub(
                r'index-url = "https://pypi\.org/simple/"',
                f'index-url = "{self.config.python_index_url}"',
                content,
            )

        # Replace package path in build targets
        if self.config.python_packages_path:
            content = re.sub(
                r'packages = \["src/my_awesome_project"\]',
                f'packages = ["{self.config.python_packages_path}"]',
                content,
            )

            # Also update version path if it follows the same pattern
            if "src/" in self.config.python_packages_path:
                package_name = self.config.python_packages_path.replace("src/", "").replace("/", "_")
                content = re.sub(
                    r'path = "src/my_awesome_project/__about__\.py"',
                    f'path = "src/{package_name}/__about__.py"',
                    content,
                )

            # Update coverage source packages
            if self.config.python_project_name:
                safe_project_name = self.config.python_project_name.replace("-", "_")
                content = re.sub(
                    r'source_pkgs = \["my_awesome_project", "tests"\]',
                    f'source_pkgs = ["{safe_project_name}", "tests"]',
                    content,
                )
                content = re.sub(
                    r'project = \["src", "\*/my_awesome_project/src"\]',
                    f'project = ["src", "*/{safe_project_name}/src"]',
                    content,
                )
                content = re.sub(
                    r'tests = \["tests", "\*/my_awesome_project/tests"\]',
                    f'tests = ["tests", "*/{safe_project_name}/tests"]',
                    content,
                )
                content = re.sub(
                    r'omit = \[\s*"src/my_awesome_project/__about__\.py",\s*\]',
                    f'omit = [\n  "src/{safe_project_name}/__about__.py",\n]',
                    content,
                )

        # Replace license
        if self.config.python_license:
            content = re.sub(
                r'license = \{text = "MIT"\}',
                f'license = {{text = "{self.config.python_license}"}}',
                content,
            )

        # Replace keywords
        if self.config.python_keywords:
            keywords_list = [f'"{kw.strip()}"' for kw in self.config.python_keywords.split(",") if kw.strip()]
            keywords_str = ", ".join(keywords_list)
            content = re.sub(
                r'keywords = \["python", "cli", "automation"\]',
                f"keywords = [{keywords_str}]",
                content,
            )

        # Configure Hatch publishing based on repository settings
        content = self.__update_hatch_publish_config(content)

        with open(target_file, "w") as f:
            f.write(content)
        if self.config.python_keywords:
            keywords_list = [f'"{kw.strip()}"' for kw in self.config.python_keywords.split(",") if kw.strip()]
            keywords_str = ", ".join(keywords_list)
            content = re.sub(
                r'keywords = \["python", "package"\]',
                f"keywords = [{keywords_str}]",
                content,
            )

        # Replace repository URL if GitHub info provided
        if self.config.python_github_username and self.config.python_github_project:
            repo_url = f"https://github.com/{self.config.python_github_username}/{self.config.python_github_project}"
            content = re.sub(
                r'repository = "https://github\.com/yourusername/your-repo"',
                f'repository = "{repo_url}"',
                content,
            )

        # Configure Hatch publishing based on repository settings
        content = self.__update_hatch_publish_config(content)

        with open(target_file, "w") as f:
            f.write(content)

        # Create environment variables example file if repository is configured
        if self.config.install_python_repository:
            self.__create_environment_variables_example()

    def __create_environment_variables_example(self) -> None:
        """Create an example .env file with the required environment variables for publishing."""
        env_file = Path(self.config.project_path) / ".env.example"

        repo_type = self.config.python_repository_type or "pypi"
        publish_url = self.config.python_publish_url or "https://upload.pypi.org/legacy/"

        env_content = f"""# Environment Variables for Python Package Publishing
# Copy this file to .env and fill in your actual credentials
# Note: Never commit .env files with real credentials to version control

# Repository Type: {repo_type.title()}
# Repository URL: {publish_url}

"""

        if repo_type == "pypi":
            env_content += """# PyPI Credentials (get token from https://pypi.org/manage/account/)
HATCH_INDEX_USER=__token__
HATCH_INDEX_AUTH=your_pypi_api_token_here

# For TestPyPI (testing), uncomment these instead:
# HATCH_INDEX_USER=__token__
# HATCH_INDEX_AUTH=your_testpypi_api_token_here
# HATCH_INDEX_REPO=https://test.pypi.org/legacy/
"""
        elif repo_type == "artifactory":
            env_content += f"""# Artifactory Credentials
HATCH_INDEX_USER=your_artifactory_username
HATCH_INDEX_AUTH=your_artifactory_password_or_token
HATCH_INDEX_REPO={publish_url}

# For development repository, you might use:
# HATCH_INDEX_REPO={publish_url.replace("-prod", "-dev") if "-prod" in publish_url else publish_url + "-dev"}
"""
        elif repo_type == "nexus":
            env_content += f"""# Nexus Credentials
HATCH_INDEX_USER=your_nexus_username
HATCH_INDEX_AUTH=your_nexus_password_or_token
HATCH_INDEX_REPO={publish_url}

# For development repository, you might use:
# HATCH_INDEX_REPO={publish_url.replace("-prod", "-dev") if "-prod" in publish_url else publish_url + "-dev"}
"""
        else:
            env_content += f"""# Custom Repository Credentials
HATCH_INDEX_USER=your_username
HATCH_INDEX_AUTH=your_password_or_token
HATCH_INDEX_REPO={publish_url}
"""

        env_content += """
# Usage Instructions:
# 1. Copy this file: cp .env.example .env
# 2. Edit .env with your actual credentials
# 3. Load environment: source .env
# 4. Publish package: hatch publish
#
# For dev containers:
# - HATCH_INDEX_REPO has been automatically configured in .devcontainer/devcontainer.json
# - Set HATCH_INDEX_USER and HATCH_INDEX_AUTH in your local environment:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
# - These will be automatically passed to the dev container on startup
"""

        with open(env_file, "w") as f:
            f.write(env_content)

    def __update_hatch_publish_config(self, content: str) -> str:
        """Update the [tool.hatch.publish.index] section based on repository configuration."""
        if not self.config.install_python_repository:
            # If repository publishing is disabled, set disable = true
            hatch_config = """
[tool.hatch.publish.index]
disable = true"""
        else:
            # Generate environment variable configuration based on repository type
            repo_type = self.config.python_repository_type or "pypi"
            publish_url = self.config.python_publish_url or "https://upload.pypi.org/legacy/"

            # Create specific instructions based on repository type
            if repo_type == "pypi":
                auth_instructions = """# For PyPI (python.org):
#   export HATCH_INDEX_USER=__token__
#   export HATCH_INDEX_AUTH=your_pypi_api_token
#   hatch publish"""
                env_example = """# Environment variables for PyPI publishing:
export HATCH_INDEX_USER=__token__
export HATCH_INDEX_AUTH=your_pypi_api_token"""
            elif repo_type == "artifactory":
                auth_instructions = f"""# For Artifactory repository:
#   export HATCH_INDEX_USER=your_artifactory_username
#   export HATCH_INDEX_AUTH=your_artifactory_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for Artifactory publishing:
export HATCH_INDEX_USER=your_artifactory_username
export HATCH_INDEX_AUTH=your_artifactory_password_or_token
export HATCH_INDEX_REPO={publish_url}"""
            elif repo_type == "nexus":
                auth_instructions = f"""# For Nexus repository:
#   export HATCH_INDEX_USER=your_nexus_username
#   export HATCH_INDEX_AUTH=your_nexus_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for Nexus publishing:
export HATCH_INDEX_USER=your_nexus_username
export HATCH_INDEX_AUTH=your_nexus_password_or_token
export HATCH_INDEX_REPO={publish_url}"""
            else:
                auth_instructions = f"""# For custom repository:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
#   export HATCH_INDEX_REPO={publish_url}
#   hatch publish"""
                env_example = f"""# Environment variables for custom repository publishing:
export HATCH_INDEX_USER=your_username
export HATCH_INDEX_AUTH=your_password_or_token
export HATCH_INDEX_REPO={publish_url}"""

            hatch_config = f"""
[tool.hatch.publish.index]
disable = false  # Set to true to disable publishing entirely

# Repository Configuration for {repo_type.title()}
# Repository URL: {publish_url}
#
# IMPORTANT: Set these environment variables for authentication and repository:
{auth_instructions}
#
# Copy and customize these environment variables:
{env_example}
#
# For development containers, add these to your .devcontainer/devcontainer.json:
# "containerEnv": {{
#   "HATCH_INDEX_USER": "${{localEnv:HATCH_INDEX_USER}}",
#   "HATCH_INDEX_AUTH": "${{localEnv:HATCH_INDEX_AUTH}}",
#   "HATCH_INDEX_REPO": "{publish_url}"
# }}
#
# NOTE: If using install.py, these containerEnv variables are automatically configured!
#
# Repository configuration via environment variables (recommended for containers):
# - HATCH_INDEX_USER: Username for authentication
# - HATCH_INDEX_AUTH: Password/token for authentication
# - HATCH_INDEX_REPO: Repository URL (overrides default PyPI)"""

        # Replace the entire [tool.hatch.publish.index] section
        # First, find and remove any existing hatch publish configuration
        pattern = r"\[tool\.hatch\.publish\.index\].*?(?=\n\[|\nTODO|\n$|\Z)"
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

        # Also remove any old repos configurations that might exist
        pattern = r"\[tool\.hatch\.publish\.index\.repos\.[^\]]+\].*?(?=\n\[|\n$|\Z)"
        content = re.sub(pattern, "", content, flags=re.DOTALL | re.MULTILINE)

        # Remove multiple consecutive blank lines
        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Find the end of the hatch publish comment section and add our config
        insertion_point = content.find("# To publish to a specific repository:")
        if insertion_point != -1:
            # Find the end of the comment block
            lines = content[insertion_point:].split("\n")
            comment_end = insertion_point
            for i, line in enumerate(lines):
                if line.startswith("#") or line.strip() == "":
                    comment_end = insertion_point + len("\n".join(lines[: i + 1]))
                else:
                    break

            # Insert our configuration after the comments
            content = content[:comment_end] + "\n" + hatch_config + "\n" + content[comment_end:]
        else:
            # Fallback: add at the end
            content += "\n" + hatch_config + "\n"

        # Check if hatch publish config already exists and replace it
        if "[tool.hatch.publish.index]" in content:
            # Replace existing configuration
            # Find the start and end of the hatch publish section
            pattern = r"\[tool\.hatch\.publish\.index\].*?(?=\n\[|$)"
            content = re.sub(pattern, hatch_config.strip(), content, flags=re.DOTALL)
        else:
            # Append new configuration
            content += "\n" + hatch_config

        # Return the updated content
        return content

    def configure_psi_header(self) -> None:
        """Configure PSI Header extension settings."""
        if not self.config.install_psi_header:
            return

        settings_dir = Path(self.config.project_path) / ".vscode"
        settings_file = settings_dir / "settings.json"

        settings_dir.mkdir(exist_ok=True)

        # Basic PSI Header configuration
        psi_config: dict[str, Any] = {
            "psi-header.config": {
                "forceToTop": True,
                "blankLinesAfter": 1,
                "license": "Custom",
            },
            "psi-header.templates": [],
        }

        # Add company name if provided
        if self.config.psi_header_company:
            psi_config["psi-header.config"]["company"] = self.config.psi_header_company

        # Add language-specific templates
        for lang_id, _lang_name in self.config.psi_header_templates:
            template_config: dict[str, Any] = {
                "language": lang_id,
                "template": [
                    f"Copyright (c) {self.config.psi_header_company or 'Company'} - All Rights Reserved",
                    f"Project: {self.config.project_name}",
                    "Author: <<author>>",
                    "Date: <<date>>",
                    "",
                    "This source code is licensed under the license found in the",
                    "LICENSE file in the root directory of this source tree.",
                ],
            }
            psi_config["psi-header.templates"].append(template_config)

        # Read existing settings or create new
        existing_settings: dict[str, Any] = {}
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    existing_settings = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_settings = {}

        # Merge PSI Header settings
        existing_settings.update(psi_config)

        # Write updated settings

        with open(settings_file, "w") as f:
            json.dump(existing_settings, f, indent=2)

    def configure_python_repository_settings(self) -> None:
        """Configure Python repository settings if needed."""
        if not self.config.install_python_tools:
            return

        # Update pip.conf or similar configuration files
        pip_dir = Path(self.config.project_path) / ".pip"
        pip_conf = pip_dir / "pip.conf"

        if self.config.python_index_url and self.config.python_index_url != "https://pypi.org/simple/":
            pip_dir.mkdir(exist_ok=True)

            config_content = [
                "[global]",
                f"index-url = {self.config.python_index_url}",
            ]

            if self.config.python_extra_index_url:
                config_content.append(f"extra-index-url = {self.config.python_extra_index_url}")

            with open(pip_conf, "w") as f:
                f.write("\n".join(config_content) + "\n")

    def show_completion(self) -> None:
        """Show completion message and exit."""
        console = Console()
        console.print("\n[bold green]Installation completed successfully![/bold green]")
        console.print("\n[cyan]Project Settings Applied:[/cyan]")
        console.print(f"  Project Name: {self.config.project_name}")
        console.print(f"  Container Name: {self.config.container_name}")
        console.print(f"  Display Name: {self.config.display_name}")

        if self.config.docker_exec_command:
            console.print(f"  Docker Exec Command: {self.config.docker_exec_command}")

        console.print("\n[cyan]Next steps:[/cyan]")
        console.print("1. [yellow]Recommended:[/yellow] Set GITHUB_TOKEN environment variable")

        # Add Python repository configuration instructions if enabled
        if self.config.install_python_repository:
            env_file = Path(self.config.project_path) / ".env.example"
            if env_file.exists():
                console.print(
                    "2. [yellow]Python Publishing:[/yellow] Environment variables automatically configured",
                )
                console.print(f"   • Review: {env_file}")
                console.print("   • Set HATCH_INDEX_USER and HATCH_INDEX_AUTH in your local environment")
                console.print("   • HATCH_INDEX_REPO automatically configured in devcontainer.json")
                console.print("   • Variables will be passed to dev container on startup")
                console.print(f"3. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
                console.print(f"4. Review tool versions in {self.config.project_path}/.mise.toml")
            else:
                console.print(f"2. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
                console.print(f"3. Review tool versions in {self.config.project_path}/.mise.toml")
        else:
            console.print(f"2. Review settings in {self.config.project_path}/.devcontainer/devcontainer.json")
            console.print(f"3. Review tool versions in {self.config.project_path}/.mise.toml")

        console.print(f"\n[blue]You can now run:[/blue] cd {self.config.project_path} && ./dev.sh")

        # Exit after showing completion
        self.app.call_later(self.app.exit)


class DynamicDevContainerApp(App[None]):
    """Main application class."""

    CSS_PATH = "install.tcss"
    TITLE = "Dynamic Dev Container Setup"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, project_path: str = "", start_screen: int | None = None, start_item: int | None = None) -> None:
        """Initialize the Dynamic Dev Container application.

        Parameters
        ----------
        project_path : str, optional
            Path where the dev container will be created, by default ""
        start_screen : int | None, optional
            Screen number to start at (0=Welcome, 1=Config, 2=Tools, 3=Extensions, 4=Summary, 5=Install), by default None
        start_item : int | None, optional
            Extension section item to start at (only valid with start_screen=3), by default None

        Raises
        ------
        FileNotFoundError
            If required template files are not found in the current directory

        """
        super().__init__()
        self.config = ProjectConfig()
        self.config.project_path = project_path
        self.source_dir = Path.cwd()  # Assume running from source directory

        # Store startup navigation parameters
        self.start_screen = start_screen
        self.start_item = start_item

        # Verify required files exist
        if not (self.source_dir / ".devcontainer" / "devcontainer.json").exists():
            msg = "Required template files not found. Must run from dynamic-dev-container directory."
            raise FileNotFoundError(msg)

        # Parse .mise.toml
        self.sections, self.tool_selected, self.tool_version_value, self.tool_version_configurable = (
            MiseParser.parse_mise_sections(self.source_dir / ".mise.toml")
        )

        # Start background loading of tool descriptions
        self.__start_background_description_loading()

        logger.debug("DynamicDevContainerApp initialized successfully")

    def __start_background_description_loading(self) -> None:
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
        """Called when app is mounted."""
        if self.start_screen is not None:
            # Jump directly to specified screen
            self.__jump_to_screen(self.start_screen, self.start_item)
        else:
            # Normal flow: start with welcome screen
            self.push_screen(WelcomeScreen(), self.after_welcome)

    def __jump_to_screen(self, screen: int, item: int | None = None) -> None:
        """Jump directly to a specific screen, bypassing earlier screens.

        Parameters
        ----------
        screen : int
            Screen number to jump to (0-5)
        item : int | None, optional
            Extension section item to start at (only valid with screen=3), by default None

        """
        # Set default project path for development convenience
        if not self.config.project_path:
            self.config.project_path = str(Path.home() / "my-project")

        # Set default project name based on path
        if not self.config.project_name:
            self.config.project_name = Path(self.config.project_path).name

        logger.debug("Jumping to screen %d, item %s", screen, item)

        if screen == SCREEN_WELCOME:  # Welcome
            self.push_screen(WelcomeScreen(), self.after_welcome)
        elif screen == SCREEN_CONFIG:  # Config
            self.push_screen(ProjectConfigScreen(self.config), self.after_project_config)
        elif screen == SCREEN_TOOLS:  # Tools
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
        elif screen == SCREEN_EXTENSIONS:  # Extensions
            # Create PSI Header screen with custom starting item
            psi_screen = ExtensionSelectionScreen(self.config, self.source_dir)
            if item is not None:
                # Set the starting section for the extensions screen
                if 0 <= item < len(psi_screen.section_names):
                    psi_screen.current_section = item
                    logger.debug("Set starting extension section to %d (%s)", item, psi_screen.section_names[item])
                else:
                    logger.warning("Invalid item %d for extensions screen, using 0", item)
                    psi_screen.current_section = 0
            self.push_screen(psi_screen, self.after_extensions)
        elif screen == SCREEN_SUMMARY:  # Summary
            self.push_screen(SummaryScreen(self.config), lambda _: None)
        elif screen == SCREEN_INSTALL:  # Install
            self.push_screen(InstallationScreen(self.config, self.source_dir), lambda _: None)
        else:
            logger.error("Invalid screen number: %d", screen)
            # Fallback to welcome screen
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

        # Python repository configuration is now handled inline in ToolSelectionScreen
        # Version configuration is also handled inline in ToolSelectionScreen
        # Skip the separate screens and go directly to Extension configuration
        self.show_extension_config()

    def after_python_repository(self, _result: None = None) -> None:
        """Called after Python repository configuration."""
        # Continue to Extension configuration
        self.show_extension_config()

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
            # Show Extensions configuration
            self.show_extension_config()

    def after_tool_versions(self, _result: None = None) -> None:
        """Called after tool version configuration."""
        # Show Extensions configuration
        self.show_extension_config()

    def show_extension_config(self) -> None:
        """Show Dev Container Extensions configuration screen."""
        self.push_screen(ExtensionSelectionScreen(self.config, self.source_dir), self.after_extensions)

    def after_extensions(self, _result: None = None) -> None:
        """Called after Dev Container Extensions configuration."""
        # Now show summary
        self.push_screen(SummaryScreen(self.config), self.after_summary)

    def after_summary(self, _result: None = None) -> None:
        """Called after summary screen."""
        self.push_screen(InstallationScreen(self.config, self.source_dir))

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def main() -> None:
    """Main entry point for the Dynamic Dev Container TUI application.

    Parses command line arguments, sets up debugging if requested,
    and launches the Textual TUI application for configuring and
    generating development container configurations.
    """
    global DEBUG_MODE  # noqa: PLW0603  # Needed for CLI debug configuration

    parser = argparse.ArgumentParser(
        description="Dynamic Dev Container TUI Setup - Python Version",
        epilog="This script creates a development container configuration with a Terminal User Interface.",
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        help="Path where the dev container will be created",
    )
    parser.add_argument(
        "--help-extended",
        action="store_true",
        help="Show extended help and examples",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging and debug panel",
    )
    parser.add_argument(
        "--screen",
        type=int,
        metavar="N",
        help="Start at specific screen (0=Welcome, 1=Config, 2=Tools, 3=Extensions, 4=Summary, 5=Install)",
    )
    parser.add_argument(
        "--item",
        type=int,
        metavar="N",
        help="Start at specific extension section item (only valid with --screen 3)",
    )

    args = parser.parse_args()

    # Validate screen and item parameters
    if args.screen is not None:
        if args.screen < USER_SCREEN_MIN or args.screen > USER_SCREEN_MAX:
            parser.error(
                f"--screen must be between {USER_SCREEN_MIN} and {USER_SCREEN_MAX} (1=Welcome, 2=Config, 3=Tools, 4=Extensions, 5=Summary, 6=Install)",
            )

        if args.item is not None:
            if args.screen != (SCREEN_EXTENSIONS + 1):  # Convert to 1-based for comparison
                parser.error("--item can only be used with --screen 4 (Extensions screen)")
            if args.item < USER_ITEM_MIN or args.item > USER_ITEM_MAX:
                parser.error(
                    f"--item must be between {USER_ITEM_MIN} and {USER_ITEM_MAX} (1=Github, 2=Markdown, 3=Shell/Bash, 4=PSI Header)",
                )
    elif args.item is not None:
        parser.error("--item requires --screen 4 to be specified")

    # Update debug mode based on command line argument
    if args.debug:
        DEBUG_MODE = True
        # Reconfigure logging for debug mode
        setup_logging(DEBUG_MODE)

    if args.help_extended:
        print("""
Dynamic Dev Container TUI Setup

This app creates a new dev container implementation for the tooling environment you select during setup.

Usage: python install.py [project_path] [--debug]

Arguments:
  project_path    Path where the dev container will be created
                  If not provided, you'll be prompted to enter it

Options:
  --debug         Enable debug mode with verbose logging and debug panel
                  Press Ctrl+D in the tool selection screen to toggle debug output

Examples:
  python install.py ~/my-project
  python install.py /workspace/new-project --debug
  python install.py  # Will prompt for path
  DEBUG=true python install.py  # Enable debug via environment variable

Requirements:
  - Python 3.9 or higher
  - Dependencies will be auto-installed: textual, rich, toml

The script must be run from the root of the dynamic-dev-container project
directory where the template files (.devcontainer/devcontainer.json, .mise.toml)
are located.
        """)
        return

    project_path = args.project_path or ""

    try:
        # Convert 1-based user input to 0-based internal values
        start_screen = args.screen - 1 if args.screen is not None else None
        start_item = args.item - 1 if args.item is not None else None

        app = DynamicDevContainerApp(project_path, start_screen, start_item)
        logger.debug("Application starting - Debug functionality available (Ctrl+D)")
        app.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("This script must be run from the root of the dynamic-dev-container project directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
