# Dynamic Dev Container with Pre-installed Mise Tools
# This Dockerfile extends the base dynamic-dev-container image and pre-installs
# all tools defined in .mise.toml during the build process and any krew plugins defined.
# cspell:ignore krew

FROM ghcr.io/sarg3nt/dynamic-dev-container:latest

# Switch to vscode user for tool installation
USER vscode

# Install user system packages
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && .devcontainer/scripts/10_install_packages.sh"

# Install mise tools - requires .mise.toml in the working directory
RUN --mount=type=bind,source=.,target=/tmp/src,rw --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,rw bash -c "cd /tmp/src && .devcontainer/scripts/20_install_mise_tools.sh"

# Install krew plugins - requires krew to be installed from mise
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && .devcontainer/scripts/30_install_krew_plugins.sh"

# Install Python packages - requires Python and pip from mise
RUN --mount=type=bind,source=.,target=/tmp/src,ro --mount=type=bind,source=.devcontainer,target=/tmp/src/.devcontainer,ro bash -c "cd /tmp/src && .devcontainer/scripts/40_install_python_packages.sh"

# VS Code by default overrides ENTRYPOINT and CMD with default values when executing `docker run`.
# Setting the ENTRYPOINT to docker_init.sh will configure non-root access to
# the Docker socket if "overrideCommand": false is set in devcontainer.json.
# The script will also execute CMD if you need to alter startup behaviors.
ENTRYPOINT [ "/usr/local/bin/docker_init.sh" ]
CMD [ "sleep", "infinity" ]