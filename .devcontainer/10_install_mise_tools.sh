#!/bin/bash
#
# Script to build the dynamic container with the mise tools defined in the root .mise.toml file.
#
# cSpell:ignore krew mise 

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
source ".devcontainer/log.sh"

# Set up mise environment for all functions
setup_mise_env() {
  eval "$(/usr/local/bin/mise activate bash)"
  export PATH="$HOME/.local/share/mise/shims:$PATH"
}

#######################################
# Install tools with mise.
# Arguments:
#   None
#######################################
install_mise_tools() {
  log_info "Starting mise tools installation..."
  
  log_info "Current directory:"
  pwd

  log_info "Current directory contents:"
  ls -alh

  # Trust the mise configuration in the current directory
  log_info "Trusting mise configuration..."
  mise trust .mise.toml
  
  log_info "Installing mise tools from .mise.toml..."
  mise install

  # Activate mise environment and set up .NET environment variables
  log_info "Activating mise environment..."
  setup_mise_env

  # Set up .NET environment variables
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
  fi

  log_success "Mise tools installation completed!"
}

main() {
  # Debug: Show what files are available
  log_info "Checking available files..."
  log_info "Files in current directory (.devcontainer):"
  for file in ./*.{toml,txt,plugins} ./.*{toml,txt,plugins}; do
    [ -e "$file" ] && log_info "  $(basename "$file")"
  done
  
  install_mise_tools
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
