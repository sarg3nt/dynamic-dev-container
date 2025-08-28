"""Debug utilities for the Dynamic Dev Container installer.

This module provides debugging capabilities including a mixin class for screens
and a modal dialog for detailed debug output display.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from installer.constants import MAX_DEBUG_MESSAGES
from installer.logging_utils import tui_log_handler

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.containers import Container
    from textual.screen import Screen
    from textual.widgets import Button, RichLog

# Import required widgets - these need to be available at runtime
try:
    import pyperclip
    from textual.binding import Binding
    from textual.containers import Container, Horizontal
    from textual.css.query import NoMatches
    from textual.screen import ModalScreen
    from textual.widgets import Button, Label, RichLog
except ImportError as e:
    msg = f"Required UI dependencies not available: {e}"
    raise ImportError(msg) from e

# Get logger for this module
logger = logging.getLogger(__name__)


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
        self.__populate_debug_log(debug_log)

        return Container(
            Label("Debug Output:", classes="debug-title"),
            debug_log,
            id="debug_container",
            classes="debug-panel",
        )

    def __populate_debug_log(self, debug_log: RichLog) -> None:
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
            self.__populate_debug_log(debug_log)

            # Force a refresh to ensure content is displayed
            debug_log.refresh()

        except NoMatches:
            # Debug widget not found - this is normal when debug panel isn't shown
            pass
        except Exception as e:
            # Log any other errors for debugging
            logger.debug("Failed to update debug output: %s", e)

    def __rebuild_with_debug_panel(self) -> None:
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
                "#tools-container",  # Used by both ToolSelectionScreen and ExtensionSelectionScreen now
                "#main-content",
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
            self.__populate_debug_log(debug_log)

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
            logger.debug("DebugMixin: Debug panel created and mounted successfully")

        except Exception as e:
            logger.debug("DebugMixin: Error creating debug panel: %s", e)

    def __copy_debug_output(self) -> None:
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


class DebugModal(ModalScreen[None]):
    """Modal screen for showing debug output."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+d", "dismiss", "Close"),
        Binding("ctrl+c", "copy_debug", "Copy"),
    ]

    def compose(self) -> ComposeResult:
        """Create the debug modal layout."""
        debug_log = RichLog(
            max_lines=100,
            wrap=True,
            highlight=True,
            markup=True,
            id="modal_debug_log",  # Different ID to avoid conflicts
        )

        # Populate with existing debug messages
        messages = tui_log_handler.get_messages()
        for msg in messages[-50:]:  # Show last 50 messages
            debug_log.write(msg)

        yield Container(
            Container(
                Horizontal(
                    Label("Debug Output (Ctrl+D to close, Ctrl+C to copy)", classes="debug-title"),
                    Button("Copy", id="copy_debug_btn", classes="debug-copy-btn"),
                    Button("Close", id="close_debug_btn", variant="primary"),
                    id="debug-header",
                ),
                debug_log,
                id="debug_content",
                classes="debug-modal-content",
            ),
            id="debug_modal",
            classes="debug-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the debug modal.

        Parameters
        ----------
        event : Button.Pressed
            The button press event containing button information

        """
        if event.button.id == "copy_debug_btn":
            self.action_copy_debug()
        elif event.button.id == "close_debug_btn":
            self.dismiss()

    def action_copy_debug(self) -> None:
        """Copy debug output to clipboard.

        Attempts to copy all captured debug messages to the system clipboard
        and displays a notification to the user.

        """
        try:
            # Get all debug messages
            messages = tui_log_handler.get_messages()
            debug_text = "\n".join(messages)

            # Try to copy to clipboard
            pyperclip.copy(debug_text)
            self.notify("Debug output copied to clipboard!", timeout=2, severity="information")
        except ImportError:
            self.notify("pyperclip not available - cannot copy to clipboard", timeout=3, severity="warning")
        except Exception as e:
            self.notify(f"Failed to copy debug output: {e}", timeout=3, severity="error")

    async def action_dismiss(self, result: None = None) -> None:
        """Close the debug modal.

        Parameters
        ----------
        result : None, optional
            Result value to pass when dismissing, by default None

        """
        self.dismiss(result)
