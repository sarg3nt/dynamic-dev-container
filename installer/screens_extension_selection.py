"""Extension selection screen for the Dynamic Dev Container installer.

This module contains the ExtensionSelectionScreen class, which provides a user interface
for selecting and configuring VS Code extensions to install in the dev container.
It handles both standard extension sections and special PSI Header configuration.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from textual import log as logger
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.css.query import NoMatches
from textual.widgets import Button, Checkbox, Input, Label

from installer.devcontainer_parser import DevContainerParser
from installer.screens_navigation import NavigationScreenBase

if TYPE_CHECKING:
    from pathlib import Path

    from textual.app import ComposeResult

    from installer.config import ProjectConfig
    from installer.protocols import DevContainerApp


class ExtensionSelectionScreen(NavigationScreenBase):
    """Screen for Dev Container Extensions configuration."""

    BINDINGS = [
        ("ctrl+n", "next", "Next"),
        ("escape", "back", "Back"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+d", "toggle_debug", "Debug"),
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

    def save_current_section(self) -> None:
        """Save the configuration for the current section."""
        current_section_name = self.section_names[self.current_section]

        if current_section_name == "PSI Header":
            self.__save_psi_header_config()
        else:
            self.__save_extension_section_config(current_section_name)

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

    def save_config(self) -> None:
        """Save Dev Container Extensions configuration."""
        # Save current section first
        self.save_current_section()

        # Continue to next screen
        app = cast("DevContainerApp", self.app)
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

    def __mount_fresh_content(self) -> None:
        """Mount fresh content after removal is complete - EXACTLY like compose method."""
        main_container = self.query_one("#main-content")

        # Remove all children from the main-content container - FORCE COMPLETE REMOVAL
        main_container.remove_children()

        # Use call_later instead of call_after_refresh to ensure callback is executed
        self.call_later(self.__complete_content_refresh)

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
