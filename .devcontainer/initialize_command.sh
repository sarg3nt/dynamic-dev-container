#!/bin/bash
#
# Initialize command script for dev container setup.
#
# This script handles the initial setup when the dev container is being built.
# It pulls the latest container image and creates required directories for
# Docker, Kubernetes, SSH, and other development tools.
#
# cSpell:ignore sarg

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
source "$(dirname "$0")/log.sh"

# Constants
readonly CONTAINER_IMAGE="ghcr.io/sarg3nt/dynamic-dev-container:0.0.3"
readonly REQUIRED_DIRECTORIES=(
  ".docker"
  ".kube"
  ".config/k9s"
  ".local/share/k9s"
  ".ssh"
)

#######################################
# Get the latest version of the dev container
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   CONTAINER_IMAGE - The container image to pull
#######################################
get_latest_dev_container_version() {
  log_info "Pulling latest 'dynamic-dev-container' image from GitHub Container Registry."
  echo ""
  
  if docker pull "$CONTAINER_IMAGE" 2>&1; then
    echo ""
    log_success "Latest dynamic-dev-container image pulled successfully."
    return 0
  else
    echo ""
    log_error "Failed to pull the latest dynamic-dev-container image. Please check your connection or credentials."
    log_error "The container will attempt to load with a cached copy if you have it."
    return 1
  fi
}

#######################################
# Create any required missing folders
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - The user's home directory
#   REQUIRED_DIRECTORIES - Array of directories to create
#######################################
create_required_folders() {
  log_info "Creating required folders (if they don't exist)."
  local directories_created=false
  local failed_directories=()
  
  for dir_name in "${REQUIRED_DIRECTORIES[@]}"; do
    local full_path="${HOME}/${dir_name}"
    
    if [[ ! -d "$full_path" ]]; then
      log_warning "Creating missing directory: $full_path"
      
      if mkdir -p "$full_path" 2>/dev/null; then
        directories_created=true
        
        # Set appropriate permissions for SSH directory
        if [[ "$dir_name" == ".ssh" ]]; then
          chmod 700 "$full_path" 2>/dev/null || true
          log_warning "WARNING: You did not have an '.ssh' folder in your home directory."
          log_warning "We created a '.ssh' folder for you so the mount didn't fail but you need to run 'ssh-keygen' to finish setup."
        fi
        
        # Log specific warnings for different directories  
        case "$dir_name" in
          ".docker")
            log_error "You did not have a .docker folder in your home directory, creating."
            log_error "Docker may not work properly without this folder."
            ;;
          ".kube")
            log_error "You did not have a .kube folder in your home directory, creating."
            log_error "Kubectl and k9s will not work without this folder."
            ;;
          ".config/k9s"|".local/share/k9s")
            log_error "You did not have a .k9s folder in your home directory, creating."
            log_error "K9s will use a local config."
            ;;
        esac
        
        echo ""
      else
        log_error "Failed to create directory: $full_path"
        failed_directories+=("$dir_name")
      fi
    fi
  done

  if [[ "$directories_created" == false ]]; then
    log_success "All required directories already exist!"
  fi
  
  if [[ ${#failed_directories[@]} -gt 0 ]]; then
    log_error "Failed to create ${#failed_directories[@]} directories: ${failed_directories[*]}"
    return 1
  fi
  
  return 0
}

#######################################
# Main function to orchestrate the initialization process
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
  local exit_code=0
  
  echo ""
  log "EXECUTING INITIALIZE COMMAND..." "gray" "INFO"
  
  # Pull latest container image (continue even if this fails)
  if ! get_latest_dev_container_version; then
    log_warning "Container image pull failed, continuing with initialization..."
    exit_code=1
  fi
  
  # Create required directories
  if ! create_required_folders; then
    log_error "Failed to create some required directories"
    exit_code=1
  fi
  
  echo ""
  if [[ $exit_code -eq 0 ]]; then
    log_success "Dev Container initialization completed successfully!"
  else
    log_warning "Dev Container initialization completed with some issues. Check logs above for details."
  fi
  
  log_info "Dev Container is now building, this might take a while the first time or after a 'Rebuild Container' command."
  log_info "To view the progress of the build click 'Connecting to Dev Container (show log)' in the bottom right corner of VS Code."
  
  return $exit_code
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
