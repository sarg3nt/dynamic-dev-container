<!-- cspell:ignore sarg trivy gitui kubectx Fira Firacode Caskaydia Consolas openbao mise zoxide lsd devcontainer krew kubens kubebench popeye cmctl tealdeer goreleaser pnpm devcontainers -->

# Dynamic Dev Container

Welcome to the Dynamic Dev Container, a comprehensive, production-ready development environment designed for consistency, security, and flexibility. Built on Rocky Linux 10 and powered by the [mise](https://mise.jdx.dev/) tool manager, this project provides an intelligent, interactive setup to create the perfect containerized workspace for any project.

## Why Choose This Dev Container?

- **Eliminate "It Works on My Machine"**: Get a consistent, reproducible environment for your entire team, ending configuration drift.
- **Intelligent & Lean Setup**: The interactive installer asks you what you need, so you only install the tools required for your project. No bloat.
- **Security-First Approach**: Built on an enterprise-grade Rocky Linux 10 base, with container images that are regularly rebuilt to incorporate the latest security patches.
- **Production-Ready Tooling**: Comes packed with optional, industry-standard tools for modern cloud-native development, including Kubernetes, OpenTofu (Terraform), and Go.
- **Smart Defaults & Automation**: The installer automatically includes the right VS Code extensions based on the tools you select, saving you setup time.

## What is a Dev Container?

For those new to the concept, a VS Code Dev Container is a running Docker container with a well-defined tool and runtime stack. It allows you to use a container as a full-featured development environment.

- **Isolation**: Your project's environment is completely isolated from your local machine. You can have different versions of tools (like Node.js or Python) for different projects without conflicts.
- **Consistency**: Everyone on the team uses the exact same environment, libraries, and tools, which are defined in code (`.devcontainer/devcontainer.json`).
- **Reproducibility**: You can quickly and reliably reproduce a development environment on any machine that has VS Code and Docker.

This project takes the dev container concept to the next level by providing a powerful, customizable base and an interactive installer to tailor it to your specific needs.

## Quick Start

Get your custom development environment running in minutes.

1.  **Clone or Download**: Get a local copy of this repository.
    ```bash
    git clone https://github.com/sarg3nt/dynamic-dev-container.git
    cd dynamic-dev-container
    ```
2.  **Run the Installer**: Execute the `install.sh` script, pointing it to your project's directory.
    ```bash
    # This will create a new project directory with the dev container files
    ./install.sh /path/to/your/new-project
    ```
3.  **Follow the Prompts**: The script will guide you through an interactive setup. Choose the tools and languages you need.
4.  **Launch the Dev Container**: Open your new project in VS Code. When prompted to "Reopen in Container", click it. If you aren't prompted, open the command palette (`Ctrl+Shift+P`) and select `Dev Containers: Reopen in Container`.

That's it! VS Code will build the container and connect to your new, fully configured development environment.

## The Installation Process (`install.sh`)

The `install.sh` script is the heart of this project. It turns a generic template into a specific, customized development environment.

1.  **Project Configuration**: It starts by asking for key details about your project, like its name and the desired Docker container name. It even generates smart defaults to save you time.
2.  **Interactive Tool Selection**: The script then walks you through a series of yes/no questions, allowing you to select toolsets by category. If you say no to a primary tool (like `kubectl`), it's smart enough to skip questions about related sub-tools (like `helm`).
3.  **Version Selection**: For key tools like Go, .NET, and `kubectl`, the script asks which version you want to install, showing you the latest available major versions as examples.
4.  **Dynamic File Generation**: Based on your selections, the script generates two critical files:
    -   `.mise.toml`: Defines the tools and versions that `mise` will install inside the container.
    -   `.devcontainer/devcontainer.json`: Configures every aspect of the VS Code environment, from which extensions to install to editor settings.
5.  **File Copy & Cleanup**: The script copies all the necessary template files into your project directory, overwrites the templates with your customized versions, and then cleans up the installer script itself, leaving your project clean.

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
