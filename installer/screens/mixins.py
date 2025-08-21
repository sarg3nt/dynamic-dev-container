"""Mixins for screen functionality.

This module contains reusable mixins that provide common functionality
to screen classes in the Dynamic Dev Container installer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

try:
    import pyperclip
    from textual.containers import Container, Horizontal
    from textual.css.query import NoMatches
    from textual.widgets import Button, Label, RichLog
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please ensure all dependencies are installed correctly.")
    import sys

    sys.exit(1)

from installer.utils import MAX_DEBUG_MESSAGES, logger, tui_log_handler

if TYPE_CHECKING:
    from textual.screen import Screen


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
        self._populate_debug_log(debug_log)

        return Container(
            Label("Debug Output:", classes="debug-title"),
            debug_log,
            id="debug_container",
            classes="debug-panel",
        )

    def _populate_debug_log(self, debug_log: RichLog) -> None:
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
            self._populate_debug_log(debug_log)

            # Force a refresh to ensure content is displayed
            debug_log.refresh()

        except NoMatches:
            # Debug widget not found - this is normal when debug panel isn't shown
            pass
        except Exception as e:
            # Log any other errors for debugging
            logger.debug("Failed to update debug output: %s", e)

    def _copy_debug_output(self) -> None:
        """Copy debug output to clipboard.

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

    def _rebuild_with_debug_panel(self) -> None:
        """Create and add debug panel to the screen.

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
                "#tools-container",
                "#main-content",
                "#psi-container",
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
            self._populate_debug_log(debug_log)

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
            logger.debug("DebugMixin: Successfully added debug panel to screen")

        except Exception as e:
            logger.debug("DebugMixin: Failed to create debug panel: %s", e)
