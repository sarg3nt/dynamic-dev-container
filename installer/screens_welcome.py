"""Welcome screen for the Dynamic Dev Container installer.

This module contains the WelcomeScreen class which provides the initial
interface for the installer application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown

from installer.constants import DEBUG_MODE
from installer.debug_utils import DebugMixin
from installer.logging_utils import get_logger

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from installer.protocols import DevContainerApp

# Initialize logger for this module
logger = get_logger(__name__)


class WelcomeScreen(Screen[None], DebugMixin):
    """Welcome screen for the installer."""

    BINDINGS = [
        Binding("ctrl+n", "continue", "Next"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def compose(self) -> ComposeResult:
        """Create the layout for this screen."""
        yield Header()

        # Main content with scrollable markdown and fixed button at bottom
        yield Container(
            ScrollableContainer(
                Markdown(f"""
# Dynamic Dev Container Setup

Welcome to the **Dynamic Dev Container TUI Setup**!

This wizard will guide you through configuring your development container with the tools and extensions you need.

## System Status:
- Debug Mode: {"✅ Enabled" if DEBUG_MODE else "❌ Disabled"}

## Getting Started:
- Click **Next: Project Configuration** to start the wizard
- Press **Ctrl+N** to proceed to the next step
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
                """),
                id="welcome-scroll",
            ),
            Horizontal(
                Button("Project Configuration >>", id="next_btn", classes="nav-button"),
                id="button-row",
            ),
            id="welcome-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted.

        Sets up debug logging and periodic debug output updates for the welcome screen.
        Also sets focus on the Next button for immediate navigation.

        """
        logger.debug("WelcomeScreen mounted - Debug functionality available (Ctrl+D)")
        # Set up a timer to periodically update debug output
        self.set_interval(1.0, self.update_debug_output)

        # Set focus on the Next button when the screen loads
        try:
            next_button = self.query_one("#next_btn")
            next_button.focus()
            logger.debug("WelcomeScreen: Set focus on Next button")
        except Exception as e:
            logger.debug("WelcomeScreen: Could not set focus on Next button: %s", e)

    def action_continue(self) -> None:
        """Continue to the next screen.

        Triggers the transition to the project configuration screen.

        """
        # Call the next step directly
        app = cast("DevContainerApp", self.app)
        self.app.call_later(app.after_welcome)
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application.

        Exits the Textual application cleanly, terminating the TUI session.

        """
        self.app.exit()

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
            logger.debug("WelcomeScreen: Removed existing debug panel")
        except NoMatches:
            # Debug panel doesn't exist, create it
            logger.debug("WelcomeScreen: Creating new debug panel")
            self.__rebuild_with_debug_panel()
        except Exception as e:
            logger.debug("WelcomeScreen: Error toggling debug panel: %s", e)
            self.__rebuild_with_debug_panel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "copy_debug_btn":
            self.__copy_debug_output()
        elif event.button.id == "next_btn":
            self.action_continue()
