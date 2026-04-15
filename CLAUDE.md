# CLAUDE.md

Notes for Claude Code on how this repository is structured. Read this first when picking up new work.

## What this repo is

A reusable VS Code Dev Container. Two distinct artifacts ship from one repo:

1. **Base image** — `ghcr.io/sarg3nt/dynamic-dev-container` — built from the root [Dockerfile](Dockerfile). Rocky Linux 10 UBI + `mise` + a curated set of CLI tools. Built and pushed by [.github/workflows/release.yml](.github/workflows/release.yml) (on tag push) and [.github/workflows/release-weekly.yml](.github/workflows/release-weekly.yml) (Sunday cron, weekly).
2. **Per-project devcontainer** — [.devcontainer/Dockerfile](.devcontainer/Dockerfile) FROMs the published base image and layers project-specific tools on top by running `.devcontainer/scripts/{10,20,30,40}_*.sh` against the consuming project's `.mise.toml`, `.krew_plugins`, and `requirements.txt`.

The TUI [install.sh](install.sh) is the bootstrap a user runs in a *new* project to copy `.devcontainer/`, `.mise.toml`, `.krew_plugins`, etc. into it. It has nothing to do with the container build itself.

## Build pipeline (base image)

[Dockerfile](Dockerfile) is a two-stage build:

- Stage `mise`: `FROM jdxcode/mise:<pinned>` — just to lift the `mise` binary.
- Stage `final`: `FROM rockylinux/rockylinux:10-ubi@sha256:...`. Runs three numbered scripts via `--mount=type=bind`:
  - [scripts/10_install_system_packages.sh](scripts/10_install_system_packages.sh) — `dnf` packages, EPEL, Docker CE repo, devcontainers `common-utils` feature.
  - [scripts/20_install_mise_tools.sh](scripts/20_install_mise_tools.sh) — `mise install` against [home/vscode/.config/mise/config.toml](home/vscode/.config/mise/config.toml) (the *base* mise config; NOT the project-level `.mise.toml`).
  - [scripts/30_install_other_apps.sh](scripts/30_install_other_apps.sh) — fzf shell completions, Oh-My-Zsh plugins.
  - [scripts/40_setup_ssh_known_hosts.sh](scripts/40_setup_ssh_known_hosts.sh).

Then COPYs `home/` and `usr/` to populate skel files (`.zshrc`, `.bashrc`, helper libs in `/usr/bin/lib/sh/`).

## Build pipeline (per-project devcontainer)

[.devcontainer/Dockerfile](.devcontainer/Dockerfile) FROMs the base image and runs four scripts that read the *project root*:

- `10_install_packages.sh` — system packages from `.packages`.
- `20_install_mise_tools.sh` — `mise install` against project's `.mise.toml`.
- `30_install_krew_plugins.sh` — kubectl plugins from `.krew_plugins`.
- `40_install_python_packages.sh` — `pip install -r requirements.txt`.

Lifecycle hooks in [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json):

- `initializeCommand` → [.devcontainer/scripts/initialize_command.sh](.devcontainer/scripts/initialize_command.sh) (runs on host: pulls latest base image, ensures `~/.docker`, `~/.kube`, `~/.ssh` exist).
- `postStartCommand` → [.devcontainer/scripts/post_start_command.sh](.devcontainer/scripts/post_start_command.sh) (runs in container: copies `~/.gitconfig-localhost`, `~/.ssh-localhost`, `~/.kube-localhost`, `~/.docker-localhost` into their real homes; runs `mise install` again for project tools; `npm install` if `package.json`).

## mise

Authoritative tool/version list lives in two places:

- [home/vscode/.config/mise/config.toml](home/vscode/.config/mise/config.toml) — baked into the base image.
- [.mise.toml](.mise.toml) at project root — added by users for project-specific tools.

Three tools come from custom asdf plugins under `[alias]`: `kubebench`, `tealdeer`, `micro` — all `asdf:sarg3nt/asdf-*`. If any of these break on a new platform, suspect the plugin.

## Multi-arch support

Target platforms: `linux/amd64` and `linux/arm64`. The latter covers Apple Silicon Macs running Docker Desktop (the container runs as linux/arm64 inside the Mac's Linux VM).

- Base image (Rocky Linux 10 UBI) and `mise` image: both multi-arch ✅.
- All `mise` tools we install are available for `linux/arm64` (mise auto-detects).
- GitHub Actions release workflows already use `docker buildx` with `--platform linux/amd64,linux/arm64`.
- [Makefile](Makefile) has multiplatform targets but they had bugs — see history of `build-multi*` targets.
- [.github/workflows/container-test.yml](.github/workflows/container-test.yml) only builds for the runner's native arch (amd64). Use a matrix if you need true cross-arch testing.

Host scripts ([dev.sh](dev.sh), [run.sh](run.sh), [install.sh](install.sh)) detect macOS via `uname -s == Darwin`. `install.sh` requires Bash 4+ (warn macOS users to `brew install bash`).

## Things that bite

- `python.pythonPath`, `dotnet`, `kubectl`, `powershell` paths in [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) are hardcoded to specific patch versions under `/home/vscode/.local/share/mise/installs/<tool>/<version>/`. They drift whenever mise resolves a different patch — including across architectures. Prefer `latest` symlinks under `installs/<tool>/latest` or env vars resolved at container start.
- `--load` only works with single-platform `buildx` builds. Multi-platform builds must `--push` to a registry or write to an OCI tarball.
- `.devcontainer/devcontainer.json` mounts assume Unix-style host paths (`${localEnv:HOME}/.docker` etc.) — fine on macOS, but `dev.sh` does WSL path conversion when `wslpath` is present.

## Layout

- `Dockerfile`, `Makefile` — base image build.
- `.devcontainer/` — per-project devcontainer (Dockerfile + scripts + devcontainer.json).
- `scripts/` — base image build scripts (run inside Dockerfile).
- `home/`, `usr/` — files copied into the base image (skel + helper libs).
- `images/` — README assets.
- `workflow_scripts/` — scripts run by GitHub Actions ([get_latest_version.sh](workflow_scripts/get_latest_version.sh)).
- `install.sh` — interactive TUI; bootstraps a new project (does NOT build the container).
- `pybuild.py`, `pyproject.toml`, `requirements.txt` — Python project scaffolding template.
- `dev.sh`, `run.sh` — host-side helpers to launch the container.
