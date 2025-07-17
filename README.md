<!--cspell:ignore sarg trivy gitui kubectx Fira Firacode Caskaydia Consolas openbao mise -->
# Dynamic Dev Container

A comprehensive, production-ready development container built on Rocky Linux 10 with intelligent tool selection using [mise](https://mise.jdx.dev/) and automatic configuration. This container is regularly built and maintained to ensure security and up-to-date tooling.

## Quick Start

1. **Clone or download** this repository to your local machine
2. **Run the installation script** to set up a new project:
   ```bash
   ./install.sh /path/to/your/project
   ```
3. **Follow the interactive prompts** to customize your development environment
4. **Navigate to your project** and start the dev container:
   ```bash
   cd /path/to/your/project
   ./dev.sh
   ```

## Key Benefits

- **Zero Configuration Drift**: Containerized environment ensures consistent development experience across all machines
- **Intelligent Tool Selection**: Interactive setup installs only what you need - no bloat
- **Security First**: Built on Rocky Linux 10 with regular automated builds to maintain security updates
- **Production Ready**: Includes enterprise-grade tools for cloud infrastructure, Kubernetes, and modern development
- **Smart Defaults**: Minimal installation by default with sensible version pinning for stability
- **Project Isolation**: Each project gets its own customized container configuration

## Environment Variables

### GitHub Token (Highly Recommended)

To avoid GitHub API rate limiting when installing tools, set a GitHub personal access token:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export GITHUB_TOKEN="your_github_token_here"
```

**Creating a GitHub Token:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `public_repo` scope (no additional permissions needed)
3. Copy the token and set it as an environment variable

**Why This Matters:** Many tools are downloaded from GitHub releases. Without a token, you may hit rate limits (60 requests/hour), causing installation failures. With a token, you get 5,000 requests/hour.

**Security Note:** The token is only used during container builds and tool installation - it's not stored in any configuration files.

### Other Optional Environment Variables

- `ZSH_THEME`: Set a custom Zsh theme (defaults to Starship if not set)
- `TZ`: Timezone setting (defaults to America/Los_Angeles)

## Features

### Container Infrastructure
- **Base OS**: Rocky Linux 10 (Red Quartz) - Enterprise-grade stability
- **Built with GitHub Actions**: Regularly updated container images ensure security and latest tooling
- **Multi-stage Build**: Optimized for size and security using Docker best practices
- **Tool Management**: [mise](https://mise.jdx.dev/) for consistent, reproducible tool installations

### Smart Setup Process
- **Interactive Setup**: Choose only the tools and extensions you need
- **Smart Defaults**: Minimal installation by default with "No" as default for all optional tools
- **Automatic Correlation**: Installing tools automatically includes relevant VS Code extensions
- **Project Customization**: Container names, display names, and shortcuts customized per project
- **File Management**: Intelligently copies configuration files without overwriting existing ones
- **Command Shortcuts**: Creates personalized Docker exec shortcuts for quick container access

### Version Management
- **Pinned Critical Tools**: Specific versions for stability (Python 3.13, OpenTofu 1.10.2, kubectl 1.32)
- **Latest Stable Tools**: Auto-updating for non-critical utilities (helm, k9s, gitui, etc.)
- **Security Focus**: Base tools updated with each container build

## Tool Categories

### Infrastructure & Cloud Tools
- **OpenTofu** (v1.10.2) - Open-source Terraform alternative for infrastructure as code
- **OpenBao** (v2.3.1) - Open-source Vault alternative for secrets management  
- **Packer** (latest) - HashiCorp image builder for automated machine images

### Kubernetes Ecosystem
**Core Tools:**
- **kubectl** (v1.32) - Kubernetes command-line tool
- **helm** (latest) - Package manager for Kubernetes
- **k9s** (latest) - Terminal-based UI for Kubernetes clusters
- **kubectx/kubens** (latest) - Fast way to switch between clusters and namespaces

**Additional Utilities:**
- **krew** (latest) - kubectl plugin manager
- **dive** (latest) - Docker image layer explorer
- **popeye** (latest) - Kubernetes cluster sanitizer
- **trivy** (latest) - Vulnerability scanner for containers and dependencies
- **k3d** (latest) - Lightweight Kubernetes for development
- **cmctl** (latest) - cert-manager CLI tool

### Programming Languages & Runtimes
- **Python** (v3.13) - Latest stable Python with comprehensive package management
- **Go** (latest) - Go programming language with goreleaser for releases
- **PowerShell** (latest) - Cross-platform PowerShell for automation

### Development Utilities
- **Git UI (gitui)** (latest) - Fast terminal-based Git interface
- **TealDeer** (latest) - Fast implementation of tldr (simplified man pages)
- **Starship** (built-in) - Modern, fast shell prompt
- **Zoxide** (built-in) - Smarter cd command with frecency
- **fzf** (built-in) - Command-line fuzzy finder
- **lsd** (built-in) - Modern ls replacement with icons and colors

### VS Code Extensions
**Automatically Included:**
- Language-specific extensions are automatically included when related tools are installed
- GitHub integration (Copilot, Pull Requests, Themes)
- Git visualization tools

**Optional Categories:**
- Python development tools (if Python extensions selected)
- Markdown editing and preview tools
- Shell/Bash scripting support
- JavaScript/TypeScript development tools

## How It Works

### Installation Process
1. **Interactive Configuration**: The `install.sh` script guides you through tool selection with smart defaults
2. **File Generation**: Creates customized `.devcontainer/devcontainer.json` and `.mise.toml` files
3. **Project Setup**: Copies necessary scripts and configuration files to your project directory
4. **Container Naming**: Generates unique container names and optional command shortcuts

### Container Lifecycle
1. **Build Phase**: Container is built from Rocky Linux 10 base with mise tool manager
2. **Tool Installation**: Selected tools are installed using mise during container creation
3. **Post-Create**: Python dependencies and additional configurations are applied
4. **Ready**: Development environment is fully configured and ready to use

### File Structure

The installation script copies and configures:
- **`.devcontainer/`** - VS Code dev container configuration with lifecycle scripts
- **`.mise.toml`** - Tool version management configuration (customized per project)
- **`.krew_plugins`** - kubectl plugin configuration for krew (customize which plugins to install)
- **`dev.sh`** - Container management script (customized with project settings)
- **`run.sh`** - Standalone container runner (uses pre-built images)
- **`cspell.json`** - Spell checker configuration for consistent documentation
- **`.gitignore`** - Git ignore rules (only if not already present)
- **`pyproject.toml` & `requirements.txt`** - Python configuration (only if Python extensions selected)

### Version-Locked Tools

For stability and reproducibility, certain critical tools are pinned to specific versions:

- **Python**: 3.13 (latest stable with enhanced performance)
- **OpenTofu**: 1.10.2 (infrastructure-as-code stability)
- **kubectl**: 1.32 (Kubernetes API compatibility)
- **Base Container Tools**: cosign, fzf, lsd, starship, yq, zoxide (managed via mise)

All other tools use "latest" versions and are updated with each container build.

## Container Images & Updates

### Automated Builds
- **Container Registry**: `ghcr.io/sarg3nt/dynamic-dev-container`
- **Build Process**: Containers are built regularly using GitHub Actions to ensure:
  - Latest security patches from Rocky Linux 10 base
  - Updated system packages and dependencies
  - Current versions of all "latest" tagged tools
  - Validation of tool installations and compatibility

### Image Versioning
- **Latest Tag**: `ghcr.io/sarg3nt/dynamic-dev-container:latest` (recommended for most users)
- **Version Tags**: Specific versions available for reproducible builds
- **Branch Tags**: Development branches get their own tags for testing

### Security & Maintenance
- **Base OS**: Rocky Linux 10 provides enterprise-grade security and stability
- **Regular Updates**: Automated builds ensure timely security patches
- **Minimal Attack Surface**: Only essential packages are installed
- **Non-root User**: Container runs as `vscode` user for enhanced security

## Usage Scenarios

### Local Development
Use the `dev.sh` script for full VS Code integration with your local project:
```bash
cd /path/to/your/project
./dev.sh  # Opens VS Code with the dev container
```

### Standalone CLI Usage
Use the `run.sh` script for command-line work without VS Code:
```bash
./run.sh              # Uses latest tag
./run.sh 1.0.4         # Uses specific version
```

### CI/CD Pipelines
Reference the container directly in your workflows:
```yaml
container: ghcr.io/sarg3nt/dynamic-dev-container:latest
```

## Customization & Extension

### Template Extraction System
All template sections in `.mise.toml` and `.devcontainer/devcontainer.json` are extracted from source files using special markers, ensuring consistency and easy maintenance across projects:

```toml
#### Begin Environment ####
[env]
MISE_PYTHON_COMPILE = false
#### End Environment ####
```

### Adding Custom Tools
1. **Modify your project's `.mise.toml`**: Add new tools after initial setup
2. **Rebuild container**: Run `./dev.sh` to rebuild with new tools
3. **VS Code Extensions**: Add corresponding extensions to `.devcontainer/devcontainer.json`

### kubectl Plugin Configuration
Customize which kubectl plugins are installed via krew by editing `.krew_plugins`:

```bash
# Default plugins (one per line)
access-matrix
blame
get-all
node-restart
switch-config
view-allocations

# Add your own plugins
ctx
ns
score
```

- **Comments**: Lines starting with `#` are ignored
- **Empty Lines**: Blank lines are ignored
- **Plugin Names**: Use the exact names from `krew search`
- **Fallback**: If the file is missing, a default set of plugins is installed

### Environment Customization
- **Timezone**: Set `TZ` environment variable in `devcontainer.json`
- **Shell Theme**: Set `ZSH_THEME` environment variable (defaults to Starship)
- **Python Path**: Automatically configured for mise-installed Python
- **Custom Variables**: Add your own environment variables to the `containerEnv` section

## Troubleshooting

### Common Issues
1. **GitHub Rate Limiting**: Set `GITHUB_TOKEN` environment variable before running installation
2. **Permission Denied**: Ensure Docker daemon is running and your user has Docker permissions
3. **Container Won't Start**: Check Docker Desktop is running and has sufficient resources
4. **Tool Installation Fails**: Verify internet connectivity and GitHub token (if using one)

### Getting Help
- Check the container logs: `docker logs <container-name>`
- Verify tool installation: `mise list` inside the container
- Test connectivity: `curl -s https://api.github.com/rate_limit` (with GITHUB_TOKEN set)

## Contributing

This project follows infrastructure-as-code principles. To contribute:
1. Fork the repository
2. Test changes in a local development environment
3. Submit pull requests with clear descriptions
4. Ensure all tools install successfully and containers build properly

---

**Built with ❤️ for modern development workflows**
