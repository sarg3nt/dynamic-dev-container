"""Header configuration screens for the Dynamic Dev Container installer.

This module contains screens for configuring file headers and templates.
"""

from __future__ import annotations

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

from installer.tools import DevContainerParser
from installer.utils import logger

from .mixins import DebugMixin

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from installer.app import DynamicDevContainerApp
    from installer.config import ProjectConfig


class PSIHeaderScreen(Screen[None], DebugMixin):
    """Screen for PSI Header configuration."""

    BINDINGS = [
        Binding("ctrl+n", "next", "Next"),
        Binding("escape", "back", "Back"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug", show=True),
    ]

    def __init__(self, config: ProjectConfig, source_dir: Path) -> None:
        """Initialize the PSI header screen.

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
        """Initialize the PSI Header screen when mounted."""
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
                # Import locally to avoid circular imports
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
            except Exception as e:
                # Skip if checkbox doesn't exist, but log for debugging
                logger.debug("Could not find checkbox for language %s: %s", lang_id, e)
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
            # Debug panel doesn't exist, create it
            self._rebuild_with_debug_panel()
