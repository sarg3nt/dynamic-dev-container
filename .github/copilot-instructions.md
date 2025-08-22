# GitHub Copilot Instructions for Dynamic Dev Container

This document provides AI coding agents with essential patterns and conventions specific to this dynamic development container installer project.

## ❌ CRITICAL RESTRICTION - DO NOT RUN INSTALL.PY ❌

**AI AGENTS MUST NEVER EXECUTE `install.py` OR `python install.py` COMMANDS**

- ❌ NEVER run `install.py` manually during development
- ❌ NEVER run `bash install.py` manually during development
- ❌ NEVER use `run_in_terminal` to execute `install.py`
- ✅ ALWAYS ask the user to test `install.py` execution
- ✅ ALWAYS request user feedback on installation results

## Project Overview

This is a Python TUI (Terminal User Interface) application built with [Textual](https://textual.textualize.io/) that creates customized development container configurations. The installer guides users through tool selection, configuration, and generates complete `.devcontainer` setups with Docker, VS Code extensions, and mise-managed tooling.

## Architecture Patterns

### TUI Screen Architecture

The application follows a multi-screen flow pattern with centralized state management:

```python
# Screen flow: Welcome → ProjectConfig → ToolSelection → ToolVersion → PSIHeader → Summary → Installation
installer/screens/
├── __init__.py          # Screen exports
├── basic.py            # Welcome and Summary screens
├── headers.py          # PSI header configuration
├── mixins.py           # Shared widget mixins
├── project.py          # Project metadata configuration
└── tools.py            # Core tool selection and configuration
```

**Key Conventions:**

- All screens inherit from `Screen` and implement `compose()` method
- Use `self.app.push_screen()` for navigation
- Access shared state via `self.app.config` (ProjectConfig instance)
- Implement `on_mount()` for initialization, `action_*()` for keybindings

### Container Recreation Pattern

**Critical Pattern:** For Textual layout issues (spacing accumulation, widget artifacts), use complete container recreation:

```python
def refresh_configuration(self):
    """Recreate entire widget container to prevent layout artifacts"""
    # Remove existing container completely
    try:
        self.query_one("#config_container").remove()
    except NoMatches:
        pass

    # Create fresh container with all widgets
    new_container = ScrollableContainer(
        # Recreate all widgets here
        id="config_container"
    )
    self.mount(new_container)
```

This pattern prevents vertical spacing accumulation and widget state pollution that can occur with partial updates.

### Configuration Management

Centralized state is managed through `ProjectConfig` class in `installer/config.py`:

```python
# Access pattern throughout screens:
config = self.app.config

# Common properties:
config.project_name          # User-defined project name
config.python_publish_pypi   # Boolean flags for publishing
config.selected_tools        # Dict of tool selections
config.tool_versions         # Dict of tool versions
```

**Key Pattern:** Always update config properties in event handlers, never maintain local state.

### Tool Discovery System

Tools are managed through the mise integration system:

```python
# Located in installer/tools.py
class MiseParser:
    def get_available_tools(self) -> Dict[str, List[str]]
    def get_tool_versions(self, tool_name: str) -> List[str]

# Usage pattern in screens:
tool_manager = ToolManager()
tools = tool_manager.get_available_tools()
versions = tool_manager.get_tool_versions("python")
```

**Mise Configuration:** The `.mise.toml` file uses sectioned organization with special markers:

- `#### Begin/End SectionName ####` for logical grouping
- `#version#` for configurability markers
- `#language: lang_name` for language associations

## Widget Patterns

### Radio Button Implementation

For mutually exclusive selections (like repository types):

```python
from textual.widgets import RadioSet, RadioButton

# In compose():
RadioSet(
    RadioButton("PyPI", value=True, id="pypi_radio"),
    RadioButton("Artifactory", id="artifactory_radio"),
    RadioButton("Other", id="other_radio"),
    id="repository_type"
)

# Event handling:
def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
    if event.radio_set.id == "repository_type":
        # Update config based on selection
        self.app.config.python_repository_pypi_selected = (event.pressed.id == "pypi_radio")
```

### Conditional Widget Display

Show/hide widgets based on user selections:

```python
# Pattern for conditional visibility
def update_url_fields_visibility(self):
    """Show URL fields only for Artifactory/Other options"""
    url_container = self.query_one("#url_container")

    if self.app.config.python_repository_pypi_selected:
        url_container.add_class("hidden")
    else:
        url_container.remove_class("hidden")
```

### Input Validation

Standard pattern for user input handling:

```python
def on_input_changed(self, event: Input.Changed) -> None:
    """Handle input field changes with validation"""
    if event.input.id == "project_name":
        # Validate and update config
        if event.value.strip():
            self.app.config.project_name = event.value.strip()
```

## File Structure Conventions

### Directory Organization

```
installer/                 # Main package
├── __init__.py            # Package initialization
├── app.py                 # Main application class and coordination
├── config.py              # ProjectConfig class and data structures
├── main.py                # Entry point and CLI handling
├── tools.py               # Tool discovery and mise integration
├── utils.py               # Shared utilities
└── screens/               # TUI screen implementations
    ├── __init__.py        # Screen exports
    ├── basic.py           # Simple screens (Welcome, Summary)
    ├── headers.py         # PSI header configuration
    ├── mixins.py          # Shared widget behaviors
    ├── project.py         # Project metadata screens
    └── tools.py           # Tool selection and configuration
```

### Import Conventions

```python
# Standard imports for screens
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioSet, RadioButton

# Internal imports
from installer.config import ProjectConfig
from installer.tools import ToolManager
```

## Python Coding Standards

### Function Documentation

**CRITICAL:** All Python functions must be documented according to our project standards using Google-style docstrings with type annotations.

**Examples from codebase:**

```python
# From app.py __init__ method:
def __init__(self, config: ProjectConfig | None = None) -> None:
    """Initialize the Dynamic Dev Container application.

    Parameters
    ----------
    config : ProjectConfig | None, optional
        Pre-configured project settings, by default None

    """
    super().__init__()
    self.config = config or ProjectConfig()

# From headers.py _get_auto_selected_languages method:
def _get_auto_selected_languages(self) -> set[str]:
    """Get languages that should be auto-selected based on selected tools.

    Analyzes the selected development tools and returns a set of language
    identifiers that should be automatically selected for PSI Header templates.

    Returns
    -------
    set[str]
        Set of language identifiers to auto-select (e.g., 'python', 'go', 'javascript')

    """
```

**Required Elements:**

- Brief one-line description
- Parameters section with type annotations and descriptions
- Returns section with type and description
- Raises section if applicable
- Examples section for complex functions

### Method Organization and Naming

**Helper and Private Methods:**

- Private methods must begin with double underscore `__`
- Helper methods must begin with double underscore `__`
- All private/helper methods must be placed at the bottom of the file
- Private/helper methods must be ordered alphabetically

**Example Structure:**

```python
class MyClass:
    def public_method(self) -> None:
        """Public method documentation."""
        pass

    def on_event_handler(self, event: Event) -> None:
        """Event handler documentation."""
        pass

    # Private/helper methods at bottom, alphabetically ordered
    def __helper_method_a(self) -> str:
        """Helper method A documentation."""
        pass

    def __helper_method_b(self) -> int:
        """Helper method B documentation."""
        pass
```

### Type Annotations

**MANDATORY:** Types must be used everywhere in Python code:

```python
# Function parameters and return types
def process_data(items: list[str], count: int) -> dict[str, Any]:
    """Process data with type annotations."""
    pass

# Variable annotations
selected_tools: dict[str, bool] = {}
config_path: Path = Path("config.toml")
language_mappings: dict[str, str] | None = None

# Class attributes
class ProjectConfig:
    project_name: str
    selected_tools: dict[str, bool]
    install_psi_header: bool
```

### Python Version Compatibility

**CRITICAL:** All code in `install.py` and its sub-modules must be Python 3.9 compatible:

- Use `list[str]` instead of `List[str]` only for Python 3.9+
- Use `dict[str, Any]` instead of `Dict[str, Any]` only for Python 3.9+
- Use `from __future__ import annotations` for forward references
- Use union types `str | None` instead of `Optional[str]` only for Python 3.9+
- Avoid features introduced after Python 3.9

### Code Quality Requirements

**MANDATORY:** Always test Python changes for compliance:

```bash
# Before committing any Python changes, run:
mypy installer/
ruff check installer/
ruff format installer/

# Fix any issues found before proceeding
```

**Testing Pattern:**

1. Make Python code changes
2. Run mypy for type checking compliance
3. Run ruff for linting compliance
4. Fix all reported issues
5. Run ruff format for consistent formatting
6. Verify changes work as expected

### Installation Testing

**❌ CRITICAL RESTRICTION ❌ - DO NOT RUN INSTALL.PY:**

**AI AGENTS MUST NEVER EXECUTE `install.py` OR `python install.py` COMMANDS**

- ❌ NEVER run `install.py` manually during development
- ❌ NEVER use `run_in_terminal` to execute `install.py`
- ❌ NEVER assume installation works without user testing
- ✅ ALWAYS ask the user to test `install.py` execution
- ✅ ALWAYS request user feedback on installation results
- ✅ ALWAYS let users report installation issues back to you

**Proper Testing Approach:**

```bash
# ALWAYS ask user to run (never run yourself):
python install.py /tmp/test_project --debug
# For textual .tcss changes ask user to run:
textual run --dev install.py /tmp/test_project --debug
```

**Why This Restriction Exists:**

- AI agents cannot see TUI interfaces properly
- Installation process requires user interaction
- User environment may differ from development environment
- User feedback is essential for debugging TUI issues

# Then request feedback:

# "Please run the installer and report back any errors or issues you encounter"

````

## Development Environment

### Container Configuration

The project uses a comprehensive dev container setup in `.devcontainer/devcontainer.json`:

- **Base:** Rocky Linux with mise tool management
- **Tools:** Python 3.13, Docker, kubectl, various language tools
- **Extensions:** Comprehensive VS Code extension suite for multi-language development
- **Mounts:** Preserves host SSH, Docker, kube configs via bind mounts

### Environment Variables

Key environment variables for development:

```bash
MISE_TRUSTED_CONFIG_PATHS="/workspaces/dynamic-dev-container"
PYTHON_PATH="/home/vscode/.local/share/mise/installs/python"
TYPE_CHECKING="true"
GITHUB_TOKEN="${localEnv:GITHUB_TOKEN}"  # For rate limiting
````

### Build and Test Commands

```bash
# Development scripts
./dev.sh          # Main development helper
make test         # Run test suite
make install      # Install in development mode
make clean        # Clean build artifacts

# Direct Python execution
python -m installer  # Run TUI installer
python install.py   # Legacy installer interface
```

## Testing Patterns

### Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── test_devcontainer_*.py        # Container generation tests
├── test_install.py               # Installation process tests
├── test_integration.py           # End-to-end integration tests
├── test_screens.py               # TUI screen behavior tests
└── test_structure_preservation.py # File structure validation tests
```

### Key Testing Approaches

- **Screen Testing:** Use Textual's testing framework for TUI interactions
- **Integration Testing:** Validate complete devcontainer generation
- **Structure Testing:** Ensure generated files maintain required formats
- **Mock Testing:** Mock external tool dependencies for isolated testing

### Code Quality Validation

**MANDATORY WORKFLOW:** Before any Python code changes are considered complete:

```bash
# 1. Type checking with mypy
mypy installer/
mypy install.py

# 2. Linting with ruff
ruff check installer/
ruff check install.py

# 3. Formatting with ruff
ruff format installer/
ruff format install.py

# 4. Run tests
make test

# 5. Ask user to test install.py
# Never run install.py manually - always request user testing
```

**Quality Gates:**

- Zero mypy errors allowed
- Zero ruff linting errors allowed
- All code must be ruff-formatted
- All functions must have proper docstrings
- All types must be annotated
- Python 3.9 compatibility required for install.py modules

## Common Pitfalls and Solutions

### Widget Layout Issues

**Problem:** Vertical spacing accumulation, widgets not appearing
**Solution:** Use container recreation pattern instead of partial updates

### State Management

**Problem:** State inconsistencies between screens
**Solution:** Always use `self.app.config` for shared state, never local variables

### Tool Discovery

**Problem:** Missing tools or versions
**Solution:** Ensure mise configuration is trusted and properly formatted with section markers

### Container Recreation Timing

**Problem:** Widgets not properly mounting after recreation
**Solution:** Use `try/except` with `NoMatches` when removing containers, ensure proper mount order

## Integration Points

### Mise Tool Management

The installer integrates with mise for tool version management:

- Parses `.mise.toml` for available tools and versions
- Respects version configurability markers (`#version#`)
- Maintains language associations (`#language: python`)

### Docker Integration

Container generation follows these patterns:

- Rocky Linux base with comprehensive package installation
- Multi-stage builds for optimization
- VS Code extension pre-installation for performance
- Volume mounts for host integration (SSH, Docker, kube configs)

### VS Code Configuration

Extension and settings management:

- Sectioned organization (`#### Begin/End SectionName ####`)
- Language-specific formatter configuration
- Tool-specific path configurations for mise-managed tools
- Comprehensive linting and formatting pipeline setup

This project follows these patterns consistently. When making changes, preserve the architectural patterns and always test TUI interactions thoroughly to ensure proper widget lifecycle management.
