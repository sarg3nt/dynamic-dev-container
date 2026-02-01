#!/bin/bash
#
# This script will start the dev container outside of VSCode.
#
# cSpell:ignore sarg3nt 

set -euo pipefail
IFS=$'\n\t'

main() {
  local tag="${1:-latest}"

  # Name of the container
  local container_name="ghcr.io/sarg3nt/dynamic-dev-container:${tag}"

  # User being created in the container
  local container_user="vscode"

  # Use absolute path for bind mount (required on macOS)
  local current_dir
  current_dir="$(cd "$(pwd)" && pwd)"

  docker run --mount type=bind,source="${current_dir}",target=/workspaces/working \
    -w /workspaces/working -it --rm -u "${container_user}" \
    "${container_name}" zsh

}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
