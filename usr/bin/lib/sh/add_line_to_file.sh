#!/bin/bash
#
# This is a library function to add a line to a file if it does not exist.
# example usage:
# source "add_line_to_file"
# add_line_to_file "file" "line"
#

# shellcheck disable=SC2034
add_line_to_file() {
  local file="${1-}"
  local line="${2-}"
  if [[ -f "$file" ]]; then
    if [[ $(type -t log) == function ]]; then
      log "  Adding line ${line} to file ${file}" "cyan"
    fi
    grep -qF -- "$line" "$file" || echo -e "$line" >>"$file"
  else
    if [[ $(type -t log) == function ]]; then
      log "  Creating new file ${file} with line ${line}" "cyan"
    fi
    echo -e "$line" >"$file"
  fi
}
