"""Tests for install.py - Core functionality tests."""

# Import the classes and functions we want to test
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from install import (
    FileManager,
    MiseParser,
    OSDetector,
    ProjectConfig,
    ToolManager,
)


class TestProjectConfig:
    """Test the ProjectConfig class."""

    def test_initialization(self):
        """Test that ProjectConfig initializes with correct defaults."""
        config = ProjectConfig()

        # Test project information defaults
        assert config.project_path == ""
        assert config.project_name == ""
        assert config.display_name == ""
        assert config.container_name == ""
        assert config.docker_exec_command == ""

        # Test tool selection defaults
        assert config.install_sections == []
        assert config.tool_selected == {}
        assert config.tool_version_configurable == {}
        assert config.tool_version_value == {}

        # Test extension flags defaults
        assert config.include_python_extensions is False
        assert config.include_markdown_extensions is False
        assert config.include_shell_extensions is False
        assert config.include_js_extensions is False

        # Test Python configuration defaults
        assert config.install_python_tools is False
        assert config.python_publish_url == "https://upload.pypi.org/legacy/"
        assert config.python_index_url == "https://pypi.org/simple/"
        assert config.python_repository_type == "PyPI"

        # Test PSI Header defaults
        assert config.install_psi_header is False
        assert config.psi_header_company == ""
        assert config.psi_header_templates == []


class TestOSDetector:
    """Test the OSDetector class."""

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    @patch("shutil.which")
    def test_detect_linux_dnf(self, mock_which, mock_exists, mock_system):
        """Test detection of DNF package manager on Linux."""
        mock_system.return_value = "linux"
        mock_exists.return_value = True
        mock_which.side_effect = lambda cmd: cmd == "dnf"

        with patch("builtins.open", mock_open_os_release("ID=fedora")):
            result = OSDetector.detect_os_and_package_manager()
            assert result == "dnf"

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    @patch("shutil.which")
    def test_detect_linux_apt(self, mock_which, mock_exists, mock_system):
        """Test detection of APT package manager on Linux."""
        mock_system.return_value = "linux"
        mock_exists.return_value = True
        mock_which.side_effect = lambda cmd: cmd == "apt-get"

        with patch("builtins.open", mock_open_os_release("ID=ubuntu")):
            result = OSDetector.detect_os_and_package_manager()
            assert result == "apt-get"

    @patch("platform.system")
    @patch("shutil.which")
    def test_detect_macos_brew(self, mock_which, mock_system):
        """Test detection of Homebrew on macOS."""
        mock_system.return_value = "darwin"
        mock_which.side_effect = lambda cmd: cmd == "brew"

        result = OSDetector.detect_os_and_package_manager()
        assert result == "brew"

    @patch("platform.system")
    def test_detect_unknown_system(self, mock_system):
        """Test detection of unknown system."""
        mock_system.return_value = "unknown_os"

        result = OSDetector.detect_os_and_package_manager()
        assert result == "unknown"

    def test_get_install_command_dnf(self):
        """Test getting install command for DNF."""
        result = OSDetector.get_install_command("dnf", "python3")
        expected = ["sudo", "dnf", "install", "-y", "python3"]
        assert result == expected

    def test_get_install_command_apt(self):
        """Test getting install command for APT."""
        result = OSDetector.get_install_command("apt", "python3")
        expected = ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y", "python3"]
        assert result == expected

    def test_get_install_command_unknown(self):
        """Test getting install command for unknown package manager."""
        result = OSDetector.get_install_command("unknown", "python3")
        assert result is None


class TestToolManager:
    """Test the ToolManager class."""

    def test_get_latest_major_versions_python(self):
        """Test getting latest major versions for Python."""
        result = ToolManager.get_latest_major_versions("python")
        assert "3.13" in result
        assert "3.12" in result
        assert "3.11" in result
        assert "3.10" in result

    def test_get_latest_major_versions_other_tool(self):
        """Test getting latest major versions for other tools."""
        result = ToolManager.get_latest_major_versions("kubectl")
        assert "latest version available" in result

    def test_get_tool_description_known_tool(self):
        """Test getting description for known tools."""
        assert "OpenTofu" in ToolManager.get_tool_description("opentofu")
        assert "Kubernetes" in ToolManager.get_tool_description("kubectl")
        assert "Python" in ToolManager.get_tool_description("python")

    def test_get_tool_description_unknown_tool(self):
        """Test getting description for unknown tool."""
        result = ToolManager.get_tool_description("unknown-tool")
        assert result == "unknown-tool - Development tool"


class TestMiseParser:
    """Test the MiseParser class."""

    def test_parse_mise_sections(self, mock_source_dir):
        """Test parsing .mise.toml sections."""
        mise_file = mock_source_dir / ".mise.toml"

        sections, tool_selected, tool_version_value, tool_version_configurable = MiseParser.parse_mise_sections(
            mise_file,
        )

        # Check that sections were found
        assert "Python" in sections
        assert "HashiCorp Tools" in sections
        assert "Kubernetes" in sections

        # Check that tools were parsed
        assert "python" in tool_selected
        assert "opentofu" in tool_selected
        assert "kubectl" in tool_selected

        # Check version configurability
        assert tool_version_configurable["python"] is True  # Has #version# marker
        assert tool_version_configurable["opentofu"] is True  # Has #version# marker
        assert tool_version_configurable["kubectl"] is False  # No marker

        # Check default values
        assert tool_version_value["python"] == "latest"
        assert tool_selected["python"] is False  # Default not selected

    def test_parse_mise_sections_missing_file(self, temp_dir):
        """Test parsing non-existent .mise.toml file."""
        missing_file = temp_dir / "missing.toml"

        sections, tool_selected, tool_version_value, tool_version_configurable = MiseParser.parse_mise_sections(
            missing_file,
        )

        assert sections == []
        assert tool_selected == {}
        assert tool_version_value == {}
        assert tool_version_configurable == {}

    def test_get_section_tools(self, mock_source_dir):
        """Test getting tools from a specific section."""
        mise_file = mock_source_dir / ".mise.toml"

        python_tools = MiseParser.get_section_tools(mise_file, "Python")
        assert python_tools == ["python"]

        hashicorp_tools = MiseParser.get_section_tools(mise_file, "HashiCorp Tools")
        assert "opentofu" in hashicorp_tools
        assert "packer" in hashicorp_tools

        # Test non-existent section
        empty_tools = MiseParser.get_section_tools(mise_file, "NonExistent")
        assert empty_tools == []


class TestFileManager:
    """Test the FileManager class."""

    def test_copy_files_and_directories_basic(self, mock_source_dir, temp_dir):
        """Test basic file and directory copying."""
        target_dir = temp_dir / "target"
        target_dir.mkdir()

        FileManager.copy_files_and_directories(mock_source_dir, target_dir, include_python=False)

        # Check that .devcontainer directory was copied
        assert (target_dir / ".devcontainer").exists()
        assert (target_dir / ".devcontainer" / "devcontainer.json").exists()

        # Check that basic files were copied
        assert (target_dir / "dev.sh").exists()
        assert (target_dir / "package.json").exists()

        # Check that Python files were NOT copied
        assert not (target_dir / "pyproject.toml").exists()
        assert not (target_dir / "requirements.txt").exists()

    def test_copy_files_and_directories_with_python(self, mock_source_dir, temp_dir):
        """Test file and directory copying with Python files."""
        target_dir = temp_dir / "target"
        target_dir.mkdir()

        FileManager.copy_files_and_directories(mock_source_dir, target_dir, include_python=True)

        # Check that Python files were copied
        assert (target_dir / "pyproject.toml").exists()
        assert (target_dir / "requirements.txt").exists()
        assert (target_dir / "pybuild.py").exists()

    def test_copy_files_and_directories_missing_source(self, temp_dir):
        """Test copying from non-existent source directory."""
        source_dir = temp_dir / "missing_source"
        target_dir = temp_dir / "target"
        target_dir.mkdir()

        # Should not raise an error, just skip missing files
        FileManager.copy_files_and_directories(source_dir, target_dir, include_python=False)

        # Target should exist but be mostly empty
        assert target_dir.exists()


def mock_open_os_release(content):
    """Mock helper for /etc/os-release file content."""
    from unittest.mock import mock_open

    return mock_open(read_data=content)


@pytest.fixture
def sample_config():
    """Create a sample ProjectConfig for testing."""
    config = ProjectConfig()
    config.project_path = "/test/project"
    config.project_name = "test-project"
    config.display_name = "Test Project"
    config.container_name = "test-project-container"
    config.docker_exec_command = "tp"
    config.tool_selected = {"python": True, "kubectl": True}
    config.tool_version_value = {"python": "3.12", "kubectl": "latest"}
    config.include_python_extensions = True
    config.install_python_tools = True
    return config
