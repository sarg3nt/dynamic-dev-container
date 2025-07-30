# Python Package Repository Configuration

The dynamic dev container now supports configurable Python package repositories, making it suitable for use with PyPI, Artifactory, Nexus, or any other Python package repository.

- [Features](#features)
- [Configuration](#configuration)
  - [Repository Types](#repository-types)
  - [Configuration Files](#configuration-files)
    - [Required Repository Configuration](#required-repository-configuration)
    - [Optional Repository Configuration](#optional-repository-configuration)
    - [Required Project Metadata Updates](#required-project-metadata-updates)
      - [Project Information](#project-information)
      - [Project URLs](#project-urls)
      - [Build Configuration Paths](#build-configuration-paths)
      - [Testing Configuration](#testing-configuration)
    - [Optional Customizations](#optional-customizations)
      - [Dependencies](#dependencies)
      - [Development Dependencies](#development-dependencies)
- [Usage](#usage)
  - [Configuration Requirements](#configuration-requirements)
- [Authentication](#authentication)
  - [Required Environment Variables](#required-environment-variables)
  - [Repository-Specific Examples](#repository-specific-examples)
    - [PyPI](#pypi)
    - [Artifactory](#artifactory)
    - [Nexus Repository](#nexus-repository)
    - [Custom Repositories](#custom-repositories)
- [Examples](#examples)
  - [Artifactory Configuration](#artifactory-configuration)
  - [Nexus Configuration](#nexus-configuration)
- [Migrating from Hardcoded URLs](#migrating-from-hardcoded-urls)
  - [Migration Steps](#migration-steps)
- [Error Handling](#error-handling)
  - [Configuration Errors](#configuration-errors)
  - [Authentication Errors](#authentication-errors)
- [Known Limitations](#known-limitations)
  - [Artifactory-Specific URL Handling](#artifactory-specific-url-handling)
  - [Repository URL Validation](#repository-url-validation)


## Features

- **Configurable Repository URLs**: Support for PyPI, Artifactory, Nexus, and custom repositories
- **Environment-specific Publishing**: Separate dev and prod environments with configurable suffixes
- **Automatic Configuration**: Interactive setup during container installation
- **Generic pybuild.py**: Works with any Python package repository
- **Configuration Validation**: Ensures all required settings are present before execution
- **Clear Error Messages**: Helpful guidance when configuration is missing or invalid

## Configuration

When you select Python development during installation, you'll be prompted to configure your package repository:

### Repository Types

1. **PyPI (default)**: Public Python Package Index
2. **Artifactory**: JFrog Artifactory enterprise repository
3. **Nexus**: Nexus Repository enterprise repository  
4. **Custom**: Any other Python package repository

### Configuration Files

All repository configuration is stored in `pyproject.toml` within the `[tool.pybuild]` section. **No default values are provided** - all configuration must be explicitly set.

#### Required Repository Configuration
```toml
[tool.pybuild]
publish_base_url = "https://upload.pypi.org/legacy/"    # Required: Where to publish packages
install_index_url = "https://pypi.org/simple/"          # Required: Where to install packages from
```

#### Optional Repository Configuration
```toml
[tool.pybuild]
install_extra_index_url = ""  # Optional: Additional package index
dev_suffix = "-dev"           # Optional: Suffix for dev environment URLs
prod_suffix = ""              # Optional: Suffix for prod environment URLs
```

#### Required Project Metadata Updates

The `pyproject.toml` template contains placeholder values that **must be updated** for your project:

##### Project Information
```toml
[project]
name = "your-project-name"                    # Replace "project-name"
description = "Your project description."     # Replace "<project descripton>."
license = "MIT"                              # Replace "<add license here>" (e.g., MIT, Apache-2.0, GPL-3.0)
keywords = ["python", "cli", "automation"]   # Replace placeholder keywords
authors = [{ name = "Your Name", email = "your.email@example.com" }]  # Update author info
```

##### Project URLs
```toml
[project.urls]
Documentation = "https://github.com/yourusername/yourproject/blob/main/README.md"
Homepage = "https://github.com/yourusername/yourproject"
Source = "https://github.com/yourusername/yourproject"
```

**Purpose of each URL:**
- **Documentation**: Link to your project's documentation (README, docs site, wiki)
- **Homepage**: Main project page (usually GitHub repository)  
- **Source**: Link to source code repository

##### Build Configuration Paths
```toml
[tool.hatch.version]
path = "src/yourproject/__about__.py"      # Replace "<project>" with your package name

[tool.hatch.build.targets.wheel]
packages = ["src/yourproject"]             # Replace "<project>" with your package name
```

##### Testing Configuration
```toml
[tool.coverage.run]
source_pkgs = ["yourproject", "tests"]     # Replace "<project>" with your package name
omit = ["src/yourproject/__about__.py"]    # Replace "<project>" with your package name

[tool.coverage.paths]
project = ["src", "*/yourproject/src"]     # Replace "<project>" with your package name
tests = ["tests", "*/yourproject/tests"]   # Replace "<project>" with your package name
```

#### Optional Customizations

##### Dependencies
Review and update the sample dependencies in the `dependencies` array to match your project's actual requirements:

```toml
dependencies = [
  # Replace these sample dependencies with your actual requirements
  "requests~=2.32",     # HTTP library
  "click~=8.1",         # CLI framework
  "pydantic~=2.5",      # Data validation
]
```

##### Development Dependencies
Update the `dev` optional dependencies as needed:

```toml
[project.optional-dependencies]
dev = [
  "pytest~=8.3",        # Testing framework
  "ruff~=0.9",          # Linting and formatting
  "mypy~=1.15.0",       # Type checking
]
```

The script will exit with clear error messages if required configuration is missing.

## Usage

The `pybuild.py` script provides these commands:

- `python pybuild.py build` - Build the package
- `python pybuild.py dev` - Build and install locally for development
- `python pybuild.py dev -c` - Run in continuous mode (watches for file changes)
- `python pybuild.py publish dev` - Publish to dev repository
- `python pybuild.py publish prod` - Publish to production repository
- `python pybuild.py test` - Run tests
- `python pybuild.py static_analysis` - Run SonarQube analysis

### Configuration Requirements

Before running any `pybuild.py` commands, ensure:

1. **pyproject.toml exists** in your project root
2. **[project] section** contains the package name
3. **[tool.pybuild] section** contains required repository URLs
4. **Environment variables** are set for authentication

If configuration is missing, the script will exit with helpful error messages guiding you to run `install.sh` for interactive setup.

## Authentication

The `pybuild.py` script uses Hatch's standard authentication environment variables, making it compatible with any repository type.

### Required Environment Variables
```bash
export HATCH_INDEX_USER="your_username"
export HATCH_INDEX_AUTH="your_password_or_token"
```

### Repository-Specific Examples

#### PyPI
```bash
export HATCH_INDEX_USER="your_pypi_username"
export HATCH_INDEX_AUTH="your_pypi_password"
# or for API tokens:
export HATCH_INDEX_USER="__token__"
export HATCH_INDEX_AUTH="your_api_token"
```

#### Artifactory
```bash
export HATCH_INDEX_USER="your_artifactory_username"
export HATCH_INDEX_AUTH="your_artifactory_password"
```

#### Nexus Repository
```bash
export HATCH_INDEX_USER="your_nexus_username"  
export HATCH_INDEX_AUTH="your_nexus_password"
```

#### Custom Repositories
Use whatever credentials your repository requires:
```bash
export HATCH_INDEX_USER="your_repo_username"
export HATCH_INDEX_AUTH="your_repo_token_or_password"
```

## Examples

### Artifactory Configuration
```toml
[tool.pybuild]
publish_base_url = "https://artifactory.company.com/artifactory/api/pypi/python-repo"
install_index_url = "https://artifactory.company.com/artifactory/api/pypi/python-repo/simple"
install_extra_index_url = "https://artifactory.company.com/artifactory/api/pypi/python-public/simple"
dev_suffix = "-dev"
prod_suffix = ""
```

### Nexus Configuration  
```toml
[tool.pybuild]
publish_base_url = "https://nexus.company.com/repository/pypi-internal/"
install_index_url = "https://nexus.company.com/repository/pypi-internal/simple"
install_extra_index_url = "https://nexus.company.com/repository/pypi-public/simple"
dev_suffix = "-dev" 
prod_suffix = ""
```

## Migrating from Hardcoded URLs

If you have an existing `pybuild.py` with hardcoded URLs, the new version will:

1. **Require pyproject.toml configuration** - No defaults are provided
2. **Read package name from [project] section** - Must be present
3. **Load all repository settings from [tool.pybuild] section** - Must be configured
4. **Validate required fields** - Will exit with clear errors if missing
5. **Maintain the same command-line interface** - All existing commands work the same

### Migration Steps

1. **Update pyproject.toml** with your repository URLs:
   ```toml
   [tool.pybuild]
   publish_base_url = "your-publish-url"
   install_index_url = "your-install-url"
   # Add optional fields as needed
   ```

2. **Update authentication variables** from old to new format:
   ```bash
   # Old format (no longer supported):
   # export ARTIFACTORY_CREDS_USR="username"
   # export ARTIFACTORY_CREDS_PSW="password"
   
   # New format (required):
   export HATCH_INDEX_USER="username"
   export HATCH_INDEX_AUTH="password"
   ```

3. **Test configuration** by running:
   ```bash
   python pybuild.py --help
   ```
   
   If configuration is missing, you'll get helpful error messages.

4. **Use install.sh for new projects** - The interactive setup will configure everything automatically.

## Error Handling

The updated `pybuild.py` provides clear error messages for common issues:

### Configuration Errors
- **Missing pyproject.toml**: "pyproject.toml file not found. This file is required for configuration."
- **Missing package name**: "Package name not found in pyproject.toml [project] section."
- **Missing repository config**: "Repository configuration not found in pyproject.toml [tool.pybuild] section."
- **Missing required URLs**: 
  - "publish_base_url must be configured in pyproject.toml [tool.pybuild] section."
  - "install_index_url must be configured in pyproject.toml [tool.pybuild] section."
- **Invalid configuration**: "Could not load pyproject.toml configuration: [specific error]"

### Authentication Errors  
- **Missing credentials**: 
  - "HATCH_INDEX_USER environment variable must be set."
  - "HATCH_INDEX_AUTH environment variable must be set."

All errors include helpful guidance on how to resolve the issue, often pointing users to run `install.sh` for interactive configuration setup.

## Known Limitations

### Artifactory-Specific URL Handling
The system still contains hardcoded logic for Artifactory URL patterns:

1. **Suffix Handling**: Special logic for detecting "artifactory" in URLs to handle dev/prod suffixes
2. **Simple URL Modification**: Hardcoded logic to replace "/simple" with suffix + "/simple" for Artifactory URLs

**Code Example**:
```python
if "artifactory" in base_url and suffix:
    return base_url + suffix

if "artifactory" in base_index:
    base_index = base_index.replace("/simple", dev_suffix + "/simple")
```

This means:
- **Artifactory** gets special suffix handling for dev/prod environments  
- **Other repositories** use generic suffix appending (may not work correctly for all repository types)
- **PyPI** is explicitly excluded from suffix handling

### Repository URL Validation
The system currently accepts any valid URL without validating repository compatibility. Users should ensure their URLs match their repository type's expected format.

**Future Enhancement**: The URL handling logic should be made more generic to support different repository types without hardcoded string matching.
