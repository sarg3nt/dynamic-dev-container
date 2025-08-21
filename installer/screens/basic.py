"""Basic screen classes for the Dynamic Dev Container installer.

This module contains simple screen classes that provide core functionality
like welcome, summary, and installation screens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

try:
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.screen import Screen
    from textual.widgets import Button, Footer, Header, Label, Markdown
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    import sys

    sys.exit(1)

from installer import utils
from installer.utils import logger

from .mixins import DebugMixin

if TYPE_CHECKING:
    from pathlib import Path

    from textual.app import ComposeResult

    from installer.app import DynamicDevContainerApp
    from installer.config import ProjectConfig


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
            Label("Dynamic Dev Container Setup", classes="title"),
            Markdown(f"""Welcome to the **Dynamic Dev Container TUI Setup**!

This wizard will guide you through configuring your development container with the tools and extensions you need.

## System Status:
- Debug Mode: {"✅ Enabled" if utils.DEBUG_MODE else "❌ Disabled"}

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
        """Initialize the welcome screen when mounted.

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
        """Initialize the summary screen when mounted."""
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

        content.append(Markdown("\\n".join(details)))
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
                content.append(Markdown("**Selected Tools:**\\n" + "\\n".join(tools_info)))
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
            content.append(Markdown("\\n".join(psi_info)))
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

            # Python project details
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

            content.append(Markdown("\\n".join(python_info)))
        else:
            # Don't show this section if Python project is not configured
            pass

        return Container(*content, classes="summary-section")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "continue_btn":
            self.action_next()
        elif event.button.id == "back_btn":
            self.action_back()
        elif event.button.id == "copy_debug_btn":
            self._copy_debug_output()

    def action_next(self) -> None:
        """Continue to the installation screen."""
        app = cast("DynamicDevContainerApp", self.app)
        self.app.call_later(app.after_summary)
        self.app.pop_screen()

    def action_back(self) -> None:
        """Go back to the previous screen."""
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
                "Generating dev container files and configuration:\\n[dim]Please wait while your development environment is being configured.[/dim]",
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
        """Initialize the installation screen when mounted."""
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
