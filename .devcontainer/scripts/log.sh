#!/bin/bash
# Must remain bash 3.2 compatible: this script is sourced by
# initialize_command.sh which runs on the host. macOS still ships bash 3.2
# as /bin/bash, so no associative arrays (`declare -A`).

_log_color_code() {
  case "$1" in
    red)    printf '\033[31m' ;;
    yellow) printf '\033[33m' ;;
    green)  printf '\033[1;32m' ;;
    blue)   printf '\033[34m' ;;
    cyan)   printf '\033[36m' ;;
    gray)   printf '\033[30m' ;;
    *)      printf '\033[0m'  ;;
  esac
}

log() {
  local message=${1:-}
  local color=${2:-nc}
  local level=${3:-INFO}

  local gray reset color_code timestamp
  gray=$(_log_color_code gray)
  reset=$(_log_color_code nc)
  color_code=$(_log_color_code "$color")
  timestamp=$(date '+%H:%M:%S')

  printf '%b%s %b%s: %s%b\n' "$gray" "[$timestamp]" "$color_code" "$level" "$message" "$reset"
}

log_warning() {
  log "$1" "yellow" "WARNING"
}

log_error() {
  log "$1" "red" "ERROR"
}

log_success() {
  log "$1" "green" "SUCCESS"
}

log_info() {
  log "$1" "blue" "INFO"
}

log_data() {
  log "$1" "cyan" "DATA"
}
