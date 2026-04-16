# syntax=docker/dockerfile:1

# See: https://hub.docker.com/r/docker/dockerfile.  Syntax directive must be first line
# cspell:ignore

# Multi-platform build support: linux/amd64, linux/arm64 (Mac ARM)
# VER=0.0.2 && IMAGE="ghcr.io/sarg3nt/dynamic-dev-container" && docker build . -t ${IMAGE}:${VER} --build-arg "VER=${VER}" && docker push ${IMAGE}:${VER}
# For multi-platform: docker buildx build --platform linux/amd64,linux/arm64 -t ${IMAGE}:${VER} --build-arg "VER=${VER}" --push .

# Mise application list and versions are located in
# home/vscode/.config/mise/config.toml
# Add custom Mise tools and version to your projects root as .mise.toml  See: https://mise.jdx.dev/configuration.html

# Base image digest is pinned for supply-chain integrity. The default is the
# OCI index digest (multi-arch manifest list) so `docker buildx` picks the right
# arch automatically. The Makefile overrides this with a single-arch manifest
# digest for native `make build` to tighten pinning further.
# https://hub.docker.com/r/rockylinux/rockylinux/tags
ARG BASE_IMAGE=rockylinux/rockylinux:10-ubi@sha256:02564b26a5d147fcdbd1058abd9b358008f5608b382dcb288cfc718d627256cb

FROM ${BASE_IMAGE} AS final
ARG GITHUB_TOKEN
# Both names are exported so mise (looks for GITHUB_TOKEN) and any legacy
# scripts/tools that check GITHUB_API_TOKEN both find the token during build.
ENV GITHUB_TOKEN=$GITHUB_TOKEN
ENV GITHUB_API_TOKEN=$GITHUB_TOKEN
LABEL org.opencontainers.image.source=https://github.com/sarg3nt/dynamic-dev-container

ARG VER=""
ENV DEV_CONTAINER_VERSION=$VER
ENV TZ='America/Los_Angeles'

# What user will be created in the dev container and will we run under.
# Recommend not changing this.
ENV USERNAME="vscode"

# Copy script libraries for use by internal scripts
COPY usr/bin/lib /usr/bin/lib

# Install packages using the dnf package manager
RUN --mount=type=bind,source=scripts/10_install_system_packages.sh,target=/10.sh,ro bash -c "/10.sh"

# Install mise. We download the glibc build of the static binary directly from
# the official GitHub release and verify it against a pinned SHA256 for the
# host architecture. The glibc build (not musl) is required so that mise
# auto-selects the python-build-standalone `linux-gnu` tarballs for
# MISE_PYTHON_COMPILE=false — the musl-freethreaded tarballs python-build-
# standalone ships are broken upstream (missing `lib` directory). libbz2.so.1.0
# is a runtime dep of the glibc mise binary; bzip2-libs is installed via dnf
# in scripts/10_install_system_packages.sh.
# SHA256s come from https://github.com/jdx/mise/releases/download/v${MISE_VERSION}/SHASUMS256.txt
ARG MISE_VERSION=2025.12.13
ARG MISE_SHA256_AMD64=2134c55725d08547cddc921f84ddac05c9de1700115c32817563435072cae5ed
ARG MISE_SHA256_ARM64=e4a4b6990007d1918da8181093b79b50b01a5f056bdd1567960aadfdf3c86752
ARG TARGETARCH
# Strip the mise binary before installing it (~63MB -> ~15MB). `strip` comes
# from binutils, which is installed persistently by scripts/10_install_system_packages.sh.
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) MISE_ARCH=x64;   MISE_SHA256="$MISE_SHA256_AMD64" ;; \
      arm64) MISE_ARCH=arm64; MISE_SHA256="$MISE_SHA256_ARM64" ;; \
      *) echo "unsupported TARGETARCH: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/mise \
      "https://github.com/jdx/mise/releases/download/v${MISE_VERSION}/mise-v${MISE_VERSION}-linux-${MISE_ARCH}"; \
    echo "${MISE_SHA256}  /tmp/mise" | sha256sum -c -; \
    strip /tmp/mise; \
    install -m 0755 /tmp/mise /usr/local/bin/mise; \
    rm /tmp/mise

# Set current user to the vscode user, run all future commands as this user.
USER vscode

COPY --chown=vscode:vscode home/vscode/.config/mise /home/vscode/.config/mise

# Install mise tools and configure environment in one layer
RUN --mount=type=bind,source=scripts/20_install_mise_tools.sh,target=/20.sh,ro bash -c "/20.sh" 
RUN --mount=type=bind,source=scripts/30_install_other_apps.sh,target=/30.sh,ro bash -c "/30.sh"
RUN --mount=type=bind,source=scripts/40_setup_ssh_known_hosts.sh,target=/40.sh,ro bash -c "/40.sh"

COPY --chown=vscode:vscode home /home/
COPY usr /usr 