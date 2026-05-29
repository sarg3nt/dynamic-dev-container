#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

# cSpell:ignore ncdu, epel, buildx, socat, devel, btop, iputils, nmap snmp

# Install system packages
setup() {
  log "Adding install_weak_deps=False to /etc/dnf/dnf.conf" "green"
  echo "install_weak_deps=False" >>/etc/dnf/dnf.conf

  log "Installing epel release" "green"
  dnf install -y epel-release

  log "Installing dnf plugins core" "green"
  dnf install -y dnf-plugins-core

  log "Running /usr/bin/crb enable" "green"
  /usr/bin/crb enable

  log "Adding docker ce repo" "green"
  dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

  log "Running dnf upgrade" "green"
  dnf upgrade -y
}

package_install() {
  log "Installing essential system packages in batch" "green"
  dnf install -y \
    bash-completion \
    binutils \
    bzip2-libs \
    ca-certificates \
    docker-ce-cli \
    docker-buildx-plugin \
    git \
    gnupg2 \
    jq \
    socat \
    util-linux-user \
    xz
}

install_dev_container_features() {
  log "Installing Microsoft Dev Container Features" "green"

  # Use temporary directory and clean up after
  local temp_dir
  temp_dir=$(mktemp -d)
  
  log "Cloning devcontainers features repository to $temp_dir" "green"
  git clone --depth 1 https://github.com/devcontainers/features.git "$temp_dir/features"

  log "Running common-utils install script" "green"
  cd "$temp_dir/features/src/common-utils/"
  ./install.sh
  
  # Return to original directory
  cd - > /dev/null
}

# /commandhistory is a root-owned dir chowned to the dev user so shell history
# persists across container rebuilds. Created here because 10.sh runs as root:
# the image build has no working sudo, so this can't live in the vscode-context
# scripts (20/30). Runs after common-utils, which creates the dev user.
add_bash_history_cache() {
  log "Creating persistent bash history directory" "green"
  mkdir -p /commandhistory
  touch /commandhistory/.bash_history
  chown -R "${USERNAME}" /commandhistory
}

cleanup() {
  log "Running comprehensive cleanup" "green"
  
  # Package manager cleanup (autoremove first, then clean)
  dnf autoremove -y
  dnf clean all
  
  # Clear package caches that might remain
  rm -rf /var/cache/dnf/*
  rm -rf /var/cache/yum/*
  
  # Clear log files
  rm -rf /var/log/*
  
  # Clear temporary directories
  rm -rf /tmp/*
  rm -rf /var/tmp/*
  
  # Clear source directories if they exist
  rm -rf /tmp/source
  
  # Clear any leftover installation files
  find /var -name "*.rpm" -delete 2>/dev/null || true
  
  log "Cleanup completed" "green"
}

main() {
  source "/usr/bin/lib/sh/log.sh"
  log "10-install-system-packages.sh" "blue"

  setup
  package_install
  install_dev_container_features
  add_bash_history_cache
  cleanup
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
