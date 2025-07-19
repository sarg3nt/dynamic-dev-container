#!/bin/bash

# cSpell:ignore sarg

set -euo pipefail
IFS=$'\n\t'

source "$(dirname "$0")/log.sh"

main() {
  echo ""
  log "EXECUTING INITIALIZE COMMAND..." "gray" "INFO"
  get_latest_dev_container_version
  create_required_folders
  echo ""
  log_info "Dev Container is now building, this might take a while the first time or after a 'Rebuild Container' command."
  log_info "To view the progress of the build click 'Connecting to Dev Container (show log)' in the bottom right corner of VS Code."
}

#######################################
# Get the latest version of the dev container
#
# Description:
#   Pulls the latest 'dynamic-dev-container' Docker image from GitHub Container Registry.
#   Logs success or failure messages based on the outcome.
#
# Arguments:
#   None
#
# Exits:
#   1 - If the Docker pull command fails.
#######################################
get_latest_dev_container_version() {
  log_info "Pulling latest 'dynamic-dev-container' image from GitHub Container Registry."
  echo ""
  if docker pull ghcr.io/sarg3nt/dynamic-dev-container:0.0.1; then
    echo ""
    log_success "Latest dynamic-dev-container image pulled successfully."
  else
    echo ""
    log_error "Failed to pull the latest dynamic-dev-container image. Please check your connection or credentials."
    log_error "The container will attempt to load with a cached copy if you have it."
  fi
}

#######################################
# Create any required missing folders
#
# Description:
#   Ensures that essential directories for Docker, Kubernetes, and K9s exist
#   in the user's home directory. Creates them if they are missing.
#
# Globals:
#   HOME - The user's home directory.
#
# Arguments:
#   None
#
# Logs:
#   Info, warnings, or errors based on the folder creation status.
#######################################
create_required_folders() {
  log_info "Creating required folders (if they don't exist)."
  local directories_created=false
  if [[ ! -d "${HOME}/.docker" ]]; then
    log_error "You did not have a .docker folder in your home directory, creating."
    log_error "Docker may will not work properly without this folder."
    echo ""
    mkdir -p "${HOME}/.docker"
    directories_created=true
  fi

  if [[ ! -d "${HOME}/.kube" ]]; then
    log_error "You did not have a .kube folder in your home directory, creating."
    log_error "Kubectl and k9s will not work without this folder."
    echo ""
    mkdir -p "${HOME}/.kube"
    directories_created=true
  fi

  if [[ ! -d "${HOME}/.config/k9s" ]]; then
    log_error "You did not have a .k9s folder in your home directory, creating."
    log_error "K9s will use a local config."
    echo ""
    mkdir -p "${HOME}/.config/k9s"
    mkdir -p "${HOME}/.local/share/k9s"
    directories_created=true
  fi

  if [[ ! -d "${HOME}/.ssh" ]]; then
    log_warning "WARNING: You did not have an '.ssh' folder in your home directory."
    log_warning "We created a '.ssh' folder for you so the mount didn't fail but you need to run 'ssh-keygen' to finish setup."
    mkdir -p "${HOME}/.ssh"
    directories_created=true
  fi

  if [[ "$directories_created" = false ]]; then
    log_info "All required directories already exist!"
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
