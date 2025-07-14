#!/bin/bash

log() {
  local message=${1:-}
  local color=${2:-"nc"}
  local level=${3:-"INFO"}

  # Define colors using an associative array
  declare -A colors=(
    ["red"]="\033[31m"
    ["yellow"]="\033[33m"
    ["green"]="\033[1;32m" # Bold green
    ["blue"]="\033[34m"
    ["cyan"]="\033[36m"
    ["gray"]="\033[30m"
    ["nc"]="\033[0m"
  )

  # Validate the color input
  if [[ -z "${colors[$color]}" ]]; then
    color="nc"
  fi

  # Get the current timestamp
  local timestamp
  timestamp=$(date '+%H:%M:%S')

  # Print the log message
  printf "%b%s %b%s: %s%b\n" "${colors["gray"]}" "[$timestamp]" "${colors[$color]}" "$level" "$message" "${colors["nc"]}"
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
