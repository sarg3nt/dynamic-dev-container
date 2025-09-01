# syntax=docker/dockerfile:1

# See: https://hub.docker.com/r/docker/dockerfile.  Syntax directive must be first line
# cspell:ignore

# VER=0.0.2 && IMAGE="ghcr.io/sarg3nt/dynamic-dev-container" && docker build . -t ${IMAGE}:${VER} --build-arg "VER=${VER}" && docker push ${IMAGE}:${VER}

# Mise application list and versions are located in
# home/vscode/.config/mise/config.toml
# Add custom Mise tools and version to your projects root as .mise.toml  See: https://mise.jdx.dev/configuration.html

# Use mise from package manager or smaller binary
# https://github.com/jdx/mise/pkgs/container/mise/versions
FROM jdxcode/mise:2025.8.21@sha256:0a1e312e8abf09c79cf7fbb61469c76f8abc349216cdb8216e00b42ebf56ed0c AS mise

# Extract only the mise binary and strip it
RUN strip /usr/local/bin/mise || true

# https://hub.docker.com/r/rockylinux/rockylinux/tags
FROM rockylinux/rockylinux:10-ubi@sha256:02564b26a5d147fcdbd1058abd9b358008f5608b382dcb288cfc718d627256cb AS final
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
RUN --mount=type=bind,source=scripts/10_install_system_packages.sh,target=/10.sh,ro bash -c "/10.sh"

# Set current user to the vscode user, run all future commands as this user.
USER vscode

# Copy the mise binary from the mise container
COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise
COPY --chown=vscode:vscode home/vscode/.config/mise /home/vscode/.config/mise

# Install mise tools and configure environment in one layer
RUN --mount=type=bind,source=scripts/20_install_mise_tools.sh,target=/20.sh,ro bash -c "/20.sh" 
RUN --mount=type=bind,source=scripts/30_install_other_apps.sh,target=/30.sh,ro bash -c "/30.sh"
RUN --mount=type=bind,source=scripts/40_setup_ssh_known_hosts.sh,target=/40.sh,ro bash -c "/40.sh"

COPY --chown=vscode:vscode home /home/
COPY usr /usr 