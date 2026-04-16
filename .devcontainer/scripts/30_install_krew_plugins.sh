#!/bin/bash
#
# Script to install kubectl plugins using krew.
#
# This script manages the installation of kubectl plugins via the krew plugin manager.
# It activates the mise environment, checks for krew availability, and reads plugin
# configurations from a .krew_plugins file.
#
# cSpell:ignore krew mise 

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC1091
source "$(dirname "$0")/log.sh"

# Constants
readonly KREW_CONFIG_FILE=".krew_plugins"
readonly ZSHRC_FILE="$HOME/.zshrc"
readonly MAX_INSTALL_ATTEMPTS=3
readonly RETRY_DELAY=5

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
# Parse krew plugins from configuration file
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Outputs:
#   Plugin names, one per line, to stdout
# Globals:
#   KREW_CONFIG_FILE - Path to krew plugins configuration file
#######################################
parse_krew_plugins() {
  local plugins=()
  
  if [[ ! -f "$KREW_CONFIG_FILE" ]]; then
    log_info "No $KREW_CONFIG_FILE file found, skipping krew plugins installation" >&2
    return 0
  fi

  if [[ ! -r "$KREW_CONFIG_FILE" ]]; then
    log_error "Cannot read $KREW_CONFIG_FILE file" >&2
    return 1
  fi

  log_info "Found krew plugins configuration file at $KREW_CONFIG_FILE" >&2

  # Read plugin names from file, ignoring comments and empty lines
  while IFS= read -r plugin || [[ -n "$plugin" ]]; do
    # Remove leading/trailing whitespace and skip empty lines and comments
    plugin=$(echo "$plugin" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$plugin" || "$plugin" =~ ^# ]] && continue
    
    # Validate plugin name (basic check)
    if [[ ! "$plugin" =~ ^[a-zA-Z0-9_-]+$ ]]; then
      log_warning "Skipping invalid plugin name: $plugin" >&2
      continue
    fi
    
    plugins+=("$plugin")
  done < "$KREW_CONFIG_FILE"
  
  if [[ ${#plugins[@]} -eq 0 ]]; then
    log_info "No valid plugins found in $KREW_CONFIG_FILE" >&2
    return 0
  fi
  
  log_info "Found ${#plugins[@]} plugins to install" >&2
  
  # Output plugins one per line for main() to read
  printf '%s\n' "${plugins[@]}"
  return 0
}

#######################################
# Install kubectl plugins using krew with retry logic
# Arguments:
#   Plugin names to install
# Returns:
#   0 on success, 1 on failure
# Globals:
#   MAX_INSTALL_ATTEMPTS, RETRY_DELAY, ZSHRC_FILE - Configuration
#######################################
install_kubectl_plugins() {
  local plugins=("$@")
  
  log_info "Starting kubectl plugins installation..."
  
  # Ensure mise is activated
  if ! setup_mise_env; then
    return 1
  fi
  
  # Check if krew is available
  if ! command -v krew >/dev/null 2>&1; then
    log_info "Krew not found, checking if kubectl is available..."
    if command -v kubectl >/dev/null 2>&1; then
      log_info "kubectl found but krew not available, skipping krew plugins installation."
    else
      log_info "kubectl not found, skipping krew plugins installation."
    fi
    return 0
  fi
  
  log_info "Krew found at: $(command -v krew)"
  
  # Add krew to PATH in zshrc if not already present
  local export_statement="export PATH=\"\${KREW_ROOT:-\$HOME/.krew}/bin:\$PATH\""
  if ! grep -Fq "$export_statement" "$ZSHRC_FILE" 2>/dev/null; then
    log_info "Adding krew to PATH in $ZSHRC_FILE..."
    echo "$export_statement" >> "$ZSHRC_FILE"
    log_success "Added krew to PATH successfully"
  else
    log_info "Krew already in PATH"
  fi
  
  if [[ ${#plugins[@]} -eq 0 ]]; then
    log_info "No plugins to install"
    return 0
  fi

  log_info "Installing ${#plugins[@]} kubectl plugins: ${plugins[*]}"

  # Skip the batch path entirely. `krew install` with multiple plugins exits
  # non-zero if any single plugin fails, even when every other plugin in the
  # batch installed successfully. On arm64 some plugins (e.g. access-matrix)
  # don't publish a binary for this platform, so the batch always "fails" and
  # we fall back to the individual loop anyway. Going straight to individual
  # installs avoids three minutes of pointless retries.
  local failed_plugins=()
  local succeeded_plugins=()
  local unavailable_plugins=()

  for plugin in "${plugins[@]}"; do
    log_info "Installing plugin: $plugin"

    local plugin_attempt=1
    local plugin_done=false
    local last_output=""

    while [[ $plugin_attempt -le $MAX_INSTALL_ATTEMPTS && $plugin_done == false ]]; do
      if last_output=$(krew install "$plugin" 2>&1); then
        printf '%s\n' "$last_output"
        log_success "Successfully installed plugin: $plugin"
        succeeded_plugins+=("$plugin")
        plugin_done=true
        break
      fi

      printf '%s\n' "$last_output"

      # Krew reports platform-unavailable plugins as:
      #   plugin "<name>" does not offer installation for this platform
      # That is a permanent upstream fact, not a transient failure, so record
      # it as unavailable and stop retrying.
      if grep -qF "does not offer installation for this platform" <<< "$last_output"; then
        log_warning "Plugin $plugin is not available for this platform ($(uname -m)); skipping."
        unavailable_plugins+=("$plugin")
        plugin_done=true
        break
      fi

      if [[ $plugin_attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
        log_warning "Failed to install $plugin (attempt $plugin_attempt), retrying..."
        sleep "$RETRY_DELAY"
      else
        log_error "Failed to install $plugin after $MAX_INSTALL_ATTEMPTS attempts"
        failed_plugins+=("$plugin")
      fi

      ((plugin_attempt++))
    done
  done

  # Report results
  if [[ ${#succeeded_plugins[@]} -gt 0 ]]; then
    log_success "Successfully installed ${#succeeded_plugins[@]} plugins: ${succeeded_plugins[*]}"
  fi

  if [[ ${#unavailable_plugins[@]} -gt 0 ]]; then
    log_warning "Skipped ${#unavailable_plugins[@]} plugins not available on this platform: ${unavailable_plugins[*]}"
  fi

  if [[ ${#failed_plugins[@]} -gt 0 ]]; then
    log_error "Failed to install ${#failed_plugins[@]} plugins: ${failed_plugins[*]}"
    return 1
  fi

  return 0
}

#######################################
# Main function to orchestrate the krew plugins installation process
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
  local exit_code=0
  
  log_info "Starting krew plugins installation process..."
  
  # Parse plugins from configuration file
  local plugins=()
  while IFS= read -r plugin; do
    [[ -n "$plugin" ]] && plugins+=("$plugin")
  done < <(parse_krew_plugins)
  
  if [[ ${#plugins[@]} -gt 0 ]]; then
    # Install plugins if any found
    if ! install_kubectl_plugins "${plugins[@]}"; then
      log_error "Krew plugins installation process failed"
      exit_code=1
    fi
  else
    log_info "No plugins to install"
  fi

  if [[ $exit_code -eq 0 ]]; then
    log_success "Krew plugins installation completed successfully!"
  else
    log_warning "Krew plugins installation completed with some failures. Check logs above for details."
  fi
  
  return $exit_code
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
