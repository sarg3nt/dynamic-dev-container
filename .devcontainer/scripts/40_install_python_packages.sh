#!/bin/bash
#
# Script to install Python packages from requirements.txt.
#
# This script manages the installation of Python packages from a requirements.txt file.
# It activates the mise environment, validates Python/pip availability, and installs
# packages with proper error handling and logging.
#
# cSpell:ignore krew mise 

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC1091
source "$(dirname "$0")/log.sh"

# Constants
readonly REQUIREMENTS_FILE="requirements.txt"
readonly MAX_INSTALL_ATTEMPTS=3
readonly RETRY_DELAY=5
readonly PIP_TIMEOUT=300

#######################################
# Set up mise environment for all functions
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
setup_mise_env() {
  if ! eval "$(/usr/local/bin/mise activate bash)" 2>/dev/null; then
    log_error "Failed to activate mise environment"
    return 1
  fi
  return 0
}

#######################################
# Validate Python and pip availability
# Arguments:
#   None
# Returns:
#   0 if available, 1 otherwise
#######################################
validate_python_environment() {
  # Ensure mise is activated
  if ! setup_mise_env; then
    return 1
  fi
  
  # Check if pip is available
  if ! command -v pip &>/dev/null; then
    log_error "pip could not be found"
    log_info "Available Python-related commands:"
    if [[ -d "$HOME/.local/share/mise/shims/" ]]; then
      for shim in "$HOME/.local/share/mise/shims/"*python*; do
        [[ -e "$shim" ]] && log_info "  $(basename "$shim")"
      done
    fi
    return 1
  fi

  log_info "pip is available at: $(command -v pip)"
  log_info "pip version: $(pip --version 2>/dev/null || echo 'unknown')"
  
  return 0
}

#######################################
# Install Python packages from requirements file with retry logic
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   REQUIREMENTS_FILE, MAX_INSTALL_ATTEMPTS, RETRY_DELAY, PIP_TIMEOUT
#######################################
install_python_packages() {
  log_info "Starting Python packages installation..."

  # Validate Python environment
  if ! validate_python_environment; then
    return 1
  fi

  # Check if requirements file exists
  if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    log_info "No $REQUIREMENTS_FILE found in root directory, skipping Python dependencies installation."
    return 0
  fi

  if [[ ! -r "$REQUIREMENTS_FILE" ]]; then
    log_error "Cannot read $REQUIREMENTS_FILE file"
    return 1
  fi

  log_info "Found $REQUIREMENTS_FILE in root, installing Python packages..."
  log_info "Contents of $REQUIREMENTS_FILE:"
  cat "$REQUIREMENTS_FILE" | while IFS= read -r line; do
    [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]] && log_info "  $line"
  done

  # Install packages with retry logic
  local attempt=1
  local install_success=false
  
  while [[ $attempt -le $MAX_INSTALL_ATTEMPTS && $install_success == false ]]; do
    log_info "Installing Python packages (attempt $attempt/$MAX_INSTALL_ATTEMPTS)..."
    
    if timeout "$PIP_TIMEOUT" pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE" 2>&1; then
      log_success "Python packages installed successfully!"
      install_success=true
      return 0
    else
      if [[ $attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
        log_warning "Package installation failed on attempt $attempt, retrying in $RETRY_DELAY seconds..."
        sleep "$RETRY_DELAY"
      else
        log_error "Failed to install Python dependencies after $MAX_INSTALL_ATTEMPTS attempts"
        return 1
      fi
    fi
    
    ((attempt++))
  done
  
  return 1
}

#######################################
# Main function to orchestrate the Python packages installation process
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
  local exit_code=0
  
  log_info "Starting Python packages installation process..."
  
  # Install Python packages
  if ! install_python_packages; then
    log_error "Python packages installation failed"
    exit_code=1
  fi
  
  # Log subshell information for debugging
  log_info "BASH_SUBSHELL in 40_install_python_packages.sh: $BASH_SUBSHELL"
  
  if [[ $exit_code -eq 0 ]]; then
    log_success "Python packages installation completed successfully!"
  else
    log_warning "Python packages installation completed with failures. Check logs above for details."
  fi
  
  return $exit_code
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
