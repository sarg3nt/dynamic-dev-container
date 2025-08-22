"""Test to verify devcontainer.json structure preservation."""

import shutil
import tempfile
from pathlib import Path

from install_new import InstallationScreen, ProjectConfig


def test_structure_preservation():
    """Test that the new generation method preserves structure and comments."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Setup
        source_devcontainer = Path(".devcontainer/devcontainer.json")
        temp_devcontainer_dir = temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

        # Read original content
        original_content = source_devcontainer.read_text()

        # Create config and generate
        config = ProjectConfig()
        config.project_path = str(temp_dir)
        config.project_name = "test-project"
        config.display_name = "Test Project Structure"
        config.container_name = "test-structure-container"
        config.tool_selected = {"python": True, "go": True}
        config.include_python_extensions = True

        screen = InstallationScreen(config, Path("."))
        screen.generate_devcontainer_json()

        # Read generated content
        generated_file = temp_dir / ".devcontainer" / "devcontainer.json"
        generated_content = generated_file.read_text()

        print("\\n=== ORIGINAL DEVCONTAINER.JSON STRUCTURE CHECK ===")
        print(f"Original has comments: {'// Dev Container Configuration File' in original_content}")
        print(f"Original has build section: {'"build":' in original_content}")
        print(f"Original has extensions: {'"extensions":' in original_content}")
        print(f"Original has settings: {'"settings":' in original_content}")
        print(f"Original has files.associations: {'files.associations' in original_content}")

        print("\\n=== GENERATED DEVCONTAINER.JSON STRUCTURE CHECK ===")
        print(f"Generated has comments: {'// Dev Container Configuration File' in generated_content}")
        print(f"Generated has build section: {'"build":' in generated_content}")
        print(f"Generated has extensions: {'"extensions":' in generated_content}")
        print(f"Generated has settings: {'"settings":' in generated_content}")
        print(f"Generated has files.associations: {'files.associations' in generated_content}")
        print(f"Generated preserves comment structure: {'// VS Code Settings' in generated_content}")

        # Check specific content
        print(f"\\nContainer name updated: {'test-structure-container' in generated_content}")
        print(f"Display name updated: {'Test Project Structure' in generated_content}")
        print(f"Python extensions added: {'ms-python.python' in generated_content}")
        print(f"Go extensions added: {'golang.go' in generated_content}")
        print(f"Python settings added: {'python.defaultInterpreterPath' in generated_content}")
        print(f"Go settings added: {'go.toolsManagement.checkForUpdates' in generated_content}")

        # Check that important structure is preserved
        assert "// Dev Container Configuration File" in generated_content
        assert "// Build from Dockerfile" in generated_content
        assert "// VS Code Settings" in generated_content
        assert "files.associations" in generated_content
        assert '"*.yaml.tftpl": "yaml"' in generated_content  # Check for actual file associations

        # Check that tools were properly added
        assert "ms-python.python" in generated_content
        assert "golang.go" in generated_content
        assert "python.defaultInterpreterPath" in generated_content
        assert "go.useLanguageServer" in generated_content  # Check for actual Go settings

        # Check container references were updated
        assert "test-structure-container" in generated_content
        assert "Test Project Structure" in generated_content

        print("\\n=== STRUCTURE PRESERVATION TEST PASSED ===")
        print("✓ Comments preserved")
        print("✓ Original structure maintained")
        print("✓ Tool-specific extensions and settings added")
        print("✓ Container references updated")
        print("✓ file.associations preserved")

        # Show a sample of the generated content
        print("\\n=== SAMPLE OF GENERATED CONTENT ===")
        lines = generated_content.split("\\n")
        for i, line in enumerate(lines[:50]):  # Show first 50 lines
            print(f"{i + 1:2}: {line}")

        if len(lines) > 50:
            print(f"... ({len(lines) - 50} more lines)")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_structure_preservation()
