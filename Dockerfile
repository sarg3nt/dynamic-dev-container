# syntax=docker/dockerfile:1

# See: https://hub.docker.com/r/docker/dockerfile.  Syntax directive must be first line
# cspell:ignore

# VER=1.0.0-dev1 && IMAGE="ghcr.io/sarg3nt/dynamic-dev-container" && docker build . -t ${IMAGE}:${VER} --build-arg "VER=${VER}"

# Mise application list and versions are located in
# home/vscode/.config/mise/config.toml
# Add custom Mise tools and version to your projects root as .mise.toml  See: https://mise.jdx.dev/configuration.html

# https://hub.docker.com/r/jdxcode/mise/tags
# This is latest.
FROM jdxcode/mise:v2025.7.10@sha256:647d0f9b3a6d2b5680ef07e3562e8c8dc83cacfd6952e0038190228314105278 AS mise

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
RUN --mount=type=bind,source=scripts/10_install_system_packages.sh,target=/10.sh,ro bash -c "/10.sh"

# Set current user to the vscode user, run all future commands as this user.
USER vscode

# Copy the mise binary from the mise container
COPY --from=mise /usr/local/bin/mise /usr/local/bin/mise
COPY --chown=vscode:vscode home/vscode/.config/mise /home/vscode/.config/mise

RUN --mount=type=bind,source=scripts/20_install_mise_tools.sh,target=/20.sh,ro bash -c "/20.sh"
RUN --mount=type=bind,source=scripts/30_install_other_apps.sh,target=/30.sh,ro bash -c "/30.sh"
RUN --mount=type=bind,source=scripts/40_setup_ssh_known_hosts.sh,target=/40.sh,ro bash -c "/40.sh"

COPY --chown=vscode:vscode home /home/
COPY usr /usr 

# VS Code by default overrides ENTRYPOINT and CMD with default values when executing `docker run`.
# Setting the ENTRYPOINT to docker_init.sh will configure non-root access to
# the Docker socket if "overrideCommand": false is set in devcontainer.json.
# The script will also execute CMD if you need to alter startup behaviors.
ENTRYPOINT [ "/usr/local/bin/docker_init.sh" ]
CMD [ "sleep", "infinity" ]

