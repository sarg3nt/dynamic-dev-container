#!/usr/bin/env python3
"""Test script to validate the modular ToolSelectionScreen integration."""

import sys
from pathlib import Path

# Add the current directory to Python path so we can import from install.py
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Import the modular ToolSelectionScreen
    from install import ProjectConfig, ToolSelectionScreen

    print("✅ Successfully imported ToolSelectionScreen")

    # Check that the class has the expected methods from all mixins
    expected_methods = [
        # From ToolSelectionScreenCore
        "compose",
        "on_mount",
        "refresh_tools",
        # From ToolSelectionConfigMixin
        "refresh_configuration",
        # From ToolSelectionEventMixin
        "on_checkbox_changed",
        "on_input_changed",
        "on_button_pressed",
        # From ToolSelectionUrlMixin
        "_ToolSelectionUrlMixin__update_package_related_fields",
        # From ToolSelectionActionMixin
        "save_current_section",
        "finalize_selection",
        "action_back",
    ]

    print(f"✅ Checking for {len(expected_methods)} expected methods...")

    missing_methods = []
    for method in expected_methods:
        if not hasattr(ToolSelectionScreen, method):
            missing_methods.append(method)

    if missing_methods:
        print(f"❌ Missing methods: {missing_methods}")
        sys.exit(1)
    else:
        print("✅ All expected methods are present")

    # Try to instantiate the class (this tests the mixin composition)
    config = ProjectConfig()
    sections = ["development", "databases"]
    tool_selected = {"python": True, "node": False}
    tool_version_configurable = {"python": True}
    tool_version_value = {"python": "3.11"}

    # This should work without errors
    screen = ToolSelectionScreen(
        config,
        sections,
        tool_selected,
        tool_version_configurable,
        tool_version_value,
    )

    print("✅ Successfully instantiated ToolSelectionScreen with modular composition")

    # Check that the instance has the expected attributes
    assert hasattr(screen, "config")
    assert hasattr(screen, "sections")
    assert hasattr(screen, "tool_selected")
    assert hasattr(screen, "tool_version_configurable")
    assert hasattr(screen, "tool_version_value")

    print("✅ Instance has all expected attributes")

    print("\n🎉 SUCCESS: Modular ToolSelectionScreen integration is working correctly!")
    print(f"   - Composed from {len(ToolSelectionScreen.__bases__)} mixin classes")
    print(f"   - Has {len([m for m in dir(screen) if not m.startswith('_')])} public methods/attributes")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
