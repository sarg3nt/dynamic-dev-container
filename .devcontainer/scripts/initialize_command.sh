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
readonly CONTAINER_IMAGE="ghcr.io/sarg3nt/dynamic-dev-container:latest"

# Directory configuration: "name|permission|log_level|impact_message"
readonly DIRECTORY_CONFIG=(
  ".docker||warning|Docker may not work properly without this folder."
  ".kube||warning|Kubectl may not work properly without this folder."
  ".ssh|700|error|You need to run 'ssh-keygen' to finish setup."
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
        
        log "Created ${dir_name} folder in your home directory." "$color" "${log_level^^}"
        
        # Log the impact message if provided (only for newly created directories)
        if [[ -n "$impact_message" ]]; then
          log "$impact_message" "$color" "${log_level^^}"
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
# Setup Git configuration if .gitconfig doesn't exist
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - The user's home directory
#######################################
setup_git_config() {
  log_info "Checking Git configuration..."
  
  local gitconfig_path="${HOME}/.gitconfig"
  
  # Check if .gitconfig already exists
  if [[ -f "$gitconfig_path" ]]; then
    log_info "Found existing .gitconfig file, skipping Git configuration setup."
    return 0
  fi
  
  log_warning "No .gitconfig file found in your home directory."
  log_info "Let's set up your Git configuration..."
  
  # Prompt for user name
  local git_name=""
  while [[ -z "$git_name" ]]; do
    echo -n "Please enter your full name for Git commits: "
    read -r git_name
    if [[ -z "$git_name" ]]; then
      log_warning "Name cannot be empty. Please try again."
    fi
  done
  
  # Prompt for user email
  local git_email=""
  while [[ -z "$git_email" ]]; do
    echo -n "Please enter your email address for Git commits: "
    read -r git_email
    if [[ -z "$git_email" ]]; then
      log_warning "Email cannot be empty. Please try again."
    elif [[ ! "$git_email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
      log_warning "Please enter a valid email address."
      git_email=""
    fi
  done
  
  # Set Git configuration with user-provided values
  if git config --global user.name "$git_name" 2>/dev/null && \
     git config --global user.email "$git_email" 2>/dev/null; then
    
    log_success "Git configuration created successfully!"
    log_info "Name: $git_name"
    log_info "Email: $git_email"
    log_info "You can change these later using 'git config --global user.name \"New Name\"' and 'git config --global user.email \"new.email@example.com\"'"
    return 0
  else
    log_error "Failed to create Git configuration."
    return 1
  fi
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
  
  # Setup Git configuration if needed
  if ! setup_git_config; then
    log_error "Failed to setup Git configuration"
    log_error "You can manually configure Git using these commands:"
    log_error "  git config --global user.name \"Your Full Name\""
    log_error "  git config --global user.email \"your.email@example.com\""
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
