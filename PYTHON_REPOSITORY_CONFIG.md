# Python Package Repository Configuration

This document explains how to configure Python package repositories and project metadata for the development container.

## Automated Configuration

When you run `install.sh` and select Python extensions, the script will automatically guide you through configuring your Python project:

### What the Script Configures Automatically

1. **Project Metadata**: Project name, description, author information, license, and keywords
2. **GitHub Integration**: Automatically configures project URLs based on your GitHub username and repository name
3. **Package Structure**: Creates the proper `src/<package_name>/` directory structure with `__init__.py` and `__about__.py` files
4. **Repository URLs**: Configures package repository URLs for PyPI, Artifactory, or Nexus based on your selection

### Interactive Setup Process

The installation script will prompt you for:

- **Project Information**:
  - Project name (will be used for both the package name and directory structure)
  - Project description
  - License type (e.g., MIT, Apache-2.0, GPL-3.0)
  - Keywords for package discovery

- **Author Information**:
  - Your name
  - Your email address

- **GitHub Repository**:
  - Your GitHub username
  - GitHub project/repository name
  - (Used to automatically configure Documentation, Homepage, Source, and Bug Tracker URLs)

- **Package Repository Type**:
  - PyPI (default public repository)
  - JFrog Artifactory (enterprise)
  - Nexus Repository (enterprise)
  - Custom repository URLs

### Quick Start Checklist

After running the automated setup, verify your configuration:

1. **Project Structure Created**: ✅ Automatically done
   - `src/<your_package_name>/` directory created
   - `__about__.py` with version information
   - `__init__.py` with project description

2. **Project Metadata Configured**: ✅ Automatically done
   - Project name, description, license, keywords set
   - Author information configured
   - GitHub URLs properly set

3. **Repository Configuration**: ✅ Automatically done (if selected)
   - Package repository URLs configured
   - Environment suffixes set (if applicable)

## Manual Configuration (Advanced)

If you need to manually modify the configuration after the automated setup, the dynamic dev container supports configurable Python package repositories, making it suitable for use with PyPI, Artifactory, Nexus, or any other Python package repository.

- [Automated Configuration](#automated-configuration)
  - [What the Script Configures Automatically](#what-the-script-configures-automatically)
  - [Interactive Setup Process](#interactive-setup-process)
  - [Quick Start Checklist](#quick-start-checklist)
- [Manual Configuration (Advanced)](#manual-configuration-advanced)
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


### Repository Types

The automated setup supports the following repository types:

1. **PyPI (default)**: Public Python Package Index
2. **Artifactory**: JFrog Artifactory enterprise repository
3. **Nexus**: Nexus Repository enterprise repository  
4. **Custom**: Any other Python package repository

### Quick Start Checklist

To customize the `pyproject.toml` template for your project:

1. **Update Project Metadata** (Required):
   - [ ] Change `name` from "my-awesome-project" to your package name
   - [ ] Update `description` with your project's purpose
   - [ ] Set the correct `license` (MIT, Apache-2.0, etc.)
   - [ ] Replace `keywords` with relevant tags
   - [ ] Update `authors` with your information

2. **Configure URLs** (Recommended):
   - [ ] Update all GitHub URLs to point to your repository
   - [ ] Verify `Documentation` link points to your README or docs
   - [ ] Ensure `Bug Tracker` points to your issues page

3. **Update File Paths** (Required):
   - [ ] Replace "my_awesome_project" in `tool.hatch.version.path`
   - [ ] Replace "my_awesome_project" in `tool.hatch.build.targets.wheel.packages`
   - [ ] Replace "my_awesome_project" in all `tool.coverage` sections

4. **Customize Dependencies** (As Needed):
   - [ ] Review and update `dependencies` for your project's needs
   - [ ] Modify `dev` dependencies based on your development tools

5. **Repository Configuration** (If Using Private Repos):
   - [ ] Update `tool.pybuild` URLs for your package repository
   - [ ] Set environment variables for authentication

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

The `pyproject.toml` template contains example values that should be updated for your project:

##### Project Information
```toml
[project]
name = "my-awesome-project"                           # Your package name (lowercase, no spaces)
description = "A brief description of your project"  # What your project does
license = "MIT"                                      # Your license (MIT, Apache-2.0, GPL-3.0, etc.)
keywords = ["python", "cli", "automation"]          # Keywords for discoverability
authors = [
  { name = "Your Name", email = "your.email@example.com" }
]
```

##### Project URLs
```toml
[project.urls]
Documentation = "https://github.com/yourusername/my-awesome-project/blob/main/README.md"
Homepage = "https://github.com/yourusername/my-awesome-project"
Source = "https://github.com/yourusername/my-awesome-project"
"Bug Tracker" = "https://github.com/yourusername/my-awesome-project/issues"
```

**Purpose of each URL:**
- **Documentation**: Link to your project's documentation (README, docs site, wiki)
- **Homepage**: Main project page (usually GitHub repository)  
- **Source**: Link to source code repository
- **Bug Tracker**: Where users can report issues

##### Build Configuration Paths
```toml
[tool.hatch.version]
path = "src/my_awesome_project/__about__.py"      # Replace with your package name

[tool.hatch.build.targets.wheel]
packages = ["src/my_awesome_project"]             # Replace with your package name
```

##### Testing Configuration
```toml
[tool.coverage.run]
source_pkgs = ["my_awesome_project", "tests"]     # Replace with your package name
omit = ["src/my_awesome_project/__about__.py"]    # Replace with your package name

[tool.coverage.paths]
project = ["src", "*/my_awesome_project/src"]     # Replace with your package name
tests = ["tests", "*/my_awesome_project/tests"]   # Replace with your package name
```

#### Optional Customizations

##### Dependencies
The template includes common, sensible dependencies. Update them based on your project's needs:

```toml
dependencies = [
  "click>=8.0,<9.0",      # CLI framework for command-line tools
  "requests>=2.28,<3.0",  # HTTP library for web requests
  "pydantic>=2.0,<3.0",   # Data validation and parsing
]
```

##### Development Dependencies
Update the `dev` optional dependencies as needed:

```toml
[project.optional-dependencies]
dev = [
  "hatch>=1.14,<2.0",           # Build and project management tool
  "pytest>=8.0,<9.0",          # Testing framework
  "pytest-cov>=4.0,<5.0",      # Coverage reporting for tests
  "ruff>=0.9,<1.0",             # Fast Python linter and formatter
  "mypy>=1.15,<2.0",            # Static type checker
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
