# Dynamic Dev Container with Pre-installed Mise Tools
# This Dockerfile extends the base dynamic-dev-container image and pre-installs
# all tools defined in .mise.toml during the build process and any krew plugins defined.
# cspell:ignore krew

FROM ghcr.io/sarg3nt/dynamic-dev-container:0.0.1

# Switch to vscode user for tool installation
USER vscode

# Copy mise configuration from workspace root
COPY .mise.toml /tmp/.mise.toml
COPY .krew_plugins /tmp/.krew_plugins

# Run the devcontainer build script to install mise tools and krew plugins.
RUN --mount=type=bind,source=scripts/devcontainer_dockerfile_build.sh,target=/build.sh,ro bash -c "/build.sh"

# Activate mise environment for all future shells
RUN echo 'eval "$(/usr/local/bin/mise activate zsh)"' >> /home/vscode/.zshrc
