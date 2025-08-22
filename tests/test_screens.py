"""Tests for install.py - TUI Screen functionality tests."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the TUI classes we want to test
sys.path.insert(0, str(Path(__file__).parent.parent))

from install_new import (
    DynamicDevContainerApp,
    InstallationScreen,
    ProjectConfig,
    ProjectConfigScreen,
    SummaryScreen,
    ToolSelectionScreen,
    WelcomeScreen,
)


class TestProjectConfigScreen:
    """Test the ProjectConfigScreen class."""

    def test_screen_initialization(self) -> None:
        """Test that ProjectConfigScreen initializes correctly."""
        config = ProjectConfig()
        screen = ProjectConfigScreen(config)
        assert screen.config is config

    @patch("install.ProjectConfigScreen.query_one")
    def test_save_config_basic(self, mock_query_one) -> None:
        """Test basic configuration saving."""
        config = ProjectConfig()
        screen = ProjectConfigScreen(config)

        # Mock the input values
        mock_inputs = {
            "#project_name": Mock(value="test-project"),
            "#display_name": Mock(value="Test Project"),
            "#container_name": Mock(value="test-container"),
            "#docker_command": Mock(value="tp"),
        }

        def mock_query_side_effect(selector, widget_type):
            return mock_inputs[selector]

        mock_query_one.side_effect = mock_query_side_effect

        # Call save_config
        screen.save_config()

        # Check that config was updated
        assert config.project_name == "test-project"
        assert config.display_name == "Test Project"
        assert config.container_name == "test-container"
        assert config.docker_exec_command == "tp"

    @patch("install.ProjectConfigScreen.query_one")
    @patch("install.ProjectConfigScreen.notify")
    def test_save_config_empty_name(self, mock_notify, mock_query_one) -> None:
        """Test that empty project name triggers error."""
        config = ProjectConfig()
        screen = ProjectConfigScreen(config)

        # Mock empty project name
        mock_inputs = {
            "#project_name": Mock(value=""),
            "#display_name": Mock(value="Test Project"),
            "#container_name": Mock(value="test-container"),
            "#docker_command": Mock(value="tp"),
        }

        def mock_query_side_effect(selector, widget_type):
            return mock_inputs[selector]

        mock_query_one.side_effect = mock_query_side_effect

        # Call save_config - should trigger notification
        screen.save_config()

        # Check that error notification was called
        mock_notify.assert_called_once_with("Project name is required!", severity="error")

    @patch("install.ProjectConfigScreen.query_one")
    def test_save_config_defaults(self, mock_query_one) -> None:
        """Test that defaults are applied for empty values."""
        config = ProjectConfig()
        screen = ProjectConfigScreen(config)

        # Mock inputs with some empty values
        mock_inputs = {
            "#project_name": Mock(value="test-project"),
            "#display_name": Mock(value=""),  # Empty display name
            "#container_name": Mock(value=""),  # Empty container name
            "#docker_command": Mock(value="tp"),
        }

        def mock_query_side_effect(selector, widget_type):
            return mock_inputs[selector]

        mock_query_one.side_effect = mock_query_side_effect

        # Call save_config
        screen.save_config()

        # Check that defaults were applied
        assert config.project_name == "test-project"
        assert config.display_name == "test-project"  # Should default to project_name
        assert config.container_name == "test-project-container"  # Should default


class TestToolSelectionScreen:
    """Test the ToolSelectionScreen class."""

    def test_screen_initialization(self) -> None:
        """Test that ToolSelectionScreen initializes correctly."""
        config = ProjectConfig()
        sections = ["Python", "Kubernetes"]
        tool_selected = {"python": True, "kubectl": False}
        tool_version_configurable = {"python": True, "kubectl": False}
        tool_version_value = {"python": "3.12", "kubectl": "latest"}

        screen = ToolSelectionScreen(
            config,
            sections,
            tool_selected,
            tool_version_configurable,
            tool_version_value,
        )

        assert screen.config is config
        assert screen.sections == sections
        assert screen.tool_selected == tool_selected
        assert screen.current_section == 0

    def test_finalize_selection(self) -> None:
        """Test finalizing tool selection updates config correctly."""
        config = ProjectConfig()
        sections = ["Python", "Node Development"]
        tool_selected = {"python": True, "node": True, "kubectl": False}
        tool_version_configurable = {"python": True}
        tool_version_value = {"python": "3.12"}

        screen = ToolSelectionScreen(
            config,
            sections,
            tool_selected,
            tool_version_configurable,
            tool_version_value,
        )

        # Call finalize_selection
        screen.finalize_selection()

        # Check that config was updated
        assert config.tool_selected == tool_selected
        assert config.tool_version_configurable == tool_version_configurable
        assert config.tool_version_value == tool_version_value

        # Check that Python and JS extensions are enabled
        assert config.install_python_tools is True
        assert config.include_python_extensions is True
        assert config.include_js_extensions is True
        assert config.include_markdown_extensions is True
        assert config.include_shell_extensions is True


class TestSummaryScreen:
    """Test the SummaryScreen class."""

    def test_generate_summary_basic(self) -> None:
        """Test basic summary generation."""
        config = ProjectConfig()
        config.project_name = "test-project"
        config.display_name = "Test Project"
        config.container_name = "test-container"
        config.docker_exec_command = "tp"
        config.tool_selected = {"python": True, "kubectl": False}
        config.tool_version_value = {"python": "3.12", "kubectl": "latest"}
        config.include_python_extensions = True
        config.include_markdown_extensions = True

        screen = SummaryScreen(config)
        summary = screen.generate_summary()

        # Check that summary contains expected information
        assert "test-project" in summary
        assert "Test Project" in summary
        assert "test-container" in summary
        assert "tp" in summary
        assert "python" in summary
        assert "Python" in summary  # Extension
        assert "Markdown" in summary  # Extension

    def test_generate_summary_no_tools(self) -> None:
        """Test summary generation with no tools selected."""
        config = ProjectConfig()
        config.project_name = "empty-project"
        config.display_name = "Empty Project"
        config.container_name = "empty-container"
        config.tool_selected = {}

        screen = SummaryScreen(config)
        summary = screen.generate_summary()

        assert "empty-project" in summary
        assert "None selected" in summary

    def test_generate_summary_with_python_config(self) -> None:
        """Test summary generation with Python configuration."""
        config = ProjectConfig()
        config.project_name = "python-project"
        config.display_name = "Python Project"
        config.container_name = "python-container"
        config.install_python_tools = True
        config.python_publish_url = "https://pypi.org/simple/"
        config.python_repository_type = "pypi"
        config.python_project_name = "my-package"

        screen = SummaryScreen(config)
        summary = screen.generate_summary()

        assert "Python Configuration" in summary
        assert "pypi" in summary
        assert "https://pypi.org/simple/" in summary
        assert "my-package" in summary


class TestInstallationScreen:
    """Test the InstallationScreen class."""

    def test_screen_initialization(self, mock_source_dir) -> None:
        """Test that InstallationScreen initializes correctly."""
        config = ProjectConfig()
        config.project_path = "/test/project"

        screen = InstallationScreen(config, mock_source_dir)

        assert screen.config is config
        assert screen.source_dir == mock_source_dir
        assert screen.progress_step == 0
        assert screen.total_steps == 6

    @patch("install.InstallationScreen.query_one")
    def test_update_progress(self, mock_query_one) -> None:
        """Test progress update functionality."""
        config = ProjectConfig()
        screen = InstallationScreen(config, Path("/test"))

        # Mock the progress bar and status label
        mock_progress = Mock()
        mock_status = Mock()

        def mock_query_side_effect(selector, widget_type):
            if "progress" in selector:
                return mock_progress
            if "status" in selector:
                return mock_status

        mock_query_one.side_effect = mock_query_side_effect

        # Call update_progress
        screen.update_progress("Testing...")

        # Check that progress was updated
        assert screen.progress_step == 1
        mock_progress.update.assert_called_once_with(progress=1)
        mock_status.update.assert_called_once_with("Testing...")

    def test_create_project_directory(self, temp_dir) -> None:
        """Test project directory creation."""
        config = ProjectConfig()
        config.project_path = str(temp_dir / "new_project")

        screen = InstallationScreen(config, Path("/test"))
        screen.create_project_directory()

        # Check that directory was created
        assert Path(config.project_path).exists()
        assert Path(config.project_path).is_dir()


class TestDynamicDevContainerApp:
    """Test the main DynamicDevContainerApp class."""

    def test_app_initialization_with_path(self, mock_source_dir) -> None:
        """Test app initialization with project path."""
        with patch("install.Path.cwd", return_value=mock_source_dir):
            app = DynamicDevContainerApp("/test/project")

            assert app.config.project_path == "/test/project"
            assert app.source_dir == mock_source_dir

    def test_app_initialization_missing_files(self, temp_dir) -> None:
        """Test app initialization with missing required files."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with patch("install.Path.cwd", return_value=empty_dir):
            with pytest.raises(FileNotFoundError) as exc_info:
                DynamicDevContainerApp("/test/project")

            assert "Required template files not found" in str(exc_info.value)

    @patch("install.DynamicDevContainerApp.push_screen")
    def test_on_mount(self, mock_push_screen, mock_source_dir) -> None:
        """Test that on_mount pushes the welcome screen."""
        with patch("install.Path.cwd", return_value=mock_source_dir):
            app = DynamicDevContainerApp("/test/project")
            app.on_mount()

            # Check that WelcomeScreen was pushed
            mock_push_screen.assert_called_once()
            args = mock_push_screen.call_args[0]
            assert isinstance(args[0], WelcomeScreen)


@pytest.fixture
def sample_config_with_tools() -> ProjectConfig:
    """Create a sample ProjectConfig with tools selected."""
    config = ProjectConfig()
    config.project_name = "test-project"
    config.display_name = "Test Project"
    config.container_name = "test-container"
    config.docker_exec_command = "tp"
    config.tool_selected = {"python": True, "kubectl": True, "node": False}
    config.tool_version_value = {"python": "3.12", "kubectl": "latest", "node": "latest"}
    config.tool_version_configurable = {"python": True, "kubectl": False, "node": True}
    config.include_python_extensions = True
    config.include_markdown_extensions = True
    config.install_python_tools = True
    return config
