#!/bin/bash

# cSpell:ignore pylintrc kubectx kubens kubectl mise krew
# shellcheck disable=SC2016,SC1091

set -euo pipefail
IFS=$'\n\t'

source "$(dirname "$0")/utils/log.sh"

main() {
  echo ""
  log "EXECUTING POST START COMMAND..." "gray" "INFO"
  eval "$(/usr/local/bin/mise activate bash 2>/dev/null)" || true
  link_pylintrc_file
  echo ""
  git_update_diff_tool
  echo ""
  copy_ssh_folder
  echo ""
  copy_kube_config
  echo ""
  copy_docker_config
  echo ""
  install_kubectl_plugins
  echo ""
  install_kubectx_kubens_completions
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
# Install any kubectl plugins using krew.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
install_kubectl_plugins() {
  if command -v krew >/dev/null 2>&1; then
    log_info "Adding krew to the path" "green"
    export_statement="export PATH=\"\${KREW_ROOT:-\$HOME/.krew}/bin:\$PATH\""
    echo "$export_statement" >>~/.zshrc
    echo "$export_statement" >>~/.bashrc

    log_info "Installing plugins" "green"
    krew install access-matrix blame get-all node-restart switch-config view-allocations

    # Create a flag file to indicate krew plugins installation is complete
    touch "${HOME}/.krew_plugins_ready"

    log_info "Deleting files from /tmp" "green"
    sudo rm -rf /tmp/* || true
  else
    # If krew is not available, still create the flag to avoid waiting
    touch "${HOME}/.krew_plugins_ready"
  fi
}

#######################################
# Install kubectx and kubens completions.
# Globals:
#   HOME
# Arguments:
#   None
#######################################
install_kubectx_kubens_completions() {
  if command -v kubectl >/dev/null 2>&1; then
    log "Installing kubectx and kubens completions" "green"
    mkdir -p "$HOME/.oh-my-zsh/custom/completions"
    chmod -R 755 "$HOME/.oh-my-zsh/custom/completions"

    log "Installing kubectx completions" "green"
    curl -sL https://raw.githubusercontent.com/ahmetb/kubectx/master/completion/_kubectx.zsh --output "$HOME/.oh-my-zsh/custom/completions/_kubectx.zsh"
    log "Installing kubens completions" "green"
    curl -sL https://raw.githubusercontent.com/ahmetb/kubectx/master/completion/_kubens.zsh --output "$HOME/.oh-my-zsh/custom/completions/_kubens.zsh"
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
