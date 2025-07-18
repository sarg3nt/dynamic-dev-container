#!/bin/bash
#
# Script to install Python packages from requirements.txt.
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
# Install any Python packages..
# Arguments:
#   None
#######################################
install_python_packages() {
  log_info "Starting Python packages installation..."

  # Ensure mise is activated and Python/pip are available
  setup_mise_env
  
  # Debug: Check if pip is available
  if command -v pip &>/dev/null; then
    log_info "pip is available at: $(which pip)"
    log_info "pip version: $(pip --version)"
  else
    log_error "pip could not be found"
    log_info "Available Python-related commands:"
    for shim in "$HOME/.local/share/mise/shims/"*python*; do
      [ -e "$shim" ] && log_info "  $(basename "$shim")"
    done
    exit 1
  fi

  if [[ -f "requirements.txt" ]]; then
    log_info "Found requirements.txt in root, installing Python packages..."
    log_info "Contents of requirements.txt:"
    cat "requirements.txt"
    if pip install --disable-pip-version-check -r "requirements.txt"; then
      log_success "Python packages installed successfully."
    else
      log_error "Failed to install Python dependencies."
      exit 2
    fi
  else
    log_info "No requirements.txt found in root directory, skipping Python dependencies installation."
  fi
}

main() {
  install_python_packages
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
