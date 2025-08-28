"""File management utilities for the Dynamic Dev Container installer."""

from __future__ import annotations

import shutil
from pathlib import Path


class FileManager:
    """Manages file operations for the installer."""

    # Files and directories to copy
    FILES_TO_COPY = [
        ".gitignore",
        ".krew_plugins",
        ".packages",
        "cspell.json",
        "dev.sh",
        "package.json",
        "run.sh",
        ".mise.toml",
    ]

    PYTHON_FILES_TO_COPY = [
        "pyproject.toml",
        "requirements.txt",
        "pybuild.py",
    ]

    DIRECTORIES_TO_COPY = [".devcontainer"]

    @staticmethod
    def copy_files_and_directories(source_dir: Path, target_dir: Path, include_python: bool = False) -> None:
        """Copy required files and directories to target.

        Parameters
        ----------
        source_dir : Path
            Source directory to copy files from
        target_dir : Path
            Target directory to copy files to
        include_python : bool, optional
            Whether to include Python-specific files, by default False

        """
        # Copy directories
        for dir_name in FileManager.DIRECTORIES_TO_COPY:
            source_path = source_dir / dir_name
            target_path = target_dir / dir_name

            if source_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_path, target_path, dirs_exist_ok=True)

        # Copy files
        files_to_copy = FileManager.FILES_TO_COPY[:]
        if include_python:
            files_to_copy.extend(FileManager.PYTHON_FILES_TO_COPY)

        for file_name in files_to_copy:
            source_path = source_dir / file_name
            target_path = target_dir / file_name

            if source_path.exists() and not target_path.exists():
                shutil.copy2(source_path, target_path)
