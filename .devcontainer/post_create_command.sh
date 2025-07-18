#!/bin/bash

# cSpell:ignore

set -euo pipefail
IFS=$'\n\t'

source "$(dirname "$0")/log.sh"

main() {
  echo ""
  log "EXECUTING POST CREATE COMMAND..." "gray" "INFO"

  #install_python_dependencies
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
