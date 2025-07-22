#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

main() {
  source "/usr/bin/lib/sh/log.sh"
  install_mise_packages
  cleanup
}

install_mise_packages() {
  log "20_install_mise_tools.sh" "blue"

  # Mise is installed in the docker file from it's master docker branch.
  log "Configuring mise" "green"
  export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin/:$PATH"

  log "Mise version" "green"
  mise version

  log "Trusting configuration files" "green"
  mise trust "$HOME/.config/mise/config.toml"

  #export MISE_VERBOSE=1
  
  log "Installing tools with mise" "green"
  local retries=5
  local count=0
  until mise install --yes; do
    exit_code=$?
    count=$((count + 1))
    if [ $count -lt $retries ]; then
      log "mise install failed. Retrying ($count/$retries)..." "yellow"
      sleep 2
    else
      log "mise install failed after $retries attempts." "red"
      return $exit_code
    fi
  done
  
  log "Mise tool install complete" "green"
}

cleanup() {
  log "Running cleanup for container size optimization" "blue"

  log "Deleting files from /tmp" "green"
  sudo rm -rfv /tmp/*

  log "Deleting all .git directories" "green"
  find / -path /proc -prune -o -type d -name ".git" -not -path '/.git' -exec rm -rf {} + 2>/dev/null || true

  log "Deleting all data in /var/log" "green"
  sudo rm -rfv /var/log/*

  log "Delete Python cache files" "green"
  sudo find / -name "__pycache__" -type d -exec rm -rfv {} + 2>/dev/null || true
  sudo find / -name "*.pyc" -exec rm -fv {} + 2>/dev/null || true
  
  log "Remove pip cache (if accessible)" "green"
  rm -rf /home/vscode/.cache/pip/* 2>/dev/null || true
  
  # Note: Skipping mise cache clear since we're using Docker cache mount
  log "Skipping mise cache clear (using Docker cache mount)" "yellow"
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
