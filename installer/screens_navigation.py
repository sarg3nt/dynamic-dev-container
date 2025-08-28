"""Base navigation screen for the Dynamic Dev Container installer.

This module contains the NavigationScreenBase class which provides common
functionality for screens that need section navigation and debug panel integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label

from installer.debug_utils import DebugMixin
from installer.logging_utils import get_logger

if TYPE_CHECKING:
    from textual.app import ComposeResult

# Initialize logger for this module
logger = get_logger(__name__)


class NavigationScreenBase(Screen[None], DebugMixin):
    """Base class for screens with navigation links and debug panel support.

    Provides common functionality for screens that need section navigation,
    debug panel integration, and consistent layout structure.
    """

    def __init__(self) -> None:
        """Initialize the navigation screen base."""
        super().__init__()
        self.current_section = 0
        self.total_sections = 0
        self.section_names: list[str] = []

    def create_navigation_layout(self, main_content: Container, container_id: str) -> ComposeResult:
        """Create the standard navigation layout with debug panel support.

        Parameters
        ----------
        main_content : Container
            The main content container
        container_id : str
            ID for the main container

        Yields
        ------
        ComposeResult
            The layout components

        """
        yield Header()

        # Create main layout container with debug panel at bottom if enabled - EXACTLY like ToolSelectionScreen
        layout_components = []
        layout_components.append(main_content)

        # Create vertical container with all components - EXACTLY like ToolSelectionScreen
        main_container = Container(*layout_components, id=container_id)
        yield main_container
        yield Footer()

    def create_navigation_links_container(self, links_id: str, populate_immediately: bool = False) -> Horizontal:
        """Create a navigation links container.

        Parameters
        ----------
        links_id : str
            ID for the links container
        populate_immediately : bool, optional
            Whether to populate the container with links immediately, by default False

        Returns
        -------
        Horizontal
            Navigation links container (empty or populated)

        """
        if populate_immediately:
            # Determine label text and link prefix
            if "extension" in links_id:
                label_text = "Extensions"
                link_id_prefix = "extension_link"
            else:
                label_text = "Tools"
                link_id_prefix = "section_link"

            # Create the label
            links_label = Label(f"{label_text}:", classes="sections-links-label")

            # Create navigation links
            navigation_links = self.create_navigation_links(link_id_prefix)

            # Create container with all children in constructor
            return Horizontal(
                links_label,
                *navigation_links,
                id=links_id,
                classes="compact-group",
            )

        # Create empty container
        return Horizontal(
            id=links_id,
            classes="compact-group",
        )

    def create_navigation_links(self, link_id_prefix: str) -> list[Button]:
        """Create navigation link buttons for sections.

        Parameters
        ----------
        link_id_prefix : str
            Prefix for button IDs (e.g., "section_link" or "extension_link")

        Returns
        -------
        list[Button]
            List of navigation link buttons

        """
        logger.debug("Creating navigation links for %d sections: %s", len(self.section_names), self.section_names)
        navigation_links = []

        for i, section in enumerate(self.section_names):
            # Create a display name for the section (capitalize and format nicely)
            display_name = section.replace("_", " ").replace("-", " ").title()
            logger.debug("Creating button %d: section='%s', display='%s'", i, section, display_name)

            # Create button with version-btn-small styling (like version buttons)
            if i == self.current_section:
                # Current section - make it look selected/active
                button_text = f"[bold]{display_name}[/bold]"
                section_btn = Button(
                    button_text,
                    id=f"{link_id_prefix}_{i}",
                    classes="version-btn-small",
                    disabled=True,  # Make current section non-clickable
                )
                section_btn.can_focus = False  # Make section buttons not focusable via tab
                logger.debug("Created CURRENT navigation button: %s (disabled)", section_btn.id)
            else:
                section_btn = Button(
                    display_name,
                    id=f"{link_id_prefix}_{i}",
                    classes="version-btn-small",
                )
                section_btn.can_focus = False  # Make section buttons not focusable via tab
                logger.debug("Created regular navigation button: %s", section_btn.id)

            navigation_links.append(section_btn)

        logger.debug("Created %d navigation links total", len(navigation_links))
        return navigation_links

    def refresh_navigation_links(self, links_container_id: str, link_id_prefix: str, label_text: str) -> None:
        """Refresh navigation links in the container.

        Parameters
        ----------
        links_container_id : str
            ID of the links container
        link_id_prefix : str
            Prefix for button IDs
        label_text : str
            Text for the links label

        """
        try:
            logger.debug("Refreshing navigation links for %s", links_container_id)

            # Get the navigation links container
            links_container = self.query_one(f"#{links_container_id}", Horizontal)
            logger.debug("Found %s container: %s", links_container_id, links_container)

            # Check if we already have buttons
            existing_buttons = links_container.query("Button")
            logger.debug("Found %d existing buttons", len(existing_buttons))

            # Always create links if container is empty (happens after navigation)
            if len(existing_buttons) == 0:
                logger.debug("Container is empty, creating navigation links")

                # Clear container first to ensure clean state
                links_container.remove_children()

                # Add the label
                links_label = Label(f"{label_text}:", classes="sections-links-label")
                links_container.mount(links_label)
                logger.debug("Mounted navigation label")

                # Create and mount navigation links
                navigation_links = self.create_navigation_links(link_id_prefix)
                logger.debug("Created %d navigation links", len(navigation_links))

                for i, nav_btn in enumerate(navigation_links):
                    logger.debug("About to mount navigation button %d: %s", i, nav_btn.label)
                    links_container.mount(nav_btn)
                    logger.debug("Successfully mounted navigation button %d", i)
            else:
                logger.debug("Buttons exist, updating their disabled state")

                # Get the current section name and transform it
                current_section_raw = self.section_names[self.current_section]
                current_section_name = current_section_raw.replace("_", " ").replace("-", " ").title()
                logger.debug("Current section name: %s", current_section_name)

                # Update existing buttons' disabled state
                for button in existing_buttons:
                    if hasattr(button, "label") and hasattr(button.label, "plain"):
                        section_name = button.label.plain
                        if section_name == current_section_name:
                            button.disabled = True
                            logger.debug("Disabled button for current section: %s", section_name)
                        else:
                            button.disabled = False
                            logger.debug("Enabled button for section: %s", section_name)

            # Force multiple layout refreshes to ensure visibility
            self.refresh()
            links_container.refresh()

            # Force a parent container refresh as well
            try:
                main_container = self.query_one("#main-content")
                main_container.refresh()
                logger.debug("Forced main-content container refresh")
            except Exception as e:
                logger.debug("Could not refresh main-content: %s", e)

            # Force the entire screen to recalculate layout
            self.call_later(lambda: self.refresh())

            logger.debug("Navigation links refresh completed")

        except Exception as e:
            logger.debug("ERROR in refresh_navigation_links: %s", e)
