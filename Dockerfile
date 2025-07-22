# syntax=docker/dockerfile:1

# See: https://hub.docker.com/r/docker/dockerfile.  Syntax directive must be first line
# cspell:ignore

# VER=0.0.2 && IMAGE="ghcr.io/sarg3nt/dynamic-dev-container" && docker build . -t ${IMAGE}:${VER} --build-arg "VER=${VER}" && docker push ${IMAGE}:${VER}

# Mise application list and versions are located in
# home/vscode/.config/mise/config.toml
# Add custom Mise tools and version to your projects root as .mise.toml  See: https://mise.jdx.dev/configuration.html

# Use mise from package manager or smaller binary
FROM jdxcode/mise:v2025.7.10@sha256:647d0f9b3a6d2b5680ef07e3562e8c8dc83cacfd6952e0038190228314105278 AS mise

# Extract only the mise binary and strip it
RUN strip /usr/local/bin/mise || true

# https://hub.docker.com/r/rockylinux/rockylinux/tags
FROM rockylinux/rockylinux:10-ubi@sha256:eca03145dd5e0b2a281eef164d391e4758b4a5962d29b688d15a72cef712fbb4 AS final
ARG GITHUB_TOKEN
ENV GITHUB_API_TOKEN=$GITHUB_TOKEN
LABEL org.opencontainers.image.source=https://github.com/sarg3nt/dynamic-dev-container

ARG VER=""
ENV DEV_CONTAINER_VERSION=$VER
ENV TZ='America/Los_Angeles'

# What user will be created in the dev container and will we run under.
# Reccomend not changing this.
ENV USERNAME="vscode"

# Copy script libraries for use by internal scripts
COPY usr/bin/lib /usr/bin/lib

# Install packages using the dnf package manager
RUN --mount=type=bind,source=scripts/10_install_system_packages.sh,target=/10.sh,ro \
  --mount=type=cache,target=/var/cache/dnf \
  bash -c "/10.sh"

# Set current user to the vscode user, run all future commands as this user.
USER vscode

# Copy the mise binary from the mise container
COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise
COPY --chown=vscode:vscode home/vscode/.config/mise /home/vscode/.config/mise

# Install mise tools and configure environment in one layer
RUN --mount=type=bind,source=scripts/20_install_mise_tools.sh,target=/20.sh,ro \
  --mount=type=bind,source=scripts/30_install_other_apps.sh,target=/30.sh,ro \
  --mount=type=bind,source=scripts/40_setup_ssh_known_hosts.sh,target=/40.sh,ro \
  --mount=type=cache,target=/home/vscode/.cache/mise,uid=1000,gid=1000 \
  bash -c "/20.sh && /30.sh && /40.sh"

COPY --chown=vscode:vscode home /home/
COPY usr /usr 