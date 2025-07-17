#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

# cSpell:ignore kubectx kubens cmctl cloc

main() {
  source "/usr/bin/lib/sh/log.sh"
  export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin/:$PATH"

  log "30-install-other-apps.sh" "blue"
  # Python 3.13 is already installed via mise config - no need to install again
  add_fzf_completions_files
  add_vscode_extensions_cache
  add_bash_history_cache
  install_omz_plugins
  clean_up
  date >/home/vscode/build_date.txt
}

add_vscode_extensions_cache() {
  log "Adding VSCode Extensions Cache Support" "green"
  mkdir -p "/home/${USERNAME}/.vscode-server/extensions"
  chown -R "${USERNAME}" "/home/${USERNAME}/.vscode-server"
}

add_bash_history_cache() {
  log "Adding Bash History Cache Support" "blue"
  sudo mkdir /commandhistory
  sudo touch /commandhistory/.bash_history
  sudo chown -R "$USERNAME" "/commandhistory"
}

add_fzf_completions_files() {
  log "Adding FZF Completions Files" "green"
  curl -sL https://raw.githubusercontent.com/junegunn/fzf/master/shell/key-bindings.zsh --output "$HOME/.fzf-key-bindings.zsh"
  curl -sL https://raw.githubusercontent.com/junegunn/fzf/master/shell/completion.zsh --output "$HOME/.fzf-completion.zsh"
}

install_omz_plugins() {
  log "Installing Oh My ZSH plugins" "green"
  
  # Create plugins directory
  local plugins_dir="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins"
  mkdir -p "$plugins_dir"
  
  # Helper function to clean up plugin directory
  clean_plugin_dir() {
    local plugin_dir="$1"
    local plugin_name
    plugin_name=$(basename "$plugin_dir")
    
    log "Cleaning up $plugin_name plugin directory" "green"
    
    # Remove git directory
    rm -rf "$plugin_dir/.git"
    
    # Remove documentation files
    find "$plugin_dir" -type f \( \
      -name "*.md" -o \
      -name "*.adoc" -o \
      -name "*.txt" -o \
      -name "*.rst" -o \
      -name "CHANGELOG*" -o \
      -name "LICENSE*" -o \
      -name "COPYING*" -o \
      -name "AUTHORS*" -o \
      -name "CONTRIBUTORS*" \
    \) -delete
    
    # Remove test and development directories
    find "$plugin_dir" -type d \( \
      -name "test" -o \
      -name "tests" -o \
      -name "spec" -o \
      -name "specs" -o \
      -name ".github" -o \
      -name "images" -o \
      -name "img" -o \
      -name "docs" -o \
      -name "doc" -o \
      -name "examples" -o \
      -name "demo" \
    \) -exec rm -rf {} +
    
    # Remove development and build files
    find "$plugin_dir" -type f \( \
      -name ".gitignore" -o \
      -name ".gitmodules" -o \
      -name ".travis.yml" -o \
      -name ".github*" -o \
      -name "Makefile" -o \
      -name "makefile" -o \
      -name "*.yml" -o \
      -name "*.yaml" -o \
      -name ".fast-*" -o \
      -name "*.json" \
    \) -delete
    
    # Remove any remaining empty directories
    find "$plugin_dir" -type d -empty -delete
    
    log "Cleaned up $plugin_name - keeping only essential files" "green"
  }
  
  # Install zsh-autosuggestions
  log "Installing zsh-autosuggestions" "green"
  git clone --depth 1 -- https://github.com/zsh-users/zsh-autosuggestions.git "$plugins_dir/zsh-autosuggestions"
  clean_plugin_dir "$plugins_dir/zsh-autosuggestions"
  
  # Install fast-syntax-highlighting
  log "Installing fast-syntax-highlighting" "green"
  git clone --depth 1 -- https://github.com/zdharma-continuum/fast-syntax-highlighting.git "$plugins_dir/fast-syntax-highlighting"
  clean_plugin_dir "$plugins_dir/fast-syntax-highlighting"
  
  # Install zsh-autocomplete (specific version due to bug)
  # cloning this specific tag until the following bug is fixed or there is a workaround.
  # https://github.com/marlonrichert/zsh-autocomplete/issues/797
  log "Installing zsh-autocomplete (v24.09.04)" "green"
  git clone --branch "24.09.04" --depth 1 -- https://github.com/marlonrichert/zsh-autocomplete.git "$plugins_dir/zsh-autocomplete"
  clean_plugin_dir "$plugins_dir/zsh-autocomplete"
  
  # Install zsh-completions
  log "Installing zsh-completions" "green"
  git clone --depth 1 -- https://github.com/zsh-users/zsh-completions.git "$plugins_dir/zsh-completions"
  clean_plugin_dir "$plugins_dir/zsh-completions"
  
  # Final size report
  log "Plugin installation complete. Final sizes:" "blue"
  du -sh "$plugins_dir"/* 2>/dev/null || true
}

clean_up() {
  echo ""
  log "Deleting files from /tmp" "green"
  sudo rm -rf /tmp/* || true
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
