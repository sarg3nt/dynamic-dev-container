#!/bin/bash

set -euo pipefail
source "/usr/bin/lib/sh/log.sh"

log "Setting up known hosts file" "blue"
ssh_dir="$HOME/.ssh"

if ! [ -d  "$ssh_dir" ]; then
    mkdir -p "$ssh_dir"
fi
