#!/bin/bash
#
# This script will start the dev container and open an interactive prompt into it.
#
# cSpell:ignore

set -euo pipefail
IFS=$'\n\t'

# What quick two letter command do we want to use for this dev container / project.
# If this is empty, no command will be installed.
# Example: qq
docker_exec_command=""
# Name of the project folder
project_name="generic-dev-container"
# Name of the container
container_name="${project_name}"
# User being created in the container
container_user="vscode"

colors_sourced=false
# shellcheck source=/dev/null
if [ -f "usr/bin/lib/sh/colors.sh" ]; then
  source "usr/bin/lib/sh/colors.sh"
  colors_sourced=true
fi
# shellcheck source=/dev/null
if [ -f "lib/sh/colors.sh" ]; then
  source "lib/sh/colors.sh"
  colors_sourced=true
fi

if [ "$colors_sourced" = false ]; then
  echo "Error: colors.sh not found. Please ensure it is availing in either the usr/bin/lib/sh or lib/sh directory."
  exit 1
fi

add_docker_exec_command() {
  if [[ -n "$docker_exec_command" ]] && [ -f "${HOME}/.zshrc" ] && ! grep -F "${docker_exec_command} ()" "${HOME}/.zshrc" >/dev/null 2>&1; then
    echo -e "\n${docker_exec_command} (){\n\
      docker exec -it -u ${container_user} -w /workspaces/${project_name} ${container_name} zsh\n\
    }" >>"${HOME}/.zshrc"
    echo -e "${GREEN}Created \"${docker_exec_command}\" command in your ${HOME}/.zshrc file.${NC}"

    # Source .zshrc in a subshell to retain current environment variables
    zsh -c "source '${HOME}/.zshrc'"
  fi
}

open_vs_code() {
  # check for dependencies
  if ! command -v xxd &>/dev/null; then
    echo "xxd command not found, install with"
    echo "sudo apt install xxd"
    exit 1
  fi

  DEVCONTAINER_JSON="$PWD/.devcontainer/devcontainer.json"
  CODE_WS_FILE="$PWD/workspace.code-workspace"

  if [ ! -f "$DEVCONTAINER_JSON" ]; then
    # open code without container
    if [ -f "$CODE_WS_FILE" ]; then
      echo "Opening vscode workspace from $CODE_WS_FILE"
      code $CODE_WS_FILE
    else
      echo "Opening vscode in current directory"
      code .
    fi
    exit 0
  fi

  # open devcontainer
  HOST_PATH=$(echo $(wslpath -w $PWD) | sed -e 's,\\,\\\\,g')
  WORKSPACE="/workspaces/$(basename $PWD)"

  URI_SUFFIX=
  if [ -f "$CODE_WS_FILE" ]; then
    # open workspace file
    URI_TYPE="--file-uri"
    URI_SUFFIX="$WORKSPACE/$(basename $CODE_WS_FILE)"
    echo "Opening vscode workspace file within devcontainer"
  else
    URI_TYPE="--folder-uri"
    URI_SUFFIX="$WORKSPACE"
    echo "Opening vscode within devcontainer"
  fi

  URI="{\"hostPath\":\"$HOST_PATH\",\"configFile\":{\"\$mid\":1,\"path\":\"$DEVCONTAINER_JSON\",\"scheme\":\"vscode-fileHost\"}}"
  URI_HEX=$(echo "${URI}" | xxd -c 0 -p)
  code ${URI_TYPE}="vscode-remote://dev-container%2B${URI_HEX}${URI_SUFFIX}" &
}

exec_into_container() {
  # Here we check if the dev container has started yet.
  # Wait a max of 600 seconds (10 minutes).
  local max_wait=600
  local count=0
  local spin=("-" "\\" "|" "/")
  local rot=0
  # If not then docker_id will be empty and the while loop kicks in.
  local docker_id=""
  docker_id=$(docker container ls -f name=${container_name} -q)
  if [ -z "$docker_id" ]; then
    echo -e "${BLUE}Waiting up to 10 minutes for the dev container to start ${NO_NEW_LINE}"
  fi

  while [ -z "$docker_id" ] && ((count < max_wait)); do
    # Sleep for one second then try and get the docker_id of the dev container again.
    # Once we can get the id, the loop quits and we run the last line below, exe'ing into the container.
    sleep 1s
    docker_id=$(docker container ls -f name=${container_name} -q)
    count=$((count + 1))

    if ((count == 20)); then
      echo -ne "\b"
      echo -e "${YELLOW}The dev container is taking a while to start, VS Code could be downloading a new version or you may need to manually open it from within VS Code.${BLUE}"
    fi

    if ((count >= max_wait)); then
      exit 0
    fi
    echo -ne "\b${spin[$rot]}"
    if ((rot >= 3)); then
      rot=0
    else
      rot=$((rot + 1))
    fi
  done
  echo -ne "\b"
  echo -e "${GREEN}Dev container started, execing into it.${NC}"
  if [[ -n "$docker_exec_command" ]]; then
    echo -e "${BLUE}You can use the \"${docker_exec_command}\" command to exec into the dev container from another terminal.${NC}"
  fi
  
  docker exec -u "${container_user}" -w /workspaces/${project_name} -it ${container_name} zsh
}

# Check if user is using Docker Deskop for Windows or the native Docker Engine.
main() {
  add_docker_exec_command

  # If the dev container is running, we assume VSCode is also running. If VSCode is not running, then open it.
  if ! docker ps | grep ${container_name}; then
    open_vs_code
  fi

  exec_into_container
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
