"""Test configuration and fixtures for install.py tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mise_toml() -> str:
    """Sample .mise.toml content for testing."""
    return """# Test mise configuration
#### Begin Environment
[env]
MISE_PYTHON_COMPILE = false
#### End Environment

[tools]

#### Begin Python
#version#
python = '3.13'
#### End Python

#### Begin HashiCorp Tools
#version#
opentofu = 'latest'
packer = 'latest'
#### End HashiCorp Tools

#### Begin Kubernetes
kubectl = 'latest'
helm = 'latest'
#### End Kubernetes

[alias]
test = "echo testing"

[settings]
experimental = true
"""


@pytest.fixture
def sample_devcontainer_json() -> str:
    """Sample devcontainer.json content for testing."""
    return """{
  "name": "Dynamic Dev Container",
  "runArgs": ["--name=dynamic-dev-container"],
  "mounts": [
    {
      "source": "dynamic-dev-container-shellhistory",
      "target": "/commandhistory",
      "type": "volume"
    }
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "GitHub.copilot"
      ],
      "settings": {
        "editor.insertSpaces": true
      }
    }
  }
}"""


@pytest.fixture
def mock_source_dir(temp_dir: Path, sample_mise_toml: str, sample_devcontainer_json: str) -> Path:
    """Create a mock source directory with required files."""
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    # Create .mise.toml
    (source_dir / ".mise.toml").write_text(sample_mise_toml)

    # Create .devcontainer directory and files
    devcontainer_dir = source_dir / ".devcontainer"
    devcontainer_dir.mkdir()
    (devcontainer_dir / "devcontainer.json").write_text(sample_devcontainer_json)

    # Create other required files
    (source_dir / "dev.sh").write_text('#!/bin/bash\necho "dev script"')
    (source_dir / "package.json").write_text('{"name": "test"}')
    (source_dir / "pyproject.toml").write_text('[project]\nname = "test"')
    (source_dir / "requirements.txt").write_text("pytest")
    (source_dir / "pybuild.py").write_text('#!/usr/bin/env python3\nprint("build")')

    return source_dir
