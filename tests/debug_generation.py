"""Debug test to see what the generated content looks like."""

import shutil
import tempfile
from pathlib import Path

from install import InstallationScreen, ProjectConfig


def debug_generation():
    """Debug the generation to see what's happening."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Setup
        source_devcontainer = Path(".devcontainer/devcontainer.json")
        temp_devcontainer_dir = temp_dir / ".devcontainer"
        temp_devcontainer_dir.mkdir()
        shutil.copy2(source_devcontainer, temp_devcontainer_dir / "devcontainer.json")

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

        print("=== GENERATED CONTENT (first 100 lines) ===")
        lines = generated_content.split("\\n")
        for i, line in enumerate(lines[:100]):
            print(f"{i + 1:3}: {line}")

        print("\\n=== SEARCH FOR GO CONTENT ===")
        print(f"Contains 'Go' extension section: {'// #### Begin Go ####' in generated_content}")
        print(f"Contains 'Go Settings' section: {'// #### Begin Go Settings ####' in generated_content}")
        print(f"Contains 'golang.go': {'golang.go' in generated_content}")
        print(f"Contains 'go.toolsManagement': {'go.toolsManagement' in generated_content}")
        print(f"Contains '*.toml': {repr('*.toml') in generated_content}")
        print(f"Contains files.associations: {'files.associations' in generated_content}")

        # Show lines around files.associations
        print("\\n=== LINES AROUND files.associations ===")
        for i, line in enumerate(lines):
            if "files.associations" in line:
                start = max(0, i - 5)
                end = min(len(lines), i + 10)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{j + 1:3}: {lines[j]}")

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    debug_generation()
