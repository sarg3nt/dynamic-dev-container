#!/bin/bash
#
# Dynamic package installer for dev container startup.
#
# This script reads packages from a .packages file and installs them using dnf.
# It runs when the dev container starts, after the base system is built.
# The script supports batch installation with fallback to individual package
# installation if the batch fails.
#
# cSpell:ignore dnf epel crb

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC1091
source ".devcontainer/log.sh"

# Constants
readonly PACKAGES_FILE=".packages"
readonly DNF_INSTALL_TIMEOUT=300  # 5 minute timeout for dnf operations
readonly MAX_INSTALL_ATTEMPTS=3
readonly RETRY_DELAY=5

#######################################
# Parse packages from .packages file
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Outputs:
#   Package names, one per line, to stdout
# Globals:
#   PACKAGES_FILE - Path to packages configuration file
#######################################
parse_packages() {
  local packages=()
  
  if [[ ! -f "$PACKAGES_FILE" ]]; then
    log_success "No $PACKAGES_FILE file found, skipping package installation" >&2
    return 0
  fi

  if [[ ! -r "$PACKAGES_FILE" ]]; then
    log_error "Cannot read $PACKAGES_FILE file" >&2
    return 1
  fi

  log_info "Reading packages from $PACKAGES_FILE" >&2

  # Read file line by line, skip comments and empty lines
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Remove leading/trailing whitespace and skip empty lines and comments
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    
    # Validate package name (basic check for valid characters)
    if [[ ! "$line" =~ ^[a-zA-Z0-9_+.-]+$ ]]; then
      log_warning "Skipping invalid package name: $line" >&2
      continue
    fi
    
    # Add package to array
    packages+=("$line")
  done < "$PACKAGES_FILE"
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log_info "No valid packages found in $PACKAGES_FILE" >&2
    return 0
  fi
  
  log_info "Found ${#packages[@]} packages to install" >&2
  
  # Output packages one per line for main() to read
  printf '%s\n' "${packages[@]}"
  return 0
}

#######################################
# Install packages efficiently with retry logic
# Arguments:
#   Package names to install
# Returns:
#   0 on success, 1 on failure
# Globals:
#   MAX_INSTALL_ATTEMPTS, RETRY_DELAY - Retry configuration
#######################################
install_packages() {
  local packages=("$@")
  
  if [[ ${#packages[@]} -eq 0 ]]; then
    log_success "No packages to install"
    return 0
  fi

  log_info "Installing ${#packages[@]} packages: ${packages[*]}"

  # Validate dnf availability
  if ! command -v dnf >/dev/null 2>&1; then
    log_error "dnf command not found. Cannot install packages."
    return 1
  fi

  # Try batch installation with retry logic
  local attempt=1
  local batch_success=false
  
  while [[ $attempt -le $MAX_INSTALL_ATTEMPTS && $batch_success == false ]]; do
    log_info "Attempting batch installation (attempt $attempt/$MAX_INSTALL_ATTEMPTS)..."
    
    # Install all packages in one command for efficiency
    # Note: EPEL, CRB, and dnf-plugins-core already configured in base system
    if timeout "$DNF_INSTALL_TIMEOUT" sudo dnf install -y "${packages[@]}" 2>&1; then
      log_success "Batch installation completed successfully!"
      batch_success=true
      return 0
    else
      if [[ $attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
        log_warning "Batch installation failed on attempt $attempt, retrying in $RETRY_DELAY seconds..."
        sleep "$RETRY_DELAY"
      else
        log_warning "Batch installation failed after $MAX_INSTALL_ATTEMPTS attempts, trying individual installation"
      fi
    fi
    
    ((attempt++))
  done
  
  # If batch install fails, try individual packages
  local failed_packages=()
  local succeeded_packages=()
  
  for package in "${packages[@]}"; do
    log_info "Installing $package individually..."
    
    local pkg_attempt=1
    local pkg_success=false
    
    while [[ $pkg_attempt -le $MAX_INSTALL_ATTEMPTS && $pkg_success == false ]]; do
      if timeout "$DNF_INSTALL_TIMEOUT" sudo dnf install -y "$package" 2>&1; then
        log_success "Successfully installed: $package"
        succeeded_packages+=("$package")
        pkg_success=true
      else
        if [[ $pkg_attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
          log_warning "Failed to install $package (attempt $pkg_attempt), retrying..."
          sleep "$RETRY_DELAY"
        else
          log_error "Failed to install $package after $MAX_INSTALL_ATTEMPTS attempts"
          failed_packages+=("$package")
        fi
      fi
      
      ((pkg_attempt++))
    done
  done
  
  # Report results
  if [[ ${#succeeded_packages[@]} -gt 0 ]]; then
    log_info "Successfully installed ${#succeeded_packages[@]} packages: ${succeeded_packages[*]}"
  fi
  
  if [[ ${#failed_packages[@]} -gt 0 ]]; then
    log_warning "Failed to install ${#failed_packages[@]} packages: ${failed_packages[*]}"
    return 1
  fi
  
  return 0
}

#######################################
# Clean up dnf cache and temporary files after package installation
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
cleanup_package_cache() {
  log_info "Running cleanup after package installation..."
  
  # Clean dnf cache
  if ! sudo dnf clean all 2>/dev/null; then
    log_warning "Failed to clean dnf cache, continuing anyway"
    return 1
  fi
  
  # Remove any leftover temporary files
  if sudo find /tmp -name "dnf-*" -type f -delete 2>/dev/null; then
    log_info "Cleaned up temporary dnf files"
  fi
  
  log_success "Package cache cleanup completed"
  return 0
}

#######################################
# Main function to orchestrate the package installation process
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
  local exit_code=0
  
  log_info "Starting dynamic package installation process..."
  
  # Parse packages from file
  local packages=()
  while IFS= read -r package; do
    [[ -n "$package" ]] && packages+=("$package")
  done < <(parse_packages)
  
  if [[ ${#packages[@]} -gt 0 ]]; then
    # Install packages if any found
    if ! install_packages "${packages[@]}"; then
      log_error "Package installation process failed"
      exit_code=1
    fi
    
    # Clean up cache (continue even if this fails)
    if ! cleanup_package_cache; then
      log_warning "Cache cleanup failed, continuing..."
      exit_code=1
    fi
  else
    log_info "No packages to install"
  fi

  if [[ $exit_code -eq 0 ]]; then
    log_success "Dynamic package installation completed successfully!"
  else
    log_warning "Package installation completed with some failures. Check logs above for details."
  fi
  
  return $exit_code
}

# Run main if not sourced
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
