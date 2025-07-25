#!/bin/bash
#
# Dynamic package installer for dev container startup.
# Reads packages from /.packages file and installs them.
# This runs when the dev container starts, after the base system is built.
#
# cSpell:ignore dnf epel crb

set -euo pipefail
IFS=$'\n\t'

# Parse packages from .packages file
parse_packages() {
  local packages_file=".packages"
  local packages=()
  
  if [[ ! -f "$packages_file" ]]; then
    log_success "No /.packages file found, skipping package installation" >&2
    return 0
  fi

  log_info "Reading packages from $packages_file" >&2

  # Read file line by line, skip comments and empty lines
  while IFS= read -r line; do
    # Remove leading/trailing whitespace and skip empty lines and comments
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    
    # Add package to array
    packages+=("$line")
  done < "$packages_file"
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log_success "No packages found in $packages_file" >&2
    return 0
  fi
  
  # Output packages one per line for main() to read
  printf '%s\n' "${packages[@]}"
}

# Install packages efficiently
install_packages() {
  local packages=("$@")
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log_success "No packages to install"
    return 0
  fi

  log_info "Installing ${#packages[@]} packages in batch: ${packages[*]}"

  # Install all packages in one command for efficiency
  # Note: EPEL, CRB, and dnf-plugins-core already configured in base system
  if ! sudo dnf install -y "${packages[@]}"; then
    log_warning "Package installation failed, trying individual installation"
    
    # If batch install fails, try individual packages
    for package in "${packages[@]}"; do
      log_info "Installing $package individually"
      if ! sudo dnf install -y "$package"; then
        log_error "Failed to install $package, skipping"
      fi
    done
  fi
}

# Lightweight cleanup for dynamic installation
cleanup() {
  log_info "Running cleanup after package installation"
  dnf clean all
  log_success "Cleanup completed"
}

main() {
  # Source logging functions from the local .devcontainer directory
  # shellcheck disable=SC1091
  source ".devcontainer/log.sh"
  
  log_info "10-install-packages.sh"
  
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
    log_success "No packages to install"
  fi

  log_success "Dynamic package installation completed"
}

# Run main if not sourced
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
