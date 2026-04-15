# TASKS

This task file is for Claude Code and I to work on tasks in this repository.
This repository is a generic and dynamic dev container for Visual Studio Code.

## Make work with a M series Macintosh

The dev container was originally built to work on Linux and WSL in Windows.
This task is to fix issues preventing the dev container from working my new M5 MacBook Pro.

### Architecture overview

See [CLAUDE.md](CLAUDE.md) for the deep dive on how the build pipeline, mise, and devcontainer lifecycle hooks fit together. The short version: the base image is Rocky Linux 10 UBI + `mise` + curated tools; an Apple Silicon Mac runs it as `linux/arm64` inside Docker Desktop's Linux VM.

### Discovered issues

Verified by reading the actual files (not assumed). Each item lists the file and the concrete problem.

#### Build / multi-arch

1. [Makefile](Makefile):17 — `build-multiplatform` uses `--platform linux/amd64,linux/arm64` together with `--load`. `docker buildx --load` only supports a single platform; this command fails as written. Also the default `build` target uses `docker build` (not `buildx`), so it ignores BuildKit's cross-platform features.
1. [.github/workflows/container-test.yml](.github/workflows/container-test.yml):60-81 — sets up QEMU for both archs but the `build-push-action` step has no `platforms:` arg, so the test build only ever runs for the runner's native arch (amd64). arm64 regressions in the build will not be caught in CI.
1. [.github/workflows/container-test.yml](.github/workflows/container-test.yml):178-184 — same issue in the vulnerability-check job.

#### devcontainer.json hardcoded paths

These resolve to the wrong path whenever mise installs a different patch version, including across architectures (mise sometimes resolves different patches for arm64 vs amd64).

1. [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json):272,276 — `dotnet` pinned to `9.0.302`.
1. [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json):351-352 — `python` pinned to `3.13.5` even though `.mise.toml` specifies `3.13.11`. Already broken on x86_64.
1. [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json):399 — `kubectl` pinned to `1.33.2`.
1. [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json):418 — `powershell` pinned to `7.5.2`.

#### Install script bug (not arch-specific but found during the audit)

1. [install.sh](install.sh):212-220 — `sed_inplace()` calls itself recursively on the Linux branch instead of calling `sed`. Infinite loop; the macOS branch works. Real bug.

#### .NET on linux/arm64 caveat

1. The `csdevkit` VS Code extension (proprietary Microsoft) does not support `linux/arm64` officially. The `ms-dotnettools.csharp` (Roslyn) extension does. On Apple Silicon, `csdevkit` features may be unavailable inside the container — note this in README rather than try to "fix" it. No action required in code, only documentation.

#### Custom asdf plugins

`kubebench`, `tealdeer`, `micro` come from `asdf:sarg3nt/asdf-*` plugins ([.mise.toml](.mise.toml):78-81). I did not verify each plugin's arm64 support; if any fails on an M5 build, replace with the upstream mise/asdf plugin or pin a known-good version. Track here only if a build actually fails.

### Plan

Ordered by blast radius (smallest first).

1. **Fix `install.sh` `sed_inplace` recursion** — one-line bug fix.
2. **Rewrite Makefile multi-arch targets** — `build` stays as native single-arch `buildx --load`; add `build-multi` (no `--load`, OCI cache only, for cross-arch verification); keep `build-push-multi` for publishing. Remove the broken `build-multiplatform`.
3. **Fix devcontainer.json hardcoded versions** — replace pinned paths with the `latest` symlink that mise maintains under `~/.local/share/mise/installs/<tool>/latest/`. (Mise creates these symlinks automatically; verified by mise docs.) This decouples the devcontainer from patch-version drift across archs.
4. **Update `container-test.yml`** — add a `strategy.matrix.platform` over `[linux/amd64, linux/arm64]` so the test build runs on both architectures via QEMU, and pass `platforms:` through to `build-push-action`. Same for the vulnerability-check job.
5. **README note** — add a short "Apple Silicon" section pointing out: container runs as `linux/arm64`; `csdevkit` is amd64-only and may degrade .NET tooling; everything else works. (Skipping unless the user asks — README updates were not in scope.)
6. **Verify on the M5** — once 1-4 land, the user runs the build locally on the Mac and reports any failures (custom asdf plugins are the most likely surprise). Iterate on whatever actually breaks rather than pre-emptively patching.

### Out of scope

- Native macOS support without Docker (the project is intentionally container-based; CLAUDE.md states this).
- Replacing custom asdf plugins (only if they actually break on arm64).
