#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

# cSpell:ignore kubectx kubens cmctl cloc

main() {
  source "/usr/bin/lib/sh/log.sh"
  export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin/:$PATH"

  log "50-install-other-apps.sh" "blue"

  install_cloc
  add_fzf_completions_files
  add_vscode_extensions_cache
  add_bash_history_cache
  install_omz_plugins
  install_zoxide
  clean_up
  date >/home/vscode/build_date.txt
}

install_cloc() {
  log "Adding CLOC (Count Lines of Code)" "green"
  cd /tmp
  cloc_version=$(/usr/bin/lib/sh/get_latest_version.sh AlDanial cloc)
  curl -fsSL -o cloc.tar.gz "https://github.com/AlDanial/cloc/releases/download/v${cloc_version}/cloc-${cloc_version}.tar.gz"
  tar -xzvf cloc.tar.gz --wildcards --no-anchored 'cloc'
  mv "cloc-${cloc_version}/cloc" .
  chmod +x cloc
  sudo mv cloc /usr/local/bin
  cd -
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
  git clone --depth 1 -- https://github.com/zsh-users/zsh-autosuggestions.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions"
  git clone --depth 1 -- https://github.com/zdharma-continuum/fast-syntax-highlighting.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/fast-syntax-highlighting"
  # cloning this specific tag until the following but is fixed or there is a workaround.
  # https://github.com/marlonrichert/zsh-autocomplete/issues/797
  git clone --branch "24.09.04" --depth 1 -- https://github.com/marlonrichert/zsh-autocomplete.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autocomplete"
  git clone --depth 1 -- https://github.com/zsh-users/zsh-completions.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-completions"
}

install_zoxide() {
  log "Installing zoxide cd replacement tool" "green"
  curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
}


clean_up() {
  echo ""
  log "Deleting files from /tmp" "green"
  sudo rm -rf /tmp/*
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
