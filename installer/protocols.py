# Add your template text here
"""Protocol definitions for the Dynamic Dev Container installer.

This module contains protocol definitions that define interfaces for
various components of the installer application.
"""

from __future__ import annotations

from typing import Protocol


class DevContainerApp(Protocol):
    """Protocol defining the interface needed by screens."""

    def after_welcome(self, result: None = None) -> None:
        """Called after welcome screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_project_config(self, result: None = None) -> None:
        """Called after project config screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_tool_selection(self, result: None = None) -> None:
        """Called after tool selection screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_python_repository(self, result: None = None) -> None:
        """Called after Python repository screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_python_project(self, result: None = None) -> None:
        """Called after Python project screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_tool_versions(self, result: None = None) -> None:
        """Called after tool versions screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_extensions(self, result: None = None) -> None:
        """Called after extension selection screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...

    def after_summary(self, result: None = None) -> None:
        """Called after summary screen completes.

        Parameters
        ----------
        result : None, optional
            Unused parameter for callback compatibility, by default None

        """
        ...
