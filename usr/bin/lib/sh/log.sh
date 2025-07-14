#!/bin/bash
#
# This is a library function to log to a provided log file.
# example usage:
# source "lib/sh/log.sh"
# log "my message" "green"
#

# shellcheck disable=SC2034
log() {
  local message=${1:-}

  # if no color is passed then set color to nc
  local color=${2:-"nc"}

  local red="\033[1;31m"
  local yellow="\033[1;33m"
  local green="\033[1;32m"
  local blue="\033[1;34m"
  local cyan="\033[1;36m"
  local gray="\033[1;30m"
  local nc="\033[0m"
  local dt=""
  dt=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "${gray}${dt}${nc} ${!color}${message}${nc}"
}
