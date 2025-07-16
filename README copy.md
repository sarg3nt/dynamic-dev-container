# Generic Dev Container

- [Making Changes to the Dev Container](#making-changes-to-the-dev-container)
- [Manually Build the Dev Container Image](#manually-build-the-dev-container-image)
- [Using the Dev Container Outside of VS Code](#using-the-dev-container-outside-of-vs-code)
- [Files and Directories](#files-and-directories)
  - [`Dockerfile`](#dockerfile)
  - [`mise`](#mise)
  - [`.devcontainer`](#devcontainer)
    - [Host Environment Variables](#host-environment-variables)
  - [`scripts`](#scripts)
  - [`cspell.json`](#cspelljson)
  - [`dev.sh`](#devsh)
  - [`run.sh`](#runsh)
- [Starship Powerline Prompt](#starship-powerline-prompt)
- [Initial Workstation Setup](#initial-workstation-setup)
  - [WSL](#wsl)
  - [Windows Font Install](#windows-font-install)
    - [Windows Terminal Font Setup](#windows-terminal-font-setup)
    - [Visual Studio Code Font Setup](#visual-studio-code-font-setup)

## Making Changes to the Dev Container

> [!NOTE]
> Follow these procedures when making changes to the dev container, such as upgrading packages, installing new packages, or fixing issues.

1. Pull the latest `main` branch.
1. Create a new branch for your changes.
1. Update the `devContainerVersion` string in `ci/Jenkinsfile` to a new version number.
1. Update the example build command in the `Dockerfile` to match the new version number.
1. Do your development work.
1. Push your changes to GitHub

## Using the Dev Container Outside of VS Code

> [!NOTE]
> Although optimized for use with a VS Code project, the dev container image can also be used standalone by passing in a few parameters, including a bind-mounted directory.

We've simplified this for you with the `run.sh` command.  
Execute `./run.sh` at the root, and it will start the container, mounting your current working directory.  
The following code is executed in the `run.sh` command:

In this example, we are mounting the current working directory using `pwd` (print working directory) to the destination `/workspaces/working`.  
All files in your current working directory will be accessible in the container under `/workspaces/working`.

```bash
docker run --mount type=bind,source="$(pwd)",target=/workspaces/working \
  -w /workspaces/working -it --rm -u vscode \
  ghcr.io/sarg3nt/dynamic-dev-container:latest zsh
```

- `--mount` mounts your current working directory to `/workspaces/working` inside the container.
- `-w` sets the working directory inside the container to `/workspaces/working`, so you start in that directory.
- `-it` opens an interactive terminal.
- `--rm` removes the container when it is closed, so you don't have to manually clean it up later.
- `-u` sets the user to `vscode`, which is the non-privileged user you should be working as in the container.

## Files and Directories

### `Dockerfile`

Is used to build the dev container image, which is used by the devcontainer.

### `mise`

`mise` is used to install most applications that are not `dnf` packages.  
The list of applications is located in `home/vscode/.config/mise/config.toml`.  
Some applications are version-locked and can be updated in the `config.toml` file.  

### `.devcontainer` 

This project's dev container configuration.  
The file in this repo uses its own dev container to provide all the tooling needed to manage and upgrade itself.  

You can use the `.devcontainer` folder as a template for new repositories by copying it into your VS Code project.

When using this `devcontainer.json` file as a template for a new project, you must change the following:

- Update `"name": "Generic Dev Container"` to match the target repository/project.
- In `"mounts": [`, change all instances of `generic-dev-*` to match the target repository/project.
- In `"runArgs": [`, change `"--name=generic-dev"` to match the target repository/project.
- Copy the `cspell.json` to the root of the new repo and edit as needed.

> [!TIP]  
> If you are creating a new project called `my-project` using the `generic-dev` dev container, copy the `.devcontainer` directory into the new VS Code project. Then, find and replace all instances of `generic-dev` in the `devcontainer.json` with `my-project`.
> Copy the `cspell.json` file as well. We don't copy this as part of the build since you may need to edit it for each repo.

#### Host Environment Variables

Some environment variables can be set on your host and are automatically passed into the dev container, as configured in `devcontainer.json`:

-  `ZSH_THEME`   — If you already have an Oh My ZSH theme set on your Linux host, it will be used in the dev container too.

### `scripts`

This directory contains all scripts used to build the dev container.

### `cspell.json`

The cspell config file that stores common words we want cspell to ignore.

### `dev.sh`

This script will open VS Code and wait for the dev container to open, then `docker exec` into the target container.
This makes getting into the dev container from your main terminal window much easier.

This file can be copied to other projects and reused. When doing so, the `docker_exec_command`, `project_name`, and `container_name` need to be changed to match your project.

### `run.sh`

This script launches the dev container outside of VS Code.
This is useful when you want to use the dev container for other purposes outside of VS Code.

## Starship Powerline Prompt

The terminal in the dev container uses [Starship](https://starship.rs/) to display a *smart* powerline-style prompt that includes the git branch, Kubernetes context and namespace, and other useful information. This prompt requires special Nerd Fonts that include glyphs to display properly. You can install these fonts using the PowerShell script shown below.

## Initial Workstation Setup

Instructions to set up your workstation.
For more information on Dev Containers, check out the [official docs](https://code.visualstudio.com/docs/devcontainers/containers).

### WSL

1. If you will be building Docker containers in Windows, install Docker Desktop for Windows following [Docker's instructions](https://docs.docker.com/desktop/install/windows-install/). If you do not need Docker for Windows support, you can [directly install Docker inside Ubuntu](https://docs.docker.com/engine/install/ubuntu/) **after** you install WSL and Ubuntu in the following steps.
2. Install VS Code from the [Visual Studio Code website](https://code.visualstudio.com/download) or from the Microsoft Store.
3. Open VS Code and click on the "Extensions" button on the left.
   - Search for "Dev Containers" and install it.
   - Search for "WSL" and install it.
4. WSL is the Windows Subsystem for Linux and facilitates the use of a Linux distribution on Windows.
   Follow the [Microsoft instructions](https://learn.microsoft.com/en-us/windows/wsl/install) to install WSL and a Linux distribution. We highly recommend Ubuntu.

### Windows Font Install

To get the full functionality of font ligatures and icons, you will need to install a [Nerd Font](https://www.nerdfonts.com/) from [Nerd Fonts Downloads](https://www.nerdfonts.com/font-downloads). If you skip this step, the Dev Container terminal command line will look odd and not have icons, making it harder to read.

Many of us use [FiraCode Nerd Font](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/FiraCode.zip) or [FiraMono Nerd Font](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/FiraMono.zip), but you can [preview](https://www.programmingfonts.org/#firacode) any of the fonts and choose which one is best for you.

Download your chosen font and [install it in Windows](https://support.microsoft.com/en-us/office/add-a-font-b7c5f17c-4426-4b53-967f-455339c564c1), then proceed to the next step.

#### Windows Terminal Font Setup

1. Open Windows Terminal, select the menu chevron to the right of the last tab, and select Settings.
2. On the left, select `Profiles` → `Defaults`.
3. Under `Additional Settings`, select `Appearance`.
4. Under `Font Face`, select the name of the font you downloaded. For example, if you chose the "FiraCode Nerd Font", select `FiraCode NF`. You may need to check `Show all items` or restart Windows Terminal to see the new fonts.

#### Visual Studio Code Font Setup

1. Select `File` → `Preferences` → `Settings`.
2. Expand `Text Editor` and select `Font`.
3. In the `Font Family` text box, paste the following:
   > [!NOTE]
   > This assumes you chose "FiraCode NF". If not, replace the first font name with the name of the font you installed in Windows.
   ```
   'FiraCode NF', 'CaskaydiaCove NF', Consolas, 'Courier New', monospace
   ```