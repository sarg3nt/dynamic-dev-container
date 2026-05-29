#!/bin/bash
#
# Initialize command script for dev container setup.
#
# This script handles the initial setup when the dev container is being built.
# It pulls the latest container image and creates required directories for
# Docker, Kubernetes, SSH, and other development tools.
#
# cSpell:ignore sarg gnupg

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
source "$(dirname "$0")/log.sh"

# Constants
# TODO: revert to ":latest" once the arm64 base image is published to ghcr.io.
# Pinned to the locally-built tag while we iterate on M-series support so the
# pull step does not clobber the local build with the amd64-only published tag.
readonly CONTAINER_IMAGE="ghcr.io/sarg3nt/dynamic-dev-container:1.0.4-support-macs"

# Directory configuration: "name|permission|log_level|impact_message"
readonly DIRECTORY_CONFIG=(
  ".docker||warning|Docker may not work properly without this folder."
  ".kube||warning|Kubectl may not work properly without this folder."
  ".ssh|700|error|You need to run 'ssh-keygen' to finish setup."
)

#######################################
# Print the host's docker platform ("linux/amd64" or "linux/arm64").
# Dev containers always run as linux/<arch> regardless of host OS (macOS,
# Windows, Linux) because the container engine provides a Linux VM.
#######################################
host_docker_platform() {
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|amd64)   arch=amd64 ;;
    arm64|aarch64)  arch=arm64 ;;
    *)              arch="$arch" ;;
  esac
  printf 'linux/%s\n' "$arch"
}

#######################################
# Print the platform of a locally-present image ("os/arch"), or empty if the
# image is not present locally.
#######################################
local_image_platform() {
  docker image inspect "$1" --format '{{.Os}}/{{.Architecture}}' 2>/dev/null || true
}

#######################################
# Ensure the base image is available locally and matches the host platform.
#
# - If `SKIP_BASE_IMAGE_PULL=1` is set, trust whatever is tagged locally.
# - If the locally-tagged image already matches the host platform, skip the
#   pull. This protects a locally-built image (e.g. `make build` followed by
#   `docker tag …:latest`) from being clobbered on every restart when the
#   published `:latest` only has a different arch.
# - Otherwise pull. If the pulled image's platform does not match the host,
#   fail with a clear message rather than let the build blow up later with
#   a cryptic "CPU does not support x86-64-v3" from Rocky 10 glibc under QEMU.
# Globals:
#   CONTAINER_IMAGE - The container image to pull
# Returns:
#   0 on success, 1 on failure
#######################################
get_latest_dev_container_version() {
  local host_plat local_plat
  host_plat=$(host_docker_platform)
  local_plat=$(local_image_platform "$CONTAINER_IMAGE")

  if [[ -n "${SKIP_BASE_IMAGE_PULL:-}" ]]; then
    log_info "SKIP_BASE_IMAGE_PULL is set; using local ${CONTAINER_IMAGE} (${local_plat:-not present})."
    return 0
  fi

  if [[ -n "$local_plat" && "$local_plat" == "$host_plat" ]]; then
    log_info "Local ${CONTAINER_IMAGE} already matches host platform (${host_plat}); skipping pull."
    log_info "Set SKIP_BASE_IMAGE_PULL=1 to suppress this check. Unset to force a pull."
    return 0
  fi

  log_info "Pulling latest 'dynamic-dev-container' image from GitHub Container Registry."
  echo ""

  if ! docker pull "$CONTAINER_IMAGE" 2>&1; then
    echo ""
    log_error "Failed to pull the latest dynamic-dev-container image. Please check your connection or credentials."
    log_error "The container will attempt to load with a cached copy if you have it."
    return 1
  fi

  echo ""
  local pulled_plat
  pulled_plat=$(local_image_platform "$CONTAINER_IMAGE")

  if [[ -n "$pulled_plat" && "$pulled_plat" != "$host_plat" ]]; then
    log_error "Pulled ${CONTAINER_IMAGE} has platform ${pulled_plat}, host is ${host_plat}."
    log_error "Rocky Linux 10 glibc is compiled for x86-64-v3 and will not run under Docker's QEMU emulation."
    log_error "Build a local base image with 'make build' and tag it as ${CONTAINER_IMAGE}, then set SKIP_BASE_IMAGE_PULL=1."
    return 1
  fi

  log_success "Latest dynamic-dev-container image pulled successfully (${pulled_plat})."
  return 0
}

#######################################
# Ensure all required folders exist
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - The user's home directory
#   DIRECTORY_CONFIG - Array of directory configurations
#######################################
create_required_folders() {
  log_info "Ensuring required folders exist."
  local failed_directories=()
  
  for dir_config in "${DIRECTORY_CONFIG[@]}"; do
    # Parse the config string: "name|permission|log_level|impact_message"
    IFS='|' read -r dir_name permission log_level impact_message <<< "$dir_config"
    local full_path="${HOME}/${dir_name}"
    
    # Check if directory already exists
    local dir_existed=false
    if [[ -d "$full_path" ]]; then
      dir_existed=true
    fi
    
    # Always ensure directory exists (mkdir -p is safe)
    if mkdir -p "$full_path" 2>/dev/null; then
      # Set directory permissions if specified
      if [[ -n "$permission" ]]; then
        chmod "$permission" "$full_path" 2>/dev/null || true
      fi
      
      # Log appropriate message based on whether directory existed
      if [[ "$dir_existed" == true ]]; then
        log_info "Verified ${dir_name} folder exists in your home directory."
      else
        # Log directory-specific messages using configured log level
        local color_map=("error:red" "warning:yellow" "info:blue")
        local color="blue"  # default for info
        
        # Find the color for the log level
        for mapping in "${color_map[@]}"; do
          if [[ "$log_level" == "${mapping%:*}" ]]; then
            color="${mapping#*:}"
            break
          fi
        done
        
        # Uppercase the log level without bash 4's ${var^^} — this script
        # runs on the host and macOS ships bash 3.2.
        local log_level_upper
        log_level_upper=$(printf '%s' "$log_level" | tr '[:lower:]' '[:upper:]')
        log "Created ${dir_name} folder in your home directory." "$color" "$log_level_upper"

        # Log the impact message if provided (only for newly created directories)
        if [[ -n "$impact_message" ]]; then
          log "$impact_message" "$color" "$log_level_upper"
        fi
      fi
    else
      failed_directories+=("$dir_name")
    fi
  done

  if [[ ${#failed_directories[@]} -gt 0 ]]; then
    log_error "Failed to create ${#failed_directories[@]} directories: ${failed_directories[*]}"
    return 1
  else
    log_success "All required directories are ready!"
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
