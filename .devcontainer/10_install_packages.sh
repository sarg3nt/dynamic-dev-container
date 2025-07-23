#!/bin/bash
#
# Dynamic package installer for dev container startup.
# Reads packages from /.packages file and installs them.
# This runs when the dev container starts, after the base system is built.
#

set -euo pipefail
IFS=$'\n\t'

# Parse packages from .packages file
parse_packages() {
  local packages_file=".packages"
  local packages=()
  
  if [[ ! -f "$packages_file" ]]; then
    log "No /.packages file found, skipping package installation" "yellow" >&2
    return 0
  fi
  
  log "Reading packages from $packages_file" "green" >&2
  
  # Read file line by line, skip comments and empty lines
  while IFS= read -r line; do
    # Remove leading/trailing whitespace and skip empty lines and comments
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    
    # Add package to array
    packages+=("$line")
  done < "$packages_file"
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log "No packages found in $packages_file" "yellow" >&2
    return 0
  fi
  
  log "Found ${#packages[@]} packages to install: ${packages[*]}" "green" >&2
  printf '%s\n' "${packages[@]}"
}

# Install packages efficiently
install_packages() {
  local packages=("$@")
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log "No packages to install" "yellow"
    return 0
  fi
  
  log "Installing ${#packages[@]} packages in batch: ${packages[*]}" "green"
  
  # Install all packages in one command for efficiency
  # Note: EPEL, CRB, and dnf-plugins-core already configured in base system
  if ! sudo dnf install -y "${packages[@]}"; then
    log "Package installation failed, trying individual installation" "yellow"
    
    # If batch install fails, try individual packages
    for package in "${packages[@]}"; do
      log "Installing $package individually" "green"
      if ! sudo dnf install -y "$package"; then
        log "Failed to install $package, skipping" "red"
      fi
    done
  fi
}

# Lightweight cleanup for dynamic installation
cleanup() {
  log "Running cleanup after package installation" "green"
  
  # Clean package caches
  dnf clean all
  
  log "Cleanup completed" "green"
}

main() {
  # Source logging functions from the local .devcontainer directory
  if [[ -f ".devcontainer/log.sh" ]]; then
    source ".devcontainer/log.sh"
  elif [[ -f "/usr/bin/lib/sh/log.sh" ]]; then
    source "/usr/bin/lib/sh/log.sh"
  else
    # Fallback logging if not available
    log() {
      local message="$1"
      local color="${2:-white}"
      echo "$(date '+%Y-%m-%d %H:%M:%S') $message"
    }
  fi
  
  log "10-install-packages.sh (dynamic installer)" "blue"
  
  # Parse packages from file
  local packages=()
  while IFS= read -r package; do
    [[ -n "$package" ]] && packages+=("$package")
  done < <(parse_packages)
  
  if [[ ${#packages[@]} -gt 0 ]]; then
    # Install packages if any found
    install_packages "${packages[@]}"
    cleanup
  else
    log "No packages to install" "yellow"
  fi
  
  log "Dynamic package installation completed" "green"
}

# Run main if not sourced
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
