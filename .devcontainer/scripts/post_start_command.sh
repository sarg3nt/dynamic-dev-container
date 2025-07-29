#!/bin/bash
#
# Post-start command script for dev container setup.
#
# This script runs after the dev container has started and handles the setup
# of user-specific configurations, tool installations, and environment preparation.
# It manages git configuration, SSH setup, Docker/Kubernetes configs, and 
# JavaScript/Node.js tool installation.
#
# cSpell:ignore pylintrc kubectx kubens kubectl mise krew
# shellcheck disable=SC2016,SC1091

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC2016,SC1091
source "$(dirname "$0")/log.sh"

# Constants
readonly MAX_INSTALL_ATTEMPTS=5
readonly RETRY_DELAY=5
readonly MISE_CONFIG_FILE=".mise.toml"
readonly JS_BEGIN_MARKER="#### Begin Node Development"

main() {
  echo ""
  log "EXECUTING POST START COMMAND..." "gray" "INFO"
  # Set workspace path for configuration files
  WORKSPACE_PATH="${WORKSPACE_PATH:-/workspaces/$(basename "$(pwd)")}"
  export WORKSPACE_PATH
  eval "$(/usr/local/bin/mise activate bash)"

  link_pylintrc_file
  echo ""
  copy_gitconfig
  echo ""
  git_update_diff_tool
  echo ""
  copy_ssh_folder
  echo ""
  copy_kube_config
  echo ""
  copy_docker_config
  echo ""
  install_node
  echo ""
  install_node_modules
  echo ""
  # Uncomment to install PowerCLI
  # bash usr/local/bin/install_powercli
  log_success "Container startup complete. You can now start coding!"
}

#######################################
# Link the .pylintrc file from the home directory to the workspace folder
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME, WORKSPACE_PATH - Directory paths
#######################################
link_pylintrc_file() {
  log_info "Linking '.pylintrc' from Home to Workspace folder."
  
  if [[ ! -f "${HOME}/.pylintrc" ]]; then
    log_warning "No .pylintrc file found in home directory, skipping link creation"
    return 0
  fi
  
  if [[ -z "${WORKSPACE_PATH:-}" ]]; then
    log_error "WORKSPACE_PATH not set, cannot create pylintrc link"
    return 1
  fi
  
  if ln -f -s "${HOME}/.pylintrc" "${WORKSPACE_PATH}/.pylintrc" 2>/dev/null; then
    log_success "Link added successfully."
    return 0
  else
    log_error "Failed to create pylintrc link"
    return 1
  fi
}

#######################################
# Copy in the user's '.gitconfig' so modifications to it in the devcontainer do not affect the host's version
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory
#######################################
copy_gitconfig() {
  log_info "Git Config Setup:"
  local remote_config="${HOME}/.gitconfig-localhost"
  local config="${HOME}/.gitconfig"
  
  if [[ -f "$remote_config" ]]; then
    log_info "Remote '.gitconfig' detected, copying in."
    
    if cp "$remote_config" "$config" 2>/dev/null && sudo chown "$(id -u)" "$config" 2>/dev/null; then
      # Fix credential helper if it's set to manager-core (which requires GPG that may not be available)
      local current_helper
      current_helper=$(git config --global credential.helper 2>/dev/null || echo "")
      
      if [[ "$current_helper" == "manager-core" ]]; then
        log_info "Found manager-core credential helper which requires GPG. Switching to cache helper."
        git config --global credential.helper cache 2>/dev/null || true
        log_info "Updated credential helper to 'cache' (memory-only)."
      fi
      
      log_success "Copied '.gitconfig' successfully."
      return 0
    else
      log_error "Failed to copy .gitconfig file"
      return 1
    fi
  else
    log_warning "No remote '.gitconfig' file detected. You need to set up Git."
    return 0
  fi
}

