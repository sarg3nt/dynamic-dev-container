"""Parser utilities for .mise.toml files in the Dynamic Dev Container installer."""

from __future__ import annotations

import re
from pathlib import Path


class MiseParser:
    """Parser for .mise.toml files."""

    @staticmethod
    def parse_mise_sections(mise_file: Path) -> tuple[list[str], dict[str, bool], dict[str, str], dict[str, bool]]:
        """Parse tool sections from .mise.toml file.

        Parameters
        ----------
        mise_file : Path
            Path to the .mise.toml file to parse

        Returns
        -------
        tuple[list[str], dict[str, bool], dict[str, str], dict[str, bool]]
            Tuple containing (sections, tool_selected, tool_version_value, tool_version_configurable)

        """
        if not mise_file.exists():
            return [], {}, {}, {}

        with open(mise_file) as f:
            content = f.read()

        sections = []
        tool_selected = {}
        tool_version_value = {}
        tool_version_configurable = {}

        # Parse sections between markers
        in_tools_section = False
        current_section = None
        lines = content.split("\n")
        previous_line = ""

        for line in lines:
            stripped_line = line.strip()

            if stripped_line == "[tools]":
                in_tools_section = True
                continue

            if in_tools_section and stripped_line.startswith("[") and stripped_line != "[tools]":
                break

            if in_tools_section:
                # Check for section markers (these start with ####)
                begin_match = re.match(r"^#### Begin (.+)$", stripped_line)
                if begin_match:
                    current_section = begin_match.group(1)
                    if current_section not in sections:
                        sections.append(current_section)
                    continue

                end_match = re.match(r"^#### End (.+)$", stripped_line)
                if end_match:
                    current_section = None
                    continue

                # Check for tool definitions (only when we're in a section)
                if current_section:
                    tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", stripped_line)
                    if tool_match:
                        tool_name = tool_match.group(1)
                        tool_selected[tool_name] = False  # Default to not selected
                        tool_version_value[tool_name] = "latest"

                        # Check if previous line had version marker
                        tool_version_configurable[tool_name] = previous_line.strip() == "#version#"

            previous_line = line

        return sections, tool_selected, tool_version_value, tool_version_configurable

    @staticmethod
    def get_section_tools(mise_file: Path, section_name: str) -> list[str]:
        """Get all tools in a specific section.

        Parameters
        ----------
        mise_file : Path
            Path to the .mise.toml file to parse
        section_name : str
            Name of the section to get tools from

        Returns
        -------
        list[str]
            List of tool names in the specified section

        """
        if not mise_file.exists():
            return []

        with open(mise_file) as f:
            content = f.read()

        tools = []
        in_section = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            if stripped_line == f"#### Begin {section_name}":
                in_section = True
                continue

            if stripped_line == f"#### End {section_name}":
                break

            if in_section:
                tool_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*", stripped_line)
                if tool_match:
                    tools.append(tool_match.group(1))

        return tools
