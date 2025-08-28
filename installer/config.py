"""Project configuration data container for the Dynamic Dev Container installer."""

from __future__ import annotations


class ProjectConfig:
    """Container for project configuration data."""

    def __init__(self) -> None:
        """Initialize the ProjectConfig with default values for project, tool, and extension settings."""
        # Project information
        self.project_path: str = ""
        self.project_name: str = ""
        self.display_name: str = ""
        self.container_name: str = ""
        self.docker_exec_command: str = ""

        # Tool selection
        self.install_sections: list[str] = []
        self.tool_selected: dict[str, bool] = {}
        self.tool_version_configurable: dict[str, bool] = {}
        self.tool_version_value: dict[str, str] = {}

        # Extension flags
        self.include_python_extensions: bool = False
        self.include_markdown_extensions: bool = False
        self.include_shell_extensions: bool = False
        self.include_js_extensions: bool = False

        # Python configuration
        self.install_python_tools: bool = False
        self.install_python_repository: bool = False
        self.python_publish_url: str = "https://upload.pypi.org/legacy/"
        self.python_index_url: str = "https://pypi.org/simple/"
        self.python_extra_index_url: str = ""
        self.python_dev_suffix: str = "dev"
        self.python_prod_suffix: str = "prod"
        self.python_repository_type: str = "PyPI"

        # Python project metadata
        self.python_project_name: str = ""
        self.python_project_description: str = ""
        self.python_author_name: str = ""
        self.python_author_email: str = ""
        self.python_github_username: str = ""
        self.python_github_project: str = ""
        self.python_license: str = ""
        self.python_keywords: str = ""

        # Additional pyproject.toml configuration
        self.python_requires_python: str = ">=3.12"
        self.python_homepage_url: str = ""
        self.python_source_url: str = ""
        self.python_documentation_url: str = ""
        self.python_packages_path: str = ""

        # PSI Header configuration
        self.install_psi_header: bool = False
        self.psi_header_company: str = ""
        self.psi_header_templates: list[tuple[str, str]] = []

        # Extension configuration
        self.selected_extension_sections: dict[str, bool] = {}
        self.selected_extensions: dict[str, bool] = {}
