#!/bin/bash

set -euo pipefail
IFS=$'\n\t'

# cSpell:ignore ncdu, epel, buildx, socat, devel, btop, iputils, nmap snmp

# Install system packages
setup() {
  log "Adding install_weak_deps=False to /etc/dnf/dnf.conf" "green"
  echo "install_weak_deps=False" >>/etc/dnf/dnf.conf

  log "Installing epel release" "green"
  dnf install -y epel-release && dnf clean all

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
  log "Installing bash completion" "green"
  dnf install -y bash-completion

  log "Installing ca-certificates" "green"
  dnf install -y ca-certificates

  log "Installin docker-ce-cli" "green"
  dnf install -y docker-ce-cli

  log "Installing docker-buildx-plugin" "green"
  dnf install -y docker-buildx-plugin

  log "Installing git" "green"
  dnf install -y git

  log "Installing gnupg2" "green"
  dnf install -y gnupg2

  log "Installing jq" "green"
  dnf install -y jq

  log "Installing util-linux-user" "green"
  dnf install -y util-linux-user

  log "Installing xz" "green"
  dnf install -y xz
  
  # Final cleanup after all packages
  log "Final package cache cleanup" "green"
  dnf clean all
}

install_dev_container_features() {
  log "Installing Microsoft Dev Container Features" "green"

  cd /tmp/
  log "Cloning devcontainers features repository" "green"
  git clone --depth 1 -- https://github.com/devcontainers/features.git

  log "Running install script" "green"
  cd /tmp/features/src/common-utils/
  ./install.sh
}

cleanup() {
  log "Running comprehensive cleanup" "green"
  
  # Package manager cleanup
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
  cleanup
}

# Run main
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
