#!/bin/bash
#
# Script to to add Mise tools to the dynamic dev container.
#
# cSpell:ignore krew mise 

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC1091
source ".devcontainer/log.sh"

# Set up mise environment for all functions
setup_mise_env() {
  eval "$(/usr/local/bin/mise activate bash)"
}

#######################################
# Install tools with mise.
# Arguments:
#   None
#######################################
install_mise_tools() {
  log_info "Starting mise tools installation..."
  
  # Trust the mise configuration in the current directory
  log_info "Trusting mise configuration..."
  mise trust .mise.toml

  log_info "Installing mise tools from .mise.toml..."
  mise install -y
  log_success "Mise tools installed successfully!"

  # Activate mise environment and set up .NET environment variables
  log_info "Activating mise environment..."
  setup_mise_env

  # # Set up .NET environment variables
  if [ -n "${DOTNET_ROOT:-}" ] && [ -d "${DOTNET_ROOT}" ]; then 
    log_info "Setting up .NET environment variables..."
    # Find and set MSBuildSDKsPath
    SDKS_PATH=$(find "${DOTNET_ROOT}" -name "Sdks" -type d 2>/dev/null | head -1)
    if [ -n "${SDKS_PATH}" ] && [ -d "${SDKS_PATH}" ]; then
      log_info "Setting MSBuildSDKsPath to: ${SDKS_PATH}"
      echo "export MSBuildSDKsPath=\"${SDKS_PATH}\"" >> /home/vscode/.zshrc;
    fi

    # Set telemetry opt-out
    log_info "Disabling .NET telemetry..."
    echo "export DOTNET_CLI_TELEMETRY_OPTOUT=1" >> /home/vscode/.zshrc; 
    log_success " .NET environment variables set successfully."
  fi

  if command -v go >/dev/null 2>&1; then
    log_info "Adding Go Tools..."
    go install github.com/go-delve/delve/cmd/dlv@latest
    go install golang.org/x/tools/gopls@latest
    go install mvdan.cc/gofumpt@latest
    log_success "Go tools installed successfully."
  fi

  unset NODE_OPTIONS

}

main() {
  install_mise_tools
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
