"""Test devcontainer.json generation functionality."""

import shutil
import tempfile
from pathlib import Path

import pytest
from install import InstallationScreen, ProjectConfig


class TestDevcontainerBasics:
    """Basic tests for devcontainer.json generation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        source_devcontainer = Path(".devcontainer/devcontainer.json")
        temp_devcontainer_dir = self.temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

    def teardown_method(self) -> None:
        """Clean up after test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_config(self, tools: dict[str, bool]) -> ProjectConfig:
        """Create a test configuration."""
        config = ProjectConfig()
        config.project_path = str(self.temp_dir)
        config.project_name = "test-project"
        config.display_name = "Test Project"
        config.container_name = "test-container"
        config.tool_selected = tools
        config.include_python_extensions = tools.get("python", False)
        config.include_js_extensions = tools.get("node", False)
        config.include_markdown_extensions = True
        config.include_shell_extensions = True
        return config

    def generate_devcontainer(self, config: ProjectConfig) -> str:
        """Generate devcontainer and return content."""
        screen = InstallationScreen(config, Path("."))
        screen.generate_devcontainer_json()

        generated_file = self.temp_dir / ".devcontainer" / "devcontainer.json"
        assert generated_file.exists()
        return generated_file.read_text()

    def test_python_extensions_included(self) -> None:
        """Test Python extensions are included when Python is selected."""
        config = self.create_test_config({"python": True})
        content = self.generate_devcontainer(config)

        assert "ms-python.python" in content
        assert "charliermarsh.ruff" in content
        assert "ms-python.mypy-type-checker" in content

    def test_go_extensions_included(self) -> None:
        """Test Go extensions are included when Go is selected."""
        config = self.create_test_config({"go": True})
        content = self.generate_devcontainer(config)

        assert "golang.go" in content
        assert "premparihar.gotestexplorer" in content  # Actual Go extension in template

    def test_dotnet_extensions_included(self) -> None:
        """Test .NET extensions are included when .NET is selected."""
        config = self.create_test_config({"dotnet": True})
        content = self.generate_devcontainer(config)

        assert "ms-dotnettools.csharp" in content
        assert "ms-dotnettools.csdevkit" in content

    def test_javascript_extensions_when_enabled(self) -> None:
        """Test JavaScript extensions are included when Node.js is selected and JS extensions enabled."""
        config = self.create_test_config({"node": True})
        config.include_js_extensions = True
        content = self.generate_devcontainer(config)

        assert "ms-vscode.vscode-typescript-next" in content
        assert "esbenp.prettier-vscode" in content

    def test_core_extensions_always_included(self) -> None:
        """Test core extensions are always included."""
        config = self.create_test_config({})
        content = self.generate_devcontainer(config)

        assert "GitHub.copilot" in content
        assert "GitHub.copilot-chat" in content
        assert "streetsidesoftware.code-spell-checker" in content

    def test_container_name_replacement(self) -> None:
        """Test container name is properly replaced."""
        config = self.create_test_config({})
        config.container_name = "my-custom-container"
        content = self.generate_devcontainer(config)

        assert "my-custom-container" in content
        assert "--name=my-custom-container" in content

    def test_display_name_replacement(self) -> None:
        """Test display name is properly replaced."""
        config = self.create_test_config({})
        config.display_name = "My Custom Project"
        content = self.generate_devcontainer(config)

        assert '"name": "My Custom Project"' in content

    def test_comments_preserved(self) -> None:
        """Test that comments are preserved in generated file."""
        config = self.create_test_config({})
        content = self.generate_devcontainer(config)

        assert "// Dev Container Configuration File" in content
        assert "// Build from Dockerfile" in content
        assert "// VS Code Settings" in content

    def test_python_settings_included(self) -> None:
        """Test Python settings are included when Python is selected."""
        config = self.create_test_config({"python": True})
        content = self.generate_devcontainer(config)

        assert "python.defaultInterpreterPath" in content
        assert "python.analysis.ignore" in content

    def test_go_settings_included(self) -> None:
        """Test Go settings are included when Go is selected."""
        config = self.create_test_config({"go": True})
        content = self.generate_devcontainer(config)

        assert "go.buildTags" in content
        assert "go.useLanguageServer" in content

    def test_dotnet_settings_included(self) -> None:
        """Test .NET settings are included when .NET is selected."""
        config = self.create_test_config({"dotnet": True})
        content = self.generate_devcontainer(config)

        assert "dotnet.inlayHints.enableInlayHintsForParameters" in content
        assert "dotnet.completion.showCompletionItemsFromUnimportedNamespaces" in content

    def test_core_settings_always_included(self) -> None:
        """Test core settings are always included."""
        config = self.create_test_config({})
        content = self.generate_devcontainer(config)

        assert "editor.formatOnSave" in content
        assert "files.watcherExclude" in content
        assert "mise.checkForUpdates" in content

    def test_file_associations_preserved(self) -> None:
        """Test that file associations are preserved."""
        config = self.create_test_config({})
        content = self.generate_devcontainer(config)

        assert "files.associations" in content
        assert "*.yaml.tftpl" in content

    def test_multiple_tools_combined(self) -> None:
        """Test multiple tools can be combined."""
        config = self.create_test_config({"python": True, "go": True, "dotnet": True})
        content = self.generate_devcontainer(config)

        # Check all tool extensions are included
        assert "ms-python.python" in content
        assert "golang.go" in content
        assert "ms-dotnettools.csharp" in content

        # Check all tool settings are included
        assert "python.defaultInterpreterPath" in content
        assert "go.buildTags" in content
        assert "dotnet.completion.showCompletionItemsFromUnimportedNamespaces" in content


def test_valid_json_structure() -> None:
    """Test that generated file maintains valid JSON structure."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Setup
        source_devcontainer = Path(".devcontainer/devcontainer.json")
        temp_devcontainer_dir = temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

        # Create config
        config = ProjectConfig()
        config.project_path = str(temp_dir)
        config.project_name = "test"
        config.display_name = "Test"
        config.container_name = "test-container"
        config.tool_selected = {"python": True}

        # Generate
        screen = InstallationScreen(config, Path("."))
        screen.generate_devcontainer_json()

        # Read content
        generated_file = temp_dir / ".devcontainer" / "devcontainer.json"
        content = generated_file.read_text()

        # Test structure without parsing (comments make it invalid JSON)
        assert '"name":' in content
        assert '"build":' in content  # Uses build section, not image
        assert '"customizations":' in content
        assert '"vscode":' in content
        assert '"extensions":' in content
        assert '"settings":' in content

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
