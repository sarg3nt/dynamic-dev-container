#!/bin/bash
#
# Script to install kubectl plugins using krew.
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
# Install any kubectl plugins using krew.
# Arguments:
#   None
#######################################
install_kubectl_plugins() {
  log_info "Starting kubectl plugins installation..."
  
  # Ensure mise is activated and krew is available
  setup_mise_env
  
  if command -v krew >/dev/null 2>&1; then
    log_info "Krew found at: $(which krew)"
    log_info "Adding krew to PATH..."
    export_statement="export PATH=\"\${KREW_ROOT:-\$HOME/.krew}/bin:\$PATH\""
    echo "$export_statement" >>~/.zshrc
    
    log_info "Current directory:"
    pwd

    log_info "Current directory contents:"
    ls -alh

    # Read plugins from configuration file
    local krew_config=".krew_plugins"
    if [[ -f "$krew_config" ]]; then
      log_info "Found krew plugins configuration file..."
      # Read plugin names from file, ignoring comments and empty lines, into an array
      local plugins_array=()
      while IFS= read -r plugin; do
        [[ -n "$plugin" ]] && plugins_array+=("$plugin")
      done < <(grep -v '^#' "$krew_config" | grep -v '^[[:space:]]*$')
      
      if [[ ${#plugins_array[@]} -gt 0 ]]; then
        log_info "Installing ${#plugins_array[@]} kubectl plugins: ${plugins_array[*]}"
        krew install "${plugins_array[@]}"
        log_success "Kubectl plugins installation completed!"
      else
        log_info "No plugins found in configuration file."
      fi
    else
      log_info "No krew plugins configuration file found."
    fi
  else
    log_info "Krew not found, checking if kubectl is available..."
    if command -v kubectl >/dev/null 2>&1; then
      log_info "kubectl found but krew not available, skipping krew plugins installation."
    else
      log_info "kubectl not found, skipping krew plugins installation."
    fi
  fi
}

main() {
  install_kubectl_plugins
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
