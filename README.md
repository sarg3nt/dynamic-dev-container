# Generic Dev Container

A comprehensive development container setup with intelligent tool selection and automatic configuration.

## Quick Start

1. Run the installation script to set up a new project:
   ```bash
   ./install.sh /path/to/your/project
   ```

2. Follow the interactive prompts to customize your development environment

3. Navigate to your project and start the dev container:
   ```bash
   cd /path/to/your/project
   ./dev.sh
   ```

## Environment Variables

### GitHub Token (Recommended)

To avoid GitHub API rate limiting when installing tools, set a GitHub personal access token:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export GITHUB_TOKEN="your_github_token_here"
```

**Creating a GitHub Token:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `public_repo` scope (no additional permissions needed)
3. Copy the token and set it as an environment variable

**Security Note:** The token is only passed through to the container and is not stored in any configuration files.

### Other Optional Environment Variables

- `ZSH_THEME`: Set a custom Zsh theme (defaults to Starship if not set)

## Features

- **Interactive Setup**: Choose only the tools and extensions you need
- **Smart Defaults**: Minimal installation by default with "No" as default for all tools
- **Automatic Correlation**: Installing tools automatically includes relevant VS Code extensions
- **Project Customization**: Container names, display names, and shortcuts customized per project
- **File Management**: Intelligently copies configuration files without overwriting existing ones

## Tool Categories

### Infrastructure & Cloud
- OpenTofu (Terraform alternative)
- OpenBao (Vault alternative)
- Kubernetes tools (kubectl, helm, k9s, kubectx)
- Additional Kubernetes utilities (krew, dive, popeye, trivy, k3d, cmctl)
- Packer

### Programming Languages
- Go (with goreleaser)
- PowerShell
- Python support (via VS Code extensions)

### Development Utilities
- Git UI (gitui)
- TealDeer (fast tldr client)

### VS Code Extensions
- Language-specific extensions automatically included when tools are installed
- Optional extensions for Python, Markdown, Shell/Bash, and JavaScript/TypeScript

## File Structure

The installation script copies and configures:
- `.devcontainer/` - VS Code dev container configuration
- `.mise.toml` - Tool version management
- `dev.sh` - Container management script
- `run.sh` - Additional run script
- `cspell.json` - Spell checker configuration
- `.gitignore` - Git ignore rules (if not present)
- `pyproject.toml` & `requirements.txt` - Python configuration (if Python extensions selected)

## Customization

All template sections in `.mise.toml` and `.devcontainer/devcontainer.json` are extracted from source files, ensuring consistency and easy maintenance across projects.