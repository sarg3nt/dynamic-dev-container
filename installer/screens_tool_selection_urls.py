"""Tool selection screen URL and package field management for the Dynamic Dev Container installer.

This module contains URL generation utilities and package field update functionality
for the ToolSelectionScreen class, including homepage/source/documentation URL
management and package name propagation.
"""

from __future__ import annotations

import re
import traceback

from textual import log as logger
from textual.css.query import NoMatches
from textual.widgets import Input


class ToolSelectionUrlMixin:
    """Mixin providing URL and package field management functionality for ToolSelectionScreen.

    This mixin requires the parent class to provide:
    - config: ProjectConfig instance for accessing project configuration
    - query_one: Method for querying Textual widgets by ID
    """

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
        """Get default homepage URL based on current package name.

        Returns
        -------
        str
            Default homepage URL using current package name

        """
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_source_url(self) -> str:
        """Get default source URL based on current package name.

        Returns
        -------
        str
            Default source URL using current package name

        """
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_url = package_name.lower().replace("_", "-").replace(" ", "-")
            return f"https://github.com/yourusername/{package_name_url}"
        return "https://github.com/yourusername/my-awesome-project"

    def __get_default_documentation_url(self) -> str:
        """Get default documentation URL based on current package name.

        Returns
        -------
        str
            Default documentation URL using current package name

        """
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
        """Get default package path based on current package name.

        Returns
        -------
        str
            Default package path using current package name

        """
        package_name = self.config.python_project_name
        if package_name and package_name != "my-awesome-project":
            package_name_clean = package_name.lower().replace("-", "_").replace(" ", "_")
            return f"src/{package_name_clean}"
        return "src/my_awesome_project"
