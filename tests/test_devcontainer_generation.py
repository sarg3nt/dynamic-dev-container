"""Comprehensive tests for devcontainer.json generation.

These tests verify that the devcontainer.json file is generated correctly
with proper extensions and settings based on different tool combinations.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
from install import InstallationScreen, ProjectConfig


class TestDevContainerGeneration:
    """Test class for devcontainer.json generation."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Create a temporary directory for each test
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_dir = Path(".")

        # Copy source devcontainer.json to temp directory
        source_devcontainer = self.source_dir / ".devcontainer" / "devcontainer.json"
        temp_devcontainer_dir = self.temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

    def teardown_method(self):
        """Clean up after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_config(self, tool_selections: dict[str, bool], **kwargs) -> ProjectConfig:
        """Create a test configuration with specified tool selections."""
        config = ProjectConfig()
        config.project_path = str(self.temp_dir)
        config.project_name = "test-project"
        config.display_name = "Test Project"
        config.container_name = "test-project-container"
        config.docker_exec_command = "tp"
        config.tool_selected = tool_selections

        # Set defaults
        config.include_python_extensions = kwargs.get("include_python_extensions", False)
        config.include_markdown_extensions = kwargs.get("include_markdown_extensions", True)
        config.include_shell_extensions = kwargs.get("include_shell_extensions", True)
        config.include_js_extensions = kwargs.get("include_js_extensions", False)
        config.install_psi_header = kwargs.get("install_psi_header", False)

        return config

    def generate_and_parse_devcontainer(self, config: ProjectConfig) -> dict[str, Any]:
        """Generate devcontainer.json and parse it as JSON."""
        screen = InstallationScreen(config, self.source_dir)
        screen.generate_devcontainer_json()

        generated_file = self.temp_dir / ".devcontainer" / "devcontainer.json"
        assert generated_file.exists(), f"Generated file not found at: {generated_file}"

        # Read and parse the generated JSON (removing comments for parsing)
        content = generated_file.read_text()

        # Simple comment removal for parsing (not perfect but good enough for tests)
        lines = content.split("\n")
        clean_lines = []
        for line in lines:
            # Remove single-line comments
            if "//" in line:
                clean_line = line.split("//")[0].rstrip()
                clean_lines.append(clean_line)
            else:
                clean_lines.append(line)

        clean_content = "\n".join(clean_lines)

        try:
            parsed_json = json.loads(clean_content)
            return parsed_json  # type: ignore  # JSON is validated to be dict[str, Any]
        except json.JSONDecodeError as e:
            pytest.fail(f"Generated devcontainer.json is not valid JSON: {e}\\nContent:\\n{content}")

    def test_python_only_configuration(self):
        """Test devcontainer generation with only Python tools selected."""
        config = self.create_config(
            tool_selections={"python": True},
            include_python_extensions=True,
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        # Check basic structure
        assert devcontainer["name"] == "Test Project"
        assert devcontainer["runArgs"] == ["--name=test-project-container"]

        # Check extensions
        extensions = devcontainer["customizations"]["vscode"]["extensions"]

        # Should include GitHub extensions
        assert "GitHub.copilot" in extensions
        assert "GitHub.copilot-chat" in extensions

        # Should include Python extensions
        assert "ms-python.python" in extensions
        assert "ms-python.mypy-type-checker" in extensions
        assert "charliermarsh.ruff" in extensions

        # Should include Markdown and Shell extensions (defaults)
        assert "yzhang.markdown-all-in-one" in extensions
        assert "foxundermoon.shell-format" in extensions

        # Should NOT include Go or .NET extensions
        assert "golang.go" not in extensions
        assert "ms-dotnettools.csharp" not in extensions

        # Check settings
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Should include Python settings
        assert "python.defaultInterpreterPath" in settings
        assert "python.analysis.typeCheckingMode" in settings

        # Should NOT include Go or .NET settings
        assert "go.toolsManagement.checkForUpdates" not in settings
        assert "dotnet.server.useOmnisharp" not in settings

        # Should include core settings
        assert "editor.formatOnSave" in settings
        assert "files.watcherExclude" in settings

    def test_go_and_dotnet_configuration(self):
        """Test devcontainer generation with Go and .NET tools selected."""
        config = self.create_config(
            tool_selections={"go": True, "dotnet": True},
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        extensions = devcontainer["customizations"]["vscode"]["extensions"]
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Should include Go extensions
        assert "golang.go" in extensions
        assert "ms-vscode.vscode-go" in extensions

        # Should include .NET extensions
        assert "ms-dotnettools.csharp" in extensions
        assert "ms-dotnettools.csdevkit" in extensions

        # Should include Go settings
        assert "go.toolsManagement.checkForUpdates" in settings
        assert "go.useLanguageServer" in settings

        # Should include .NET settings
        assert "dotnet.server.useOmnisharp" in settings
        assert "dotnet.completion.showCompletionItemsFromUnimportedNamespaces" in settings

        # Should NOT include Python extensions or settings
        assert "ms-python.python" not in extensions
        assert "python.defaultInterpreterPath" not in settings

    def test_javascript_configuration(self):
        """Test devcontainer generation with JavaScript tools selected."""
        config = self.create_config(
            tool_selections={"node": True},
            include_js_extensions=True,
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        extensions = devcontainer["customizations"]["vscode"]["extensions"]
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Should include JavaScript extensions
        assert "ms-vscode.vscode-typescript-next" in extensions
        assert "ms-vscode.vscode-eslint" in extensions
        assert "esbenp.prettier-vscode" in extensions

        # Should include JavaScript settings
        assert "typescript.preferences.includePackageJsonAutoImports" in settings
        assert "eslint.validate" in settings

    def test_minimal_configuration(self):
        """Test devcontainer generation with no tools selected."""
        config = self.create_config(
            tool_selections={},
            include_python_extensions=False,
            include_markdown_extensions=False,
            include_shell_extensions=False,
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        extensions = devcontainer["customizations"]["vscode"]["extensions"]
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Should always include GitHub and core extensions
        assert "GitHub.copilot" in extensions
        assert "albert.TabOut" in extensions
        assert "streetsidesoftware.code-spell-checker" in extensions

        # Should NOT include tool-specific extensions
        assert "ms-python.python" not in extensions
        assert "golang.go" not in extensions
        assert "ms-dotnettools.csharp" not in extensions

        # Should always include core settings
        assert "editor.formatOnSave" in settings
        assert "mise.checkForUpdates" in settings
        assert "todo-tree.general.tags" in settings

        # Should NOT include tool-specific settings
        assert "python.defaultInterpreterPath" not in settings
        assert "go.toolsManagement.checkForUpdates" not in settings

    def test_psi_header_configuration(self):
        """Test devcontainer generation with PSI Header enabled."""
        config = self.create_config(
            tool_selections={"python": True},
            install_psi_header=True,
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        extensions = devcontainer["customizations"]["vscode"]["extensions"]

        # Should include PSI Header extension
        assert "psioniq.psi-header" in extensions

    def test_container_references_replacement(self):
        """Test that container references are properly replaced."""
        config = self.create_config(
            tool_selections={"python": True},
        )
        config.display_name = "My Awesome Project"
        config.container_name = "my-awesome-project-container"

        devcontainer = self.generate_and_parse_devcontainer(config)

        # Check name replacement
        assert devcontainer["name"] == "My Awesome Project"

        # Check runArgs replacement
        assert devcontainer["runArgs"] == ["--name=my-awesome-project-container"]

        # Check mount sources replacement
        found_shell_mount = False
        found_plugins_mount = False

        for mount in devcontainer["mounts"]:
            if "shellhistory" in mount["source"]:
                assert mount["source"] == "my-awesome-project-container-shellhistory"
                found_shell_mount = True
            elif "plugins" in mount["source"]:
                assert mount["source"] == "my-awesome-project-container-plugins"
                found_plugins_mount = True

        assert found_shell_mount, "Shell history mount not found or not updated"
        assert found_plugins_mount, "Plugins mount not found or not updated"

    def test_settings_structure_preservation(self):
        """Test that important settings structure is preserved."""
        config = self.create_config(
            tool_selections={"python": True},
        )

        devcontainer = self.generate_and_parse_devcontainer(config)
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Check that complex nested settings are preserved
        assert "files.watcherExclude" in settings
        watcher_exclude = settings["files.watcherExclude"]
        assert isinstance(watcher_exclude, dict)
        assert "**/node_modules/*/**" in watcher_exclude
        assert "**/.git/objects/**" in watcher_exclude

        # Check that files.associations is included
        assert "files.associations" in settings
        associations = settings["files.associations"]
        assert isinstance(associations, dict)
        assert "*.toml" in associations

        # Check that spell checker settings are properly structured
        assert "cSpell.enabledLanguageIds" in settings
        enabled_languages = settings["cSpell.enabledLanguageIds"]
        assert isinstance(enabled_languages, list)
        assert "python" in enabled_languages
        assert "javascript" in enabled_languages

    def test_extensions_order_consistency(self):
        """Test that extensions are in a consistent order."""
        config1 = self.create_config(tool_selections={"python": True, "go": True})
        config2 = self.create_config(tool_selections={"go": True, "python": True})

        devcontainer1 = self.generate_and_parse_devcontainer(config1)
        devcontainer2 = self.generate_and_parse_devcontainer(config2)

        extensions1 = devcontainer1["customizations"]["vscode"]["extensions"]
        extensions2 = devcontainer2["customizations"]["vscode"]["extensions"]

        # Extensions should be in the same order regardless of tool selection order
        assert extensions1 == extensions2

    def test_all_tools_configuration(self):
        """Test devcontainer generation with all tools selected."""
        config = self.create_config(
            tool_selections={
                "python": True,
                "go": True,
                "dotnet": True,
                "node": True,
                "pnpm": True,
            },
            include_python_extensions=True,
            include_js_extensions=True,
            install_psi_header=True,
        )

        devcontainer = self.generate_and_parse_devcontainer(config)

        extensions = devcontainer["customizations"]["vscode"]["extensions"]
        settings = devcontainer["customizations"]["vscode"]["settings"]

        # Should include extensions for all selected tools
        assert "ms-python.python" in extensions
        assert "golang.go" in extensions
        assert "ms-dotnettools.csharp" in extensions
        assert "ms-vscode.vscode-typescript-next" in extensions
        assert "psioniq.psi-header" in extensions

        # Should include settings for all selected tools
        assert "python.defaultInterpreterPath" in settings
        assert "go.toolsManagement.checkForUpdates" in settings
        assert "dotnet.server.useOmnisharp" in settings
        assert "typescript.preferences.includePackageJsonAutoImports" in settings

        # Should still include core settings
        assert "editor.formatOnSave" in settings
        assert "files.watcherExclude" in settings


def test_generated_file_is_valid_jsonc():
    """Test that the generated file is valid JSONC that can be read by VS Code."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Copy source devcontainer.json
        source_devcontainer = Path(".devcontainer/devcontainer.json")
        temp_devcontainer_dir = temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

        # Create config and generate
        config = ProjectConfig()
        config.project_path = str(temp_dir)
        config.project_name = "test"
        config.display_name = "Test"
        config.container_name = "test-container"
        config.tool_selected = {"python": True}
        config.include_markdown_extensions = True
        config.include_shell_extensions = True

        screen = InstallationScreen(config, Path("."))
        screen.generate_devcontainer_json()

        generated_file = temp_dir / ".devcontainer" / "devcontainer.json"
        content = generated_file.read_text()

        # Verify file has proper structure
        assert content.startswith("// Dev Container Configuration File")
        assert '"name":' in content
        assert '"extensions":' in content
        assert '"settings":' in content

        # Verify comments are preserved
        assert "// Build from Dockerfile" in content
        assert "// VS Code Settings" in content

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
