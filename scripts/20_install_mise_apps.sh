#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# cSpell:ignore devel libuuid gdbm libnsl epel

main() {
  source "/usr/bin/lib/sh/log.sh"

  ############ Install mise
  log "20_install_mise_apps.sh" "blue"
  log "****** GITHUB API TOKEN: $GITHUB_API_TOKEN"
  log "Sourcing Mise files" "green"
  eval "$(/usr/local/bin/mise activate bash)"
  mise trust --all
  export MISE_VERBOSE=1
  
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

  # Clean caches
  #pip cache purge

  log "Deleting files from /tmp" "green"
  sudo rm -rf /tmp/*
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
