#!/bin/bash
#
# Script to build the dynamic container with the mise tools defined in the root .mise.toml file.
#
# cSpell:ignore krew mise 

set -euo pipefail
IFS=$'\n\t'

#######################################
# Install tools with mise.
# Arguments:
#   None
#######################################
install_mise_tools() {
  cd /tmp

  # Trust the mise configuration
  mise trust -y
  
  # Install all tools defined in .mise.toml
  mise install -y

  # Activate mise environment and set up .NET environment variables
  eval "$(/usr/local/bin/mise activate bash)"

  # Set up .NET environment variables
  if [ -n "${DOTNET_ROOT:-}" ] && [ -d "${DOTNET_ROOT}" ]; then 
    # Find and set MSBuildSDKsPath
    SDKS_PATH=$(find "${DOTNET_ROOT}" -name "Sdks" -type d 2>/dev/null | head -1)
    if [ -n "${SDKS_PATH}" ] && [ -d "${SDKS_PATH}" ]; then
      echo "export MSBuildSDKsPath=\"${SDKS_PATH}\"" >> /home/vscode/.zshrc;
    fi

    # Set telemetry opt-out
    echo "export DOTNET_CLI_TELEMETRY_OPTOUT=1" >> /home/vscode/.zshrc; 
  fi

  sudo rm -rf /tmp/* || true

  cd -
}

#######################################
# Install any kubectl plugins using krew.
# Arguments:
#   None
#######################################
install_kubectl_plugins() {
  if command -v krew >/dev/null 2>&1; then
    export_statement="export PATH=\"\${KREW_ROOT:-\$HOME/.krew}/bin:\$PATH\""
    echo "$export_statement" >>~/.zshrc
    
    # Read plugins from configuration file
    local krew_config="/tmp/.krew_plugins"
    if [[ -f "$krew_config" ]]; then
      # Read plugin names from file, ignoring comments and empty lines, into an array
      local plugins_array=()
      while IFS= read -r plugin; do
        [[ -n "$plugin" ]] && plugins_array+=("$plugin")
      done < <(grep -v '^#' "$krew_config" | grep -v '^[[:space:]]*$')
      
      if [[ ${#plugins_array[@]} -gt 0 ]]; then
        krew install "${plugins_array[@]}"
      fi
    fi

    sudo rm -rf /tmp/* || true
  fi
}

main() {
  install_mise_tools
  install_kubectl_plugins
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