#######################################
# Update the git config to make vscode default merge/diff tool and add some aliases
# Arguments:
#   None
#######################################
# Update '.gitconfig' to use VS Code as merge tool, diff tool, and editor
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory for git config file
#######################################
# NOTE: Required to use double quotes here because if we use single quotes the ' is removed from the aliases.
# shellcheck disable=SC2016
git_update_diff_tool() {
  log_info "Update '.gitconfig' to use vscode."
  
  local git_config="${HOME}/.gitconfig"
  
  if [[ ! -f "$git_config" ]]; then
    log_error "Git config file not found at $git_config"
    return 1
  fi
  
  if ! command -v code >/dev/null 2>&1; then
    log_error "VS Code command not found"
    return 1
  fi
  
  # Check if merge section already exists to avoid duplicate entries
  if ! grep -qxF '[merge]' "$git_config"; then
    cat >> "$git_config" << 'EOF'
[core]
  pager = bat
[alias]
  s = !git for-each-ref --format='%(refname:short)' refs/heads | fzf | xargs git switch
  c = !git for-each-ref --format='%(refname:short)' refs/heads | fzf | xargs git switch
EOF
    
    if [[ $? -eq 0 ]]; then
      log_success "Updated config successfully."
      return 0
    else
      log_error "Failed to update git config"
      return 1
    fi
  else
    log_info "Git config already contains merge tool configuration."
    return 0
  fi
}

#######################################
# Copy in the user's `~/.ssh` directory for SSH access
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory
#######################################
copy_ssh_folder() {
  log_info "SSH Folder Setup:"
  local remote_config="${HOME}/.ssh-localhost"
  local config="${HOME}/.ssh"
  
  if [[ -d "$remote_config" ]]; then
    log_success "Remote ssh folder detected, copying in."
    
    # Remove existing SSH directory if it exists
    if [[ -d "$config" ]] && ! rm -rf "$config" 2>/dev/null; then
      log_error "Failed to remove existing SSH directory"
      return 1
    fi
    
    # Create SSH directory and copy contents
    if mkdir -p "$config" >/dev/null 2>&1 && cp -R "${remote_config}/." "${config}/" 2>/dev/null; then
      # Set proper ownership and permissions
      if sudo chown -R "$(id -u)" "$config" 2>/dev/null && chmod 700 "$config" 2>/dev/null; then
        # Set permissions for all files in SSH directory
        find "$config" -type f -exec chmod 600 {} \; 2>/dev/null || {
          log_warning "Could not set all SSH file permissions properly"
        }
        log_success "SSH folder copied successfully with proper permissions."
        return 0
      else
        log_error "Failed to set SSH directory ownership or permissions"
        return 1
      fi
    else
      log_error "Failed to create SSH directory or copy contents"
      return 1
    fi
  else
    log_warning "No remote SSH folder detected. You need to set up SSH."
    return 0
  fi
}

#######################################
# Copy in the user's `~/.kube/config` so modifications to it in the devcontainer do not affect the host's version.
# Globals:
#   HOME
#######################################
# Copy Kubernetes configuration directory for kubectl access
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory
#######################################
copy_kube_config() {
  if command -v kubectl >/dev/null 2>&1; then
    log_info "K8s Config Setup:"
    local remote_config="${HOME}/.kube-localhost"
    local config="${HOME}/.kube"
    
    if [[ -d "$remote_config" ]]; then
      log_success "Remote k8s config detected, copying in."
      
      # Remove existing .kube directory if it exists
      if [[ -d "$config" ]] && ! rm -rf "$config" 2>/dev/null; then
        log_error "Failed to remove existing .kube directory"
        return 1
      fi
      
      # Create .kube directory and copy contents
      if mkdir -p "$config" >/dev/null 2>&1 && cp -R "${remote_config}/." "${config}/" 2>/dev/null; then
        # Set proper ownership
        if sudo chown -R "$(id -u)" "$config" 2>/dev/null; then
          log_success "Kubernetes config copied successfully."
          return 0
        else
          log_error "Failed to set proper ownership for .kube directory"
          return 1
        fi
      else
        log_error "Failed to create .kube directory or copy contents"
        return 1
      fi
    else
      log_warning "No remote k8s config detected, using defaults."
      return 0
    fi
  else
    log_info "kubectl not found, skipping Kubernetes config setup."
    return 0
  fi
}

