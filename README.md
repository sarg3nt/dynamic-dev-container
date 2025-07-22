<!-- cspell:ignore sarg trivy gitui kubectx Fira Firacode Caskaydia Consolas openbao mise zoxide lsd devcontainer krew kubens kubebench popeye cmctl tealdeer goreleaser pnpm devcontainers -->

# Dynamic Dev Container

Welcome to the Dynamic Dev Container, a comprehensive, production-ready development environment designed for consistency, security, and flexibility. Built on Rocky Linux 10 and powered by the [mise](https://mise.jdx.dev/) tool manager, this project provides an intelligent, **Terminal User Interface (TUI)** setup to create the perfect containerized workspace for any project.

- [Why Choose This Dev Container?](#why-choose-this-dev-container)
- [What is a Dev Container?](#what-is-a-dev-container)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
  - [VS Code Extensions Required](#vs-code-extensions-required)
  - [Windows Users: WSL Setup](#windows-users-wsl-setup)
- [The TUI Installation Process](#the-tui-installation-process)
  - [1. **Automatic Dependency Check**](#1-automatic-dependency-check)
  - [2. **Welcome \& Navigation Guide**](#2-welcome--navigation-guide)
  - [3. **Project Configuration**](#3-project-configuration)
  - [4. **Tool Selection Workflow**](#4-tool-selection-workflow)
  - [5. **Smart Version Selection**](#5-smart-version-selection)
  - [6. **Configuration Summary**](#6-configuration-summary)
  - [7. **Dynamic File Generation**](#7-dynamic-file-generation)
- [Available Tools \& Languages](#available-tools--languages)
  - [Core Development Environments](#core-development-environments)
  - [Infrastructure \& Cloud Tools](#infrastructure--cloud-tools)
  - [Kubernetes Ecosystem](#kubernetes-ecosystem)
  - [General Command-Line Utilities](#general-command-line-utilities)
- [Baked-In Goodness](#baked-in-goodness)


## Why Choose This Dev Container?

- **Eliminate "It Works on My Machine"**: Get a consistent, reproducible environment for your entire team, ending configuration drift.
- **Intuitive TUI Setup**: A beautiful, easy-to-navigate Terminal User Interface guides you through setup with keyboard and mouse support, checkboxes, and smart form validation.
- **Security-First Approach**: Built on an enterprise-grade Rocky Linux 10 base, with container images that are regularly rebuilt to incorporate the latest security patches.
- **Production-Ready Tooling**: Comes packed with optional, industry-standard tools for modern cloud-native development:
  - **Languages**: Go, .NET, JavaScript/Node.js, Python
  - **Infrastructure**: OpenTofu (Terraform), OpenBao (Vault), Packer
  - **Kubernetes**: kubectl, Helm, k9s, krew, and advanced utilities
  - **Development Tools**: gitui, PowerShell, micro, tealdeer
- **Smart Defaults & Automation**: The installer automatically includes the right VS Code extensions based on the tools you select, saving you setup time.

## What is a Dev Container?

For those new to the concept, a VS Code Dev Container is a running Docker container with a well-defined tool and runtime stack. It allows you to use a container as a full-featured development environment.

- **Isolation**: Your project's environment is completely isolated from your local machine. You can have different versions of tools (like Node.js or Python) for different projects without conflicts.
- **Consistency**: Everyone on the team uses the exact same environment, libraries, and tools, which are defined in code (`.devcontainer/devcontainer.json`).
- **Reproducibility**: You can quickly and reliably reproduce a development environment on any machine that has VS Code and Docker.

This project takes the dev container concept to the next level by providing a powerful, customizable base and an interactive installer to tailor it to your specific needs.

## Quick Start

Get your custom development environment running in minutes with our intuitive TUI installer.

1.  **Clone or Download**: Get a local copy of this repository.
    ```bash
    git clone https://github.com/sarg3nt/dynamic-dev-container.git
    cd dynamic-dev-container
    ```
2.  **Run the TUI Installer**: Execute the `install.sh` script to launch the Terminal User Interface.
    ```bash
    # Launch the interactive TUI installer
    ./install.sh
    
    # Or specify a project path directly
    ./install.sh /path/to/your/new-project
    ```
3.  **Navigate the TUI**: Use the keyboard or mouse to navigate through the setup wizard:
    - **TAB/SHIFT+TAB** to navigate between buttons
    - **SPACE** to select/deselect checkboxes  
    - **ENTER** to confirm selections
    - **Mouse clicks** are fully supported
4.  **Launch the Dev Container**: Use the included `dev.sh` script to start your development environment:
    ```bash
    cd /path/to/your/new-project
    ./dev.sh
    ```
    This script will automatically open VS Code and start the the Dev Container build process then connect to the container.  The first time the container is started it can a few minutes to build but will be cached and very fast the next time you run it.

That's it! VS Code will build the container and connect to your new, fully configured development environment.

## Prerequisites

### VS Code Extensions Required

Before you can use dev containers, you need to install the Dev Containers extension in VS Code:

1. **Install the Dev Containers Extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Dev Containers" by Microsoft
   - Click Install

2. **Optional but Recommended Extensions**:
   - **Docker**: For managing Docker containers and images
   - **Remote - SSH**: If you plan to work with remote development environments

### Windows Users: WSL Setup

If you're on Windows, you'll need Windows Subsystem for Linux (WSL):

1. **Install WSL 2**:
   ```powershell
   # Run in PowerShell as Administrator
   wsl --install
   ```

1. **Install a Linux Distribution**:
   - Open Microsoft Store
   - Search for and install "Ubuntu" (recommended) or your preferred Linux distribution
   - Launch Ubuntu and complete the initial setup

1. **Install Docker** (choose one option):

   **Option A: Docker Desktop (Recommended for beginners)**
   - Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Ensure "Use WSL 2 based engine" is enabled in Docker Desktop settings
   - In Docker Desktop settings, enable integration with your WSL distro

   **Option B: Native Docker in WSL (Advanced users)**
   ```bash
   # Inside your WSL terminal (Ubuntu)
   # Update package index
   sudo apt update
   
   # Install Docker
   sudo apt install -y docker.io
   
   # Add your user to the docker group
   sudo usermod -aG docker $USER
   
   # Start and enable Docker service
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Log out and back in, or run:
   newgrp docker
   ```

1. **Windows Font Install**
  To get the full functionality of font ligatures and icons, you will need to install a [Nerd Font](https://www.nerdfonts.com/) from [Nerd Fonts Downloads](https://www.nerdfonts.com/font-downloads). If you skip this step, the Dev Container terminal command line will look odd and not have icons, making it harder to read.  
  Many of us use [FiraCode Nerd Font](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/FiraCode.zip) or [FiraMono Nerd Font](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/FiraMono.zip), but you can [preview](https://www.programmingfonts.org/#firacode) any of the fonts and choose which one is best for you.  
  Download your chosen font and [install it in Windows](https://support.microsoft.com/en-us/office/add-a-font-b7c5f17c-4426-4b53-967f-455339c564c1), then proceed to the next step.

  1. **Windows Terminal Font Setup**
     1. Open Windows Terminal, select the menu chevron to the right of the last tab, and select Settings.
     1. On the left, select `Profiles` → `Defaults`.
     1. Under `Additional Settings`, select `Appearance`.
     1. Under `Font Face`, select the name of the font you downloaded. For example, if you chose the "FiraCode Nerd Font", select `FiraCode NF`. You may need to check `Show all items` or restart Windows Terminal to see the new fonts.

  1. **Visual Studio Code Font Setup**

      1. Select `File` → `Preferences` → `Settings`.
      1. Expand `Text Editor` and select `Font`.
      1. In the `Font Family` text box, paste the following:
         > [!NOTE]
         > This assumes you chose "FiraCode NF". If not, replace the first font name with the name of the font you installed in Windows.
         ```
         'FiraCode NF', 'CaskaydiaCove NF', Consolas, 'Courier New', monospace
         ```

1. **Clone and Run from WSL**:
   ```bash
   # Inside your WSL terminal (Ubuntu)
   # Create a source code directory in Linux filesystem (recommended)
   mkdir -p ~/src
   cd ~/src
   
   git clone https://github.com/sarg3nt/dynamic-dev-container.git
   cd dynamic-dev-container
   ./install.sh
   ```

**Important Performance Notes**: 
- **Store code in Linux filesystem**: Keep your projects in directories like `~/src` or `~/projects` for optimal performance
- **Avoid Windows filesystem**: Files stored in `/mnt/c` (Windows C: drive) will have significantly slower I/O performance when accessed from WSL
- **Cross-platform access**: You can still access your Linux files from Windows Explorer at `\\wsl$\Ubuntu\home\yourusername\src`

**Note**: Always work within the WSL environment (not Windows PowerShell) when using this dev container for optimal performance and compatibility.

## The TUI Installation Process

The `install.sh` script provides a beautiful Terminal User Interface that makes setup intuitive and enjoyable. Here's what the experience looks like:

### 1. **Automatic Dependency Check**
The installer automatically detects your operating system and package manager, then offers to install the required `dialog` utility if it's not already present. Supports:
- **Rocky Linux/RHEL/CentOS/Fedora**: Uses `dnf` or `yum`
- **Ubuntu/Debian**: Uses `apt-get` or `apt`
- **Arch/Manjaro**: Uses `pacman`
- **openSUSE**: Uses `zypper`
- **Alpine**: Uses `apk`
- **macOS**: Uses `brew`

### 2. **Welcome & Navigation Guide**
A friendly welcome screen explains how to navigate the TUI with keyboard shortcuts and mouse support.

### 3. **Project Configuration**
A comprehensive form collects all your project details in one step:
- **Project Name**: Smart defaults based on your project path
- **Display Name**: Auto-generated human-readable version
- **Container Name**: Automatically creates Docker container naming
- **Docker Command**: Generates a short command alias for easy access

### 4. **Tool Selection Workflow**
The TUI guides you through tool categories with intelligent dependencies:
- **Development Languages**: Go, .NET, JavaScript/Node.js with version selection
- **Infrastructure Tools**: OpenTofu, OpenBao, Packer with version options
- **Kubernetes Ecosystem**: kubectl, Helm, k9s, and advanced utilities
- **Command-Line Tools**: gitui, tealdeer, micro, PowerShell
- **VS Code Extensions**: Automatically included based on selected tools, plus optional categories

### 5. **Smart Version Selection**
For key tools, the installer shows available major versions and lets you choose or use "latest":
- Fetches real-time version data using `mise ls-remote`
- Shows examples like "(e.g., 1.31, 1.30, 1.29)" for informed decisions
- Handles version patterns intelligently (semantic vs. date-based)

### 6. **Configuration Summary**
Before installation, see a comprehensive summary of your choices:
- Project settings and naming
- Selected tools organized by category  
- VS Code extensions that will be included
- Clear count of selected tools and categories

### 7. **Dynamic File Generation**
Based on your selections, the installer generates:
- **`.mise.toml`**: Defines tools and versions for automatic installation
- **`.devcontainer/devcontainer.json`**: Complete VS Code configuration with extensions and settings
- **`dev.sh`**: Customized script with your project-specific Docker commands

## Available Tools & Languages

You can choose to install any combination of the following tools.

### Core Development Environments

-   **Go**: The Go programming language, with an option to include **GoReleaser** for release automation.
-   **.NET**: The .NET SDK for building applications with C#, F#, and Visual Basic.
-   **JavaScript/Node.js**: A comprehensive JS ecosystem, including:
    -   **Node.js** (v19 for compatibility, see project README for customization)
    -   **pnpm**, **yarn**: Popular alternative package managers.
    -   **Deno**, **Bun**: Modern, fast JavaScript runtimes.
-   **Python**: Python v3.13 is included by default, along with the necessary VS Code extensions.

### Infrastructure & Cloud Tools

-   **OpenTofu**: The open-source successor to Terraform for infrastructure as code.
-   **OpenBao**: The open-source, community-driven fork of HashiCorp's Vault for secrets management.
-   **Packer**: The standard for building automated machine images.

### Kubernetes Ecosystem

-   **Core Tools**:
    -   **kubectl**: The essential command-line tool for interacting with Kubernetes clusters.
    -   **Helm**: The package manager for Kubernetes.
    -   **k9s**: A powerful terminal-based UI for managing your clusters.
    -   **kubectx / kubens**: Quickly switch between Kubernetes clusters and namespaces.
-   **Utilities (requires `krew` installation)**:
    -   **krew**: The plugin manager for `kubectl`.
    -   **dive**: A tool for exploring Docker image layers.
    -   **kubebench**: A Kubernetes benchmark tool.
    -   **popeye**: A utility that scans clusters for potential issues.
    -   **trivy**: A comprehensive vulnerability scanner.
    -   **cmctl**: A command-line tool for managing cert-manager.
    -   **k3d**: A lightweight wrapper to run k3s (Rancher's minimal Kubernetes) in Docker.

### General Command-Line Utilities

-   **gitui**: A blazingly fast, terminal-based UI for Git.
-   **tealdeer**: A fast and simple client for `tldr` pages (simplified man pages).
-   **micro**: A modern and intuitive terminal-based text editor.
-   **PowerShell**: Microsoft's cross-platform automation and configuration tool.

## Baked-In Goodness

Every container comes with these powerful utilities pre-installed and configured for an enhanced shell experience.

-   **mise**: The ultimate tool for managing tool versions.
-   **Starship**: A minimal, fast, and infinitely customizable prompt for any shell.
-   **Zoxide**: A smarter `cd` command that learns your habits.
-   **fzf**: A general-purpose command-line fuzzy finder.
-   **lsd**: A modern `ls` replacement with icons, colors, and more.
-   **zsh + plugins**: A powerful shell with auto-suggestions and syntax highlighting.
-   **Docker**: The Docker CLI is available inside the container to manage sibling containers.
