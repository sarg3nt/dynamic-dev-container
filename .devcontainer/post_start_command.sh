#!/bin/bash

# cSpell:ignore pylintrc kubectx kubens kubectl mise krew
# shellcheck disable=SC2016,SC1091

set -euo pipefail
IFS=$'\n\t'

# Source the logging utility and mise parser
# shellcheck disable=SC2016,SC1091
source "$(dirname "$0")/log.sh"
source "$(dirname "$0")/mise_parser.sh"

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
}

#######################################
# Link the .pylintrc file from the home directory to the workspace folder
# Arguments:
#   None
#######################################
link_pylintrc_file() {
  log_info "Linking '.pylintrc' from Home to Workspace folder."
  ln -f -s "${HOME}/.pylintrc" "${WORKSPACE_PATH}/.pylintrc"
  log_success "Link added successfully."
}

#######################################
# Copy in the user's '.gitconfig' so modifications to it in the devcontainer do not affect the host's version.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
copy_gitconfig() {
  log_info "Git Config Setup:"
  REMOTE_CONFIG="${HOME}/.gitconfig-localhost"
  CONFIG="${HOME}/.gitconfig"
  if [[ -f "$REMOTE_CONFIG" ]]; then
    log_info "Remote '.gitconfig' detected, copying in."
    cp "$REMOTE_CONFIG" "$CONFIG"
    sudo chown "$(id -u)" "$CONFIG"
    log_success "Copied '.gitconfig' successfully."

  else
    log_warning "No remote '.gitconfig' file detected. You need to set up Git."
  fi
}

#######################################
# Update the git config to make vscode default merge/diff tool and add some aliases
# Arguments:
#   None
#######################################
# NOTE Required to use double quotes here because if we use single quotes the ' is removed from the aliases.
# shellcheck disable=SC2016
git_update_diff_tool() {
  log_info "Update '.gitconfig' to use vscode."
  grep -qxF '[merge]' ~/.gitconfig || echo "
[merge]
  tool = vscode
[mergetool \"vscode\"]
  cmd = code --wait \$MERGED
[diff]
  tool = vscode
[difftool \"vscode\"]
  cmd = code --wait --diff \$LOCAL \$REMOTE
[core]
  editor = \"code --wait\"
  pager = bat
[alias]
  s = !git for-each-ref --format='%(refname:short)' refs/heads | fzf | xargs git switch
  c = !git for-each-ref --format='%(refname:short)' refs/heads | fzf | xargs git switch
" >>~/.gitconfig
  log_success "Updated config successfully."
}

#######################################
# Copy in the user's `~/.ssh` so modifications to it in the devcontainer do not affect the host's version.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
copy_ssh_folder() {
  log_info "SSH Folder Setup:"
  REMOTE_CONFIG="${HOME}/.ssh-localhost"
  CONFIG="${HOME}/.ssh"
  if [[ -d "$REMOTE_CONFIG" ]]; then
    log_success "Remote ssh folder detected, copying in."
    rm -rf "$CONFIG"
    mkdir -p "${CONFIG}" >/dev/null 2>&1
    cp -R "${REMOTE_CONFIG}/." "${CONFIG}/"
    sudo chown -R "$(id -u)" "${CONFIG}"
  else
    log_warning "No remote SSH folder detected. You need to set up SSH."
  fi
}

#######################################
# Copy in the user's `~/.kube/config` so modifications to it in the devcontainer do not affect the host's version.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
copy_kube_config() {
  if command -v kubectl >/dev/null 2>&1; then
    log_info "K8s Config Setup:"
    REMOTE_CONFIG="${HOME}/.kube-localhost"
    CONFIG="${HOME}/.kube"
    if [[ -d "$REMOTE_CONFIG" ]]; then
      log_success "Remote k8s config detected, copying in."
      rm -rf "$CONFIG"
      mkdir -p "${CONFIG}" >/dev/null 2>&1
      cp -R "${REMOTE_CONFIG}/." "${CONFIG}/"
      sudo chown -R "$(id -u)" "${CONFIG}"
    else
      log_warning "No remote k8s config detected, using defaults."
    fi
  fi
}

#######################################
# Copy the user's `~/.docker/` so we can modify the config.json to remove any credStores that might be configured.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
copy_docker_config() {
  log_info "Docker Config Setup:"
  REMOTE_CONFIG="${HOME}/.docker-localhost"
  CONFIG="${HOME}/.docker"
  if [[ -d "$REMOTE_CONFIG" && -f "${REMOTE_CONFIG}/config.json" ]]; then
    log_success "Remote Docker config detected, copying in."
    rm -rf "$CONFIG"
    mkdir -p "${CONFIG}" >/dev/null 2>&1
    cp -R "${REMOTE_CONFIG}/." "${CONFIG}/"
    sudo chown -R "$(id -u)" "${CONFIG}"
  else
    log_warning "No remote Docker config detected, using defaults."
    log_info "You should run 'docker login' to your private repos if you want to be able to push images to them."
  fi
}

#######################################
# Install Node.js tools from the JavaScript/Node.js Development section of .mise.toml
# Arguments:
#   None
#######################################
install_node() {
  log_info "Installing JavaScript/Node.js tools from .mise.toml..."
  
  # Check if .mise.toml exists
  if [[ ! -f ".mise.toml" ]]; then
    log_warning "No .mise.toml file found, skipping JavaScript tools installation"
    return 0
  fi
  
  # Declare arrays for JavaScript tools and aliases
  local js_tools_array=()
  declare -A aliases_array
  
  # Parse only JavaScript/Node.js tools and aliases from .mise.toml
  parse_mise_tools "js_tools_array" "include_js"
  parse_mise_aliases "aliases_array"
  
  # Check if any JavaScript tools were found
  if [[ ${#js_tools_array[@]} -eq 0 ]]; then
    log_info "No JavaScript/Node.js tools found in .mise.toml"
    return 0
  fi
  
  # Install JavaScript tools locally (not globally)
  install_tools_with_mise "js_tools_array" "aliases_array" ""
  
  log_success "JavaScript/Node.js tools installation completed"
}

#######################################
# Install Node modules if node is installed.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
install_node_modules() {
  eval "$(/usr/local/bin/mise activate bash)"
  if command -v node >/dev/null 2>&1 && [[ -f package.json ]]; then
    log_info "Node.js and package.json detected, running npm install..."
    npm install
    log_success "Node package install completed."
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
