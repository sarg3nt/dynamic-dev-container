"""Integration tests for install.py - End-to-end testing."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the main functionality
sys.path.insert(0, str(Path(__file__).parent.parent))

from install_new import (
    FileManager,
    ProjectConfig,
    main,
)


class TestEndToEndInstallation:
    """Test complete installation process."""

    def test_complete_file_generation(self, mock_source_dir: Path, temp_dir: Path) -> None:
        """Test that all expected files are generated correctly."""
        target_dir = temp_dir / "target_project"
        target_dir.mkdir()

        # Create a config with typical selections
        config = ProjectConfig()
        config.project_path = str(target_dir)
        config.project_name = "test-project"
        config.display_name = "Test Project"
        config.container_name = "test-project-container"
        config.docker_exec_command = "tp"
        config.tool_selected = {"python": True, "kubectl": True}
        config.tool_version_value = {"python": "3.12", "kubectl": "latest"}
        config.include_python_extensions = True
        config.install_python_tools = True
        config.python_project_name = "test-package"

        # Copy files
        FileManager.copy_files_and_directories(
            mock_source_dir,
            target_dir,
            include_python=config.install_python_tools,
        )

        # Verify all expected files exist
        expected_files = [
            ".devcontainer/devcontainer.json",
            "dev.sh",
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "pybuild.py",
        ]

        for file_path in expected_files:
            assert (target_dir / file_path).exists(), f"Missing file: {file_path}"

    def test_mise_toml_generation(self, mock_source_dir: Path, temp_dir: Path) -> None:
        """Test .mise.toml generation with selected tools."""
        target_dir = temp_dir / "target_project"
        target_dir.mkdir()

        # Mock installation screen behavior
        from install_new import InstallationScreen

        config = ProjectConfig()
        config.project_path = str(target_dir)
        config.tool_selected = {"python": True, "kubectl": True, "opentofu": False}
        config.tool_version_value = {"python": "3.12", "kubectl": "latest"}

        screen = InstallationScreen(config, mock_source_dir)
        screen.generate_mise_toml()

        # Check that .mise.toml was created
        mise_file = target_dir / ".mise.toml"
        assert mise_file.exists()

        # Check content
        content = mise_file.read_text()
        assert "python = '3.12'" in content
        assert "kubectl = 'latest'" in content
        assert "opentofu" not in content  # Not selected
        assert "#### Begin Python ####" in content
        assert "#### Begin Kubernetes ####" in content

    def test_devcontainer_json_generation(self, mock_source_dir: Path, temp_dir: Path) -> None:
        """Test devcontainer.json generation with customizations."""
        target_dir = temp_dir / "target_project"
        target_dir.mkdir()

        from install_new import InstallationScreen

        config = ProjectConfig()
        config.project_path = str(target_dir)
        config.project_name = "custom-project"
        config.display_name = "Custom Project"
        config.container_name = "custom-project-container"

        screen = InstallationScreen(config, mock_source_dir)
        screen.generate_devcontainer_json()

        # Check that devcontainer.json was created and modified
        devcontainer_file = target_dir / ".devcontainer" / "devcontainer.json"
        assert devcontainer_file.exists()

        content = devcontainer_file.read_text()
        assert '"name": "Custom Project"' in content
        assert "--name=custom-project-container" in content
        assert "custom-project-container-shellhistory" in content

    def test_dev_sh_customization(self, mock_source_dir: Path, temp_dir: Path) -> None:
        """Test dev.sh script customization."""
        target_dir = temp_dir / "target_project"
        target_dir.mkdir()

        from install_new import InstallationScreen

        config = ProjectConfig()
        config.project_path = str(target_dir)
        config.project_name = "my-app"
        config.container_name = "my-app-dev"
        config.docker_exec_command = "ma"

        # First copy the files
        FileManager.copy_files_and_directories(mock_source_dir, target_dir)

        screen = InstallationScreen(config, mock_source_dir)
        screen.update_dev_sh()

        # Check that dev.sh was customized
        dev_sh_file = target_dir / "dev.sh"
        assert dev_sh_file.exists()

        content = dev_sh_file.read_text()
        assert 'docker_exec_command="ma"' in content
        assert 'project_name="my-app"' in content
        assert 'container_name="my-app-dev"' in content

        # Check that file is executable
        assert os.access(dev_sh_file, os.X_OK)

    def test_pyproject_toml_customization(self, mock_source_dir: Path, temp_dir: Path) -> None:
        """Test pyproject.toml customization with Python project metadata."""
        target_dir = temp_dir / "target_project"
        target_dir.mkdir()

        from install_new import InstallationScreen

        config = ProjectConfig()
        config.project_path = str(target_dir)
        config.install_python_tools = True
        config.python_project_name = "awesome-package"
        config.python_project_description = "An awesome Python package"

        # First copy the files
        FileManager.copy_files_and_directories(
            mock_source_dir,
            target_dir,
            include_python=True,
        )

        screen = InstallationScreen(config, mock_source_dir)
        screen.update_pyproject_toml()

        # Check that pyproject.toml was customized
        pyproject_file = target_dir / "pyproject.toml"
        assert pyproject_file.exists()

        content = pyproject_file.read_text()
        assert 'name = "awesome-package"' in content
        assert 'description = "An awesome Python package"' in content


class TestMainFunction:
    """Test the main function and CLI interface."""

    @patch("install.DynamicDevContainerApp")
    def test_main_with_project_path(self, mock_app_class: Mock) -> None:
        """Test main function with project path argument."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Mock sys.argv
        test_args = ["install.py", "/test/project"]
        with patch("sys.argv", test_args):
            main()

        # Check that app was created with correct path
        mock_app_class.assert_called_once_with("/test/project")
        mock_app.run.assert_called_once()

    @patch("install.DynamicDevContainerApp")
    def test_main_without_project_path(self, mock_app_class: Mock) -> None:
        """Test main function without project path argument."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Mock sys.argv with just script name
        test_args = ["install.py"]
        with patch("sys.argv", test_args):
            main()

        # Check that app was created with empty path
        mock_app_class.assert_called_once_with("")
        mock_app.run.assert_called_once()

    def test_main_help_extended(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main function with extended help."""
        test_args = ["install.py", "--help-extended"]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "Python implementation" in captured.out
        assert "textual, rich, toml" in captured.out
        assert "Examples:" in captured.out

    @patch("install.DynamicDevContainerApp")
    def test_main_keyboard_interrupt(self, mock_app_class: Mock, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main function handling keyboard interrupt."""
        mock_app = Mock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_app_class.return_value = mock_app

        test_args = ["install.py", "/test/project"]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "Operation cancelled by user" in captured.out

    @patch("install.DynamicDevContainerApp")
    def test_main_file_not_found_error(self, mock_app_class: Mock, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main function handling FileNotFoundError."""
        mock_app_class.side_effect = FileNotFoundError("Required template files not found")

        test_args = ["install.py", "/test/project"]
        with patch("sys.argv", test_args), pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "Required template files not found" in captured.out
        assert "dynamic-dev-container project directory" in captured.out

    @patch("install.DynamicDevContainerApp")
    def test_main_unexpected_error(self, mock_app_class: Mock, capsys: pytest.CaptureFixture[str]) -> None:
        """Test main function handling unexpected errors."""
        mock_app_class.side_effect = RuntimeError("Unexpected error")

        test_args = ["install.py", "/test/project"]
        with patch("sys.argv", test_args), pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "Unexpected error" in captured.out


class TestDependencyManagement:
    """Test dependency installation and management."""

    @patch("subprocess.run")
    @patch("sys.executable", "/usr/bin/python3")
    def test_dependency_installation_success(self, mock_subprocess: Mock) -> None:
        """Test successful dependency installation."""
        from install_new import check_and_install_dependencies

        # Mock successful installation
        mock_subprocess.return_value = Mock(returncode=0)

        # Mock missing textual import
        with (
            patch("builtins.__import__", side_effect=ImportError("No module named 'textual'")),
        ):
            check_and_install_dependencies()

        # Verify pip install was called
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "/usr/bin/python3"
        assert args[1:3] == ["-m", "pip"]
        assert "install" in args
        assert any("textual" in arg for arg in args)

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_dependency_installation_failure(self, mock_print: Mock, mock_subprocess: Mock) -> None:
        """Test failed dependency installation."""
        from install_new import check_and_install_dependencies

        # Mock failed installation
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "pip")

        # Mock missing textual import
        with (
            patch("builtins.__import__", side_effect=ImportError("No module named 'textual'")),
            pytest.raises(SystemExit),
        ):
            check_and_install_dependencies()

        # Verify error message was printed
        mock_print.assert_any_call("Failed to install dependencies: Command 'pip' returned non-zero exit status 1.")
