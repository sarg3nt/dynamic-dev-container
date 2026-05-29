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

### Plan (completed in iteration 1)

1. **Fix `install.sh` `sed_inplace` recursion** — done, [install.sh](install.sh):218.
2. **Rewrite Makefile multi-arch targets** — done, [Makefile](Makefile). `build`/`build-no-cache` use `buildx --platform <host>` with `--load`; `build-multi` cross-compiles both archs; `build-push-multi` publishes the manifest.
3. **Update `container-test.yml`** — done, both jobs now matrix over `[linux/amd64, linux/arm64]` and pass `platforms:` to `build-push-action`.
4. Devcontainer.json hardcoded paths — deferred (see below).
5. README note — deferred (see below).

### Iteration 2 — bring the build up on Apple Silicon

Issues found while actually running `make build` on the M5. Each was verified by reproducing the failure, fixing it, and rebuilding.

1. **jdxcode/mise arm64 binary has a `libbz2.so.1.0` runtime dep that Rocky 10 does not satisfy.**
   Rocky ships `libbz2.so.1` (no `.1.0` SONAME symlink). The jdxcode image built the arm64 variant against a distro that does. On amd64 it never mattered because the amd64 variant happens to be statically linked.
   Fix: dropped the multi-stage `FROM jdxcode/mise`. [Dockerfile](Dockerfile) now downloads the `linux-x64` / `linux-arm64` glibc mise binary directly from the pinned GitHub release and verifies it against per-arch SHA256s (also pinned via ARGs). Added `bzip2-libs` to [scripts/10_install_system_packages.sh](scripts/10_install_system_packages.sh) so the glibc binary resolves at runtime.
   The musl static variant also doesn't work — see the next issue.

2. **mise Python auto-selects a broken upstream tarball on arm64.**
   For `python = "3.13"` (floating patch) mise picks `cpython-3.13.13+20260414-aarch64-unknown-linux-gnu-freethreaded-install_only_stripped.tar.gz` from python-build-standalone, which ships without a `lib/` directory and makes mise refuse to install. (Same story for the musl variant — confirmed why switching to the musl mise binary didn't help.)
   Fix: removed `python` from the base image mise config ([home/vscode/.config/mise/config.toml](home/vscode/.config/mise/config.toml)). Base image ships *without* Python; consumers declare their Python version in their project's `.mise.toml` (the root [.mise.toml](.mise.toml) already pins `python = "3.13.11"`, which resolves to the working `install_only_stripped` glibc tarball). Bonus: smaller base image.

3. **Per-arch base-image digest pinning, passed through as build args.**
   [Makefile](Makefile) now tracks `ROCKY_AMD64_DIGEST`, `ROCKY_ARM64_DIGEST`, and `ROCKY_INDEX_DIGEST`; native `make build` passes the host-arch manifest digest via `--build-arg BASE_IMAGE=…` while multi-platform targets pass the OCI index digest. mise binaries likewise pinned with per-arch SHA256s as Dockerfile ARGs ([Dockerfile](Dockerfile)).

4. **GITHUB_TOKEN passthrough was broken end-to-end.**
   Makefile passed `--build-arg GITHUB_API_TOKEN=…`, Dockerfile declared `ARG GITHUB_TOKEN`, so the token was silently ignored and every mise tool install risked a rate-limit failure. Fixed in both [Makefile](Makefile) and [Dockerfile](Dockerfile); `GITHUB_TOKEN` and `GITHUB_API_TOKEN` are now both exported as ENV inside the final image so mise and any legacy scripts find it.

5. **mise binary size optimization.**
   Installed `binutils` persistently in [scripts/10_install_system_packages.sh](scripts/10_install_system_packages.sh) (~4MB, also useful for devs) and `strip` the mise binary in its RUN step. Saved ~10MB net on the final image. (Initial attempt installed/removed binutils in the mise RUN; that added more RPM-db cruft than strip saved — reverted.)

#### Final verified result on linux/arm64 (M5 MacBook Pro)

- `make build` succeeds end-to-end.
- Image size: **778 MB** (down from 788 MB before strip).
- Layer breakdown: Rocky base 251 MB, system-packages layer 432 MB, mise binary 52 MB, base mise tools 38 MB, other 5 MB.
- Smoke test passes: `mise --version`, `bat/fzf/lsd/starship/yq/zoxide --version`, project-level `mise install python` resolves `3.13.11` correctly, `strip` available.

### Remaining / deferred

1. **devcontainer.json hardcoded version paths** (python/dotnet/kubectl/powershell) — still stale. Can be replaced with `installs/<tool>/latest/…` paths once I verify mise creates those symlinks in this image. Low priority; only matters when a consumer rebuilds the per-project devcontainer with a new patch.
2. **README "Apple Silicon" section** — not written yet. Should note: container runs as `linux/arm64` via Docker Desktop's Linux VM; per-project `.mise.toml` must pin an explicit Python patch (not `"3.13"`) to avoid the freethreaded-stripped trap; `ms-dotnettools.csdevkit` is amd64-only so .NET tooling degrades to Roslyn-only on Apple Silicon.
3. **End-to-end devcontainer build on the M5** — base image is good; the per-project `.devcontainer/Dockerfile` extends the base and runs `mise install` against the full project `.mise.toml` (dotnet, powershell, node, opentofu, etc.). Haven't cross-verified every tool on arm64 yet. Next iteration should spin up the devcontainer and exercise each.
4. **container-test.yml GitHub Actions run** — the matrix/platforms change is correct but hasn't been executed in CI yet (no push). Will surface any CI-only issues (QEMU emulation corner cases).

### Out of scope

- Native macOS support without Docker.
- Replacing custom asdf plugins (they were removed from `.mise.toml` by the user).
