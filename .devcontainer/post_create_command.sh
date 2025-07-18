#!/bin/bash

# cSpell:ignore

set -euo pipefail
IFS=$'\n\t'

source "$(dirname "$0")/utils/log.sh"

main() {
  echo ""
  log "EXECUTING POST CREATE COMMAND..." "gray" "INFO"

  #setup_dotnet_environment
  install_python_dependencies
}

setup_dotnet_environment() {
  log_info "Setting up .NET environment variables."
  echo ""
  
  # Re-activate mise environment to ensure DOTNET_ROOT is available
  eval "$(/usr/local/bin/mise activate bash 2>/dev/null)" || true
  
  if [[ -n "${DOTNET_ROOT:-}" ]] && [[ -d "${DOTNET_ROOT}" ]]; then
    log_success "DOTNET_ROOT found at: ${DOTNET_ROOT}"
    
    # Check if MSBuildSDKsPath is already set (from pre-installed image)
    if [[ -n "${MSBuildSDKsPath:-}" ]] && [[ -d "${MSBuildSDKsPath}" ]]; then
      log_success "MSBuildSDKsPath already configured: ${MSBuildSDKsPath}"
    else
      # Find and set MSBuildSDKsPath
      # Look for the Sdks directory, following symlinks
      SDKS_PATH=$(find -L "${DOTNET_ROOT}" -name "Sdks" -type d 2>/dev/null | head -1)
      
      # Alternative approach: construct the path directly since we know the structure
      if [[ -z "${SDKS_PATH}" ]]; then
        # Try to find any SDK version directory
        SDK_VERSION_DIR=$(find -L "${DOTNET_ROOT}/sdk" -maxdepth 1 -type d -name "[0-9]*" 2>/dev/null | head -1)
        if [[ -n "${SDK_VERSION_DIR}" ]] && [[ -d "${SDK_VERSION_DIR}/Sdks" ]]; then
          SDKS_PATH="${SDK_VERSION_DIR}/Sdks"
        fi
      fi
      
      if [[ -n "${SDKS_PATH}" ]] && [[ -d "${SDKS_PATH}" ]]; then
        export MSBuildSDKsPath="${SDKS_PATH}"
        log_success "Set MSBuildSDKsPath to: ${MSBuildSDKsPath}"
        
        # Add to shell profile for persistence
        echo "export MSBuildSDKsPath=\"${SDKS_PATH}\"" >> "${HOME}/.bashrc"
        echo "export MSBuildSDKsPath=\"${SDKS_PATH}\"" >> "${HOME}/.zshrc" 2>/dev/null || true
      else
        log_warning "Could not find Sdks directory in ${DOTNET_ROOT}"
        log_info "Checked paths:"
        log_info "  - ${DOTNET_ROOT}/sdk/*/Sdks"
        log_info "  - Available directories in ${DOTNET_ROOT}:"
        ls -la "${DOTNET_ROOT}" 2>/dev/null || log_info "    (could not list directory)"
      fi
    fi
    
    # Check if telemetry is already disabled
    if [[ "${DOTNET_CLI_TELEMETRY_OPTOUT:-}" == "1" ]]; then
      log_success ".NET telemetry already disabled"
    else
      # Set DOTNET_CLI_TELEMETRY_OPTOUT to disable telemetry
      export DOTNET_CLI_TELEMETRY_OPTOUT=1
      log_success "Disabled .NET telemetry"
      
      # Add to shell profile for persistence
      echo "export DOTNET_CLI_TELEMETRY_OPTOUT=1" >> "${HOME}/.bashrc"
      echo "export DOTNET_CLI_TELEMETRY_OPTOUT=1" >> "${HOME}/.zshrc" 2>/dev/null || true
    fi
    
    echo ""
    log_success ".NET environment variables configured successfully."
  else
    log_warning "DOTNET_ROOT not found. .NET may not be installed via mise."
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