#######################################
# Copy the user's `~/.docker/` so we can modify the config.json to remove any credStores that might be configured.
#######################################
# Copy Docker configuration directory for Docker access
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory
#######################################
copy_docker_config() {
  log_info "Docker Config Setup:"
  local remote_config="${HOME}/.docker-localhost"
  local config="${HOME}/.docker"
  
  if [[ -d "$remote_config" && -f "${remote_config}/config.json" ]]; then
    log_success "Remote Docker config detected, copying in."
    
    # Remove existing .docker directory if it exists
    if [[ -d "$config" ]] && ! rm -rf "$config" 2>/dev/null; then
      log_error "Failed to remove existing .docker directory"
      return 1
    fi
    
    # Create .docker directory and copy contents
    if mkdir -p "$config" >/dev/null 2>&1 && cp -R "${remote_config}/." "${config}/" 2>/dev/null; then
      # Set proper ownership
      if sudo chown -R "$(id -u)" "$config" 2>/dev/null; then
        log_success "Docker config copied successfully."
        return 0
      else
        log_error "Failed to set proper ownership for .docker directory"
        return 1
      fi
    else
      log_error "Failed to create .docker directory or copy contents"
      return 1
    fi
  else
    log_warning "No remote Docker config detected, using defaults."
    log_info "You should run 'docker login' to your private repos if you want to be able to push images to them."
    return 0
  fi
}

#######################################
# Install Node.js tools using native mise install command
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   MISE_CONFIG_FILE - Path to mise configuration file
#   MAX_INSTALL_ATTEMPTS - Maximum number of installation attempts
#   RETRY_DELAY - Delay between retry attempts in seconds
#######################################
install_node() {
  log_info "Installing JavaScript/Node.js tools from ${MISE_CONFIG_FILE}..."
  
  # Check if ${MISE_CONFIG_FILE}, which is usually .mise.toml, exists
  if [[ ! -f "$MISE_CONFIG_FILE" ]]; then
    log_warning "No ${MISE_CONFIG_FILE} file found, skipping JavaScript tools installation"
    return 0
  fi
  
  # Check if JavaScript/Node.js section exists
  if ! grep -q "$JS_BEGIN_MARKER" "$MISE_CONFIG_FILE"; then
    log_info "No JavaScript/Node.js tools found in ${MISE_CONFIG_FILE}"
    return 0
  fi
  
  # Check if mise command is available
  if ! command -v mise >/dev/null 2>&1; then
    log_error "mise command not found"
    return 1
  fi
  
  # Trust the mise configuration in the current directory
  log_info "Trusting mise configuration..."
  if ! mise trust "$MISE_CONFIG_FILE" 2>/dev/null; then
    log_error "Failed to trust mise configuration"
    return 1
  fi
  
  # Install tools using native mise install with retry logic
  local attempt=1
  
  while [[ $attempt -le $MAX_INSTALL_ATTEMPTS ]]; do
    log_info "Running mise install to ensure all tools are installed (attempt $attempt/$MAX_INSTALL_ATTEMPTS)..."
    
    if mise install -y 2>/dev/null; then
      log_success "JavaScript/Node.js tools installation completed"
      return 0
    else
      if [[ $attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
        log_warning "Mise install failed on attempt $attempt, retrying in $RETRY_DELAY seconds..."
        sleep "$RETRY_DELAY"
      else
        log_error "Mise install failed after $MAX_INSTALL_ATTEMPTS attempts"
        return 1
      fi
    fi
    
    ((attempt++))
  done
}

#######################################
# Install Node modules if Node.js is available and package.json exists
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   HOME - User's home directory
#######################################
install_node_modules() {
  # Activate mise environment to ensure Node.js is available
  if ! eval "$(/usr/local/bin/mise activate bash)" 2>/dev/null; then
    log_warning "Could not activate mise environment"
  fi
  
  if command -v node >/dev/null 2>&1 && [[ -f package.json ]]; then
    log_info "Node.js and package.json detected, running npm install..."
    
    if npm install 2>/dev/null; then
      log_success "Node package install completed."
      return 0
    else
      log_error "npm install failed"
      return 1
    fi
  else
    if ! command -v node >/dev/null 2>&1; then
      log_info "Node.js not found, skipping npm install."
    elif [[ ! -f package.json ]]; then
      log_info "No package.json found, skipping npm install."
    fi
    return 0
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
