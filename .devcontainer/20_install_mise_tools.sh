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

# Source the shared mise parser library
# shellcheck disable=SC1091
source ".devcontainer/mise_parser.sh"

# Set up mise environment for all functions
setup_mise_env() {
  eval "$(/usr/local/bin/mise activate bash)"
}

# Parsing functions moved to shared library: mise_parser.sh

#######################################
# Install tools with mise one at a time.
# Arguments:
#   None
#######################################
install_mise_tools() {
  log_info "Starting mise tools installation..."
  
  # Check if .mise.toml exists
  if [[ ! -f ".mise.toml" ]]; then
    log_warning "No .mise.toml file found, skipping mise tools installation"
    return 0
  fi
  
  # Declare arrays for tools and aliases
  local tools_array=()
  declare -A aliases_array
  
  # Trust the mise configuration in the current directory
  log_info "Trusting mise configuration..."
  mise trust .mise.toml

  # Parse tools and aliases from .mise.toml (exclude JavaScript tools)
  if ! parse_mise_tools "tools_array" "exclude_js"; then
    log_error "Failed to parse tools from .mise.toml"
    return 1
  fi
  parse_mise_aliases "aliases_array"
  
  # Install tools using the shared function
  install_tools_with_mise "tools_array" "aliases_array" "-g"
  
  log_success "Mise tools installation completed!"
 
  log_info "BASH_SUBSHELL: $BASH_SUBSHELL"
  if [[ "$BASH_SUBSHELL" -gt 0 ]]; then
    log_info "Detected subshell. Exiting subshell."
    exit
  fi

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
  export NODE_OPTIONS=""
}

main() {
  install_mise_tools

}

if ! (return 0 2>/dev/null); then
  main "$@"
fi
