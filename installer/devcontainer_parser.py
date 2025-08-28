"""DevContainer configuration parser utilities.

This module provides utilities for parsing devcontainer.json files to extract
extension sections, settings sections, and PSI header language configurations.
"""

from __future__ import annotations

import re
from pathlib import Path


class DevContainerParser:
    """Parser for devcontainer.json files to extract extension and settings sections."""

    @staticmethod
    def parse_extension_sections(devcontainer_file: Path) -> list[str]:
        """Parse extension sections from devcontainer.json file.

        Parameters
        ----------
        devcontainer_file : Path
            Path to the devcontainer.json file to parse

        Returns
        -------
        list[str]
            List of extension section names found in the file

        """
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        sections = []
        in_extensions = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for the extensions array
            if '"extensions":' in stripped_line:
                in_extensions = True
                continue

            # Stop when we exit the extensions array
            if in_extensions and stripped_line.startswith('"settings":'):
                break

            if in_extensions:
                # Look for section markers
                begin_match = re.match(r"^//\s*#### Begin (.+) ####", stripped_line)
                if begin_match:
                    section_name = begin_match.group(1)
                    if section_name not in sections and section_name not in ["Github", "Core Extensions", "PSI Header"]:
                        sections.append(section_name)

        return sections

    @staticmethod
    def parse_extension_sections_with_extensions(devcontainer_file: Path) -> dict[str, list[tuple[str, str]]]:
        """Parse extension sections from devcontainer.json file with their extensions.

        Parameters
        ----------
        devcontainer_file : Path
            Path to the devcontainer.json file to parse

        Returns
        -------
        dict[str, list[tuple[str, str]]]
            Dictionary mapping section names to lists of (extension_id, description) tuples.
            Excludes tool-related sections (those matching tools), PSI Header, and Core Extensions.

        """
        if not devcontainer_file.exists():
            return {}

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        sections_with_extensions: dict[str, list[tuple[str, str]]] = {}
        current_section = None
        in_extensions = False
        tool_related_sections = {
            "Go Development",
            ".NET Development",
            "Node Development",
            "Python",
            "Kubernetes",
            "HashiCorp Tools",
            "PowerShell",
        }
        excluded_sections = {"Core Extensions", "PSI Header"}

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for the extensions array
            if '"extensions":' in stripped_line:
                in_extensions = True
                continue

            # Stop when we exit the extensions array
            if in_extensions and stripped_line.startswith('"settings":'):
                break

            if in_extensions:
                # Look for section begin markers
                begin_match = re.match(r"^//\s*#### Begin (.+) ####", stripped_line)
                if begin_match:
                    section_name = begin_match.group(1)
                    # Only include non-tool-related and non-excluded sections
                    if section_name not in tool_related_sections and section_name not in excluded_sections:
                        current_section = section_name
                        if current_section not in sections_with_extensions:
                            sections_with_extensions[current_section] = []
                    else:
                        current_section = None
                    continue

                # Look for section end markers
                end_match = re.match(r"^//\s*#### End (.+) ####", stripped_line)
                if end_match:
                    current_section = None
                    continue

                # Parse extension lines when we're in a valid section
                if current_section and current_section in sections_with_extensions:
                    # Look for extension IDs with comments
                    extension_match = re.match(r'^"([^"]+)",\s*//\s*(.+)', stripped_line)
                    if extension_match:
                        extension_id = extension_match.group(1)
                        description = extension_match.group(2)
                        sections_with_extensions[current_section].append((extension_id, description))

        return sections_with_extensions

    @staticmethod
    def parse_settings_sections(devcontainer_file: Path) -> list[str]:
        """Parse settings sections from devcontainer.json file.

        Parameters
        ----------
        devcontainer_file : Path
            Path to the devcontainer.json file to parse

        Returns
        -------
        list[str]
            List of settings section names found in the file

        """
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        sections = []
        in_settings = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for the settings object
            if '"settings":' in stripped_line:
                in_settings = True
                continue

            # Stop when we exit the settings object (look for closing brace at same level)
            if (
                in_settings
                and stripped_line == "}"
                and "customizations" in content[content.find('"settings"') : content.find(stripped_line)]
            ):
                break

            if in_settings:
                # Look for section markers that end with "Settings"
                begin_match = re.match(r"^//\s*#### Begin (.+) Settings ####", stripped_line)
                if begin_match:
                    section_name = begin_match.group(1)
                    # Remove "Settings" suffix to match with extension section names
                    base_section_name = section_name
                    if base_section_name not in sections and base_section_name not in [
                        "Core VS Code",
                        "Mise",
                        "Spell Checker",
                        "TODO Tree",
                        "PSI Header",
                    ]:
                        sections.append(base_section_name)

        return sections

    @staticmethod
    def create_section_tool_mapping(mise_file: Path, devcontainer_file: Path) -> dict[str, list[str]]:
        """Create a mapping of sections to tools based on .mise.toml sections.

        Parameters
        ----------
        mise_file : Path
            Path to the .mise.toml file
        devcontainer_file : Path
            Path to the devcontainer.json file

        Returns
        -------
        dict[str, list[str]]
            Mapping from section names to lists of tools in that section

        """
        # Import here to avoid circular imports
        from installer.mise_parser import MiseParser  # noqa: PLC0415

        mise_sections, _, _, _ = MiseParser.parse_mise_sections(mise_file)
        _extension_sections = DevContainerParser.parse_extension_sections(devcontainer_file)
        _settings_sections = DevContainerParser.parse_settings_sections(devcontainer_file)

        # Create mapping of section to tools
        section_tool_mapping = {}

        for section in mise_sections:
            tools = MiseParser.get_section_tools(mise_file, section)
            if tools:
                section_tool_mapping[section] = tools

        return section_tool_mapping

    @staticmethod
    def parse_psi_header_languages(devcontainer_file: Path) -> list[tuple[str, str]]:
        """Parse available PSI header languages from devcontainer.json template.

        Parameters
        ----------
        devcontainer_file : Path
            Path to the devcontainer.json file containing PSI header templates

        Returns
        -------
        list[tuple[str, str]]
            List of tuples containing (language_id, display_name) for each available language

        """
        if not devcontainer_file.exists():
            return []

        with open(devcontainer_file, encoding="utf-8") as f:
            content = f.read()

        languages = []
        in_psi_templates = False

        for line in content.split("\n"):
            stripped_line = line.strip()

            # Look for PSI header templates array
            if '"psi-header.templates":' in stripped_line:
                in_psi_templates = True
                continue

            # Stop when we exit the templates array
            if in_psi_templates and stripped_line == "]":
                break

            if in_psi_templates and '"language":' in stripped_line:
                # Extract language ID from the templates section
                match = re.search(r'"language":\s*"([^"]+)"', stripped_line)
                if match:
                    lang_id = match.group(1)
                    # Skip wildcard language for selection list
                    if lang_id != "*":
                        languages.append((lang_id, lang_id))

        return languages
