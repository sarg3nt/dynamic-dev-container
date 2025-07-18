# Dynamic Dev Container with Pre-installed Mise Tools
# This Dockerfile extends the base dynamic-dev-container image and pre-installs
# all tools defined in .mise.toml during the build process and any krew plugins defined.
# cspell:ignore krew

FROM ghcr.io/sarg3nt/dynamic-dev-container:0.0.1

# Switch to vscode user for tool installation
USER vscode

# Install mise tools - requires .mise.toml in the working directory
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && ls -alh && .devcontainer/10_install_mise_tools.sh"

# Install krew plugins - requires krew to be installed from mise
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && .devcontainer/20_install_krew_plugins.sh"

# Install Python packages - requires Python and pip from mise
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && .devcontainer/30_install_python_packages.sh"
