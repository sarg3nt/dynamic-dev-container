#!/bin/bash

# cSpell:ignore

set -euo pipefail
IFS=$'\n\t'

source "$(dirname "$0")/utils/log.sh"

main() {
  echo ""
  log "EXECUTING POST CREATE COMMAND..." "gray" "INFO"

  install_mise_applications
  install_python_dependencies
}

install_mise_applications() {
  if ! command -v mise &>/dev/null; then
    return
  fi

  log_info "Installing mise applications."
  echo ""
  mise trust -y
  eval "$(/usr/local/bin/mise activate bash)"
  # Change to the workspace directory so mise can find .mise.toml
  cd "${WORKSPACE_PATH}"
  mise trust -y
  # Check if .mise.toml exists
  if [[ -f ".mise.toml" ]]; then
    log_info "Found .mise.toml file:"
    echo ""

    # Trust the configuration and install tools
    if mise install -y; then
      echo ""
      # Re-activate mise environment after installing new tools
      eval "$(/usr/local/bin/mise activate bash)"
      log_success "Mise applications installed successfully."
    else
      echo ""
      log_error "Failed to install mise applications."
      exit 1
    fi
  else
    log_warning "No .mise.toml file found in ${WORKSPACE_PATH}. Skipping mise applications installation."
  fi
}

install_python_dependencies() {
  log_success "Workspace path: ${WORKSPACE_PATH}"
  echo ""

  # Debug: Check if pip is available
  if command -v pip &>/dev/null; then
    log_success "pip is available at: $(which pip)"
  else
    log_error "pip is not available in PATH"
    log_info "Current PATH: $PATH"
  fi

  if [[ -f "${WORKSPACE_PATH}/requirements.txt" ]]; then
    log_info "Installing Python dependencies from requirements.txt."
    echo ""
    if pip install --disable-pip-version-check -r "${WORKSPACE_PATH}/requirements.txt"; then
      echo ""
      log_success "Python dependencies installed successfully."
    else
      echo ""
      log_error "Failed to install Python dependencies."
      exit 2
    fi
  else
    log_warning "No requirements.txt file found in the workspace. Skipping Python dependencies installation."
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
