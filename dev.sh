#!/bin/bash
#
# This script will start the dev container and open an interactive prompt into it.
#
# cSpell:ignore wslpath

set -euo pipefail
IFS=$'\n\t'

# User customizable variables - modify these as needed
docker_exec_command="gdc" # What quick two letter command do we want to use for this dev container / project. If empty, no command will be installed.
project_name="generic-dev-container" # Name of the project folder
container_name="generic-dev-container" # Name of the container
container_user="vscode" # User being created in the container

# Source colors library
source_colors() {
  local colors_paths=("usr/bin/lib/sh/colors.sh" "lib/sh/colors.sh")
  
  for path in "${colors_paths[@]}"; do
    if [[ -f "$path" ]]; then
      # shellcheck source=/dev/null
      source "$path"
      return 0
    fi
  done
  
  echo "Error: colors.sh not found. Please ensure it is available in either the usr/bin/lib/sh or lib/sh directory."
  exit 1
}

# Add docker exec command to user's .zshrc
add_docker_exec_command() {
  [[ -z "$docker_exec_command" || ! -f "${HOME}/.zshrc" ]] && return 0
  
  # Check if command already exists
  if grep -qF "${docker_exec_command} ()" "${HOME}/.zshrc" 2>/dev/null; then
    return 0
  fi

  cat >> "${HOME}/.zshrc" << EOF

${docker_exec_command} (){
  docker exec -it -u "${container_user}" -w "/workspaces/${project_name}" "${container_name}" zsh
}
EOF
  
  echo -e "${GREEN}Created \"${docker_exec_command}\" command in your ${HOME}/.zshrc file.${NC}"
  
  # Source .zshrc in a subshell to retain current environment variables
  zsh -c "source '${HOME}/.zshrc'" 2>/dev/null || true
}

# Check for required dependencies
check_dependencies() {
  if ! command -v xxd >/dev/null 2>&1; then
    echo "xxd command not found."
    
    # Detect OS type
    local os_type=""
    local install_cmd=""
    
    if command -v apt >/dev/null 2>&1; then
      os_type="debian"
      install_cmd="sudo apt update && sudo apt install -y xxd"
    elif command -v dnf >/dev/null 2>&1; then
      os_type="rhel"
      install_cmd="sudo dnf install -y vim-common"
    elif command -v yum >/dev/null 2>&1; then
      os_type="rhel"
      install_cmd="sudo yum install -y vim-common"
    else
      echo "Error: Unable to detect package manager (apt/dnf/yum)."
      echo "Please install xxd manually and try again."
      exit 1
    fi
    
    echo "Detected ${os_type}-based system."
    read -r -p "Would you like to install xxd now? [Y/n]: " response
    response=${response:-Y}  # Default to Y if empty
    
    case "$response" in
      [yY]|[yY][eE][sS])
        echo "Installing xxd..."
        if eval "$install_cmd"; then
          echo "xxd installed successfully."
        else
          echo "Error: Failed to install xxd."
          exit 1
        fi
        ;;
      [nN]|[nN][oO])
        echo "Error: xxd is required for this script to work."
        echo "Please install it manually using: $install_cmd"
        exit 1
        ;;
      *)
        echo "Invalid response. Please answer Y or n."
        exit 1
        ;;
    esac
  fi
}

# Open VS Code with devcontainer support
open_vs_code() {
  check_dependencies
  
  local devcontainer_json="$PWD/.devcontainer/devcontainer.json"
  local code_ws_file="$PWD/workspace.code-workspace"

  # If no devcontainer config, open code normally
  if [[ ! -f "$devcontainer_json" ]]; then
    if [[ -f "$code_ws_file" ]]; then
      echo "Opening vscode workspace from $code_ws_file"
      code "$code_ws_file"
    else
      echo "Opening vscode in current directory"
      code .
    fi
    exit 0
  fi

  # Open devcontainer
  local host_path workspace uri_type uri_suffix uri uri_hex
  host_path=$(wslpath -w "$PWD" | sed 's,\\,\\\\,g')
  workspace="/workspaces/$(basename "$PWD")"

  if [[ -f "$code_ws_file" ]]; then
    # Open workspace file
    uri_type="--file-uri"
    uri_suffix="$workspace/$(basename "$code_ws_file")"
    echo "Opening vscode workspace file within devcontainer"
  else
    uri_type="--folder-uri"
    uri_suffix="$workspace"
    echo "Opening vscode within devcontainer"
  fi

  uri="{\"hostPath\":\"$host_path\",\"configFile\":{\"\$mid\":1,\"path\":\"$devcontainer_json\",\"scheme\":\"vscode-fileHost\"}}"
  uri_hex=$(printf '%s' "$uri" | xxd -c 0 -p)
  echo "Launching VS Code in background..."
  code "${uri_type}=vscode-remote://dev-container%2B${uri_hex}${uri_suffix}" &
  code_pid=$!
  echo "VS Code launched with PID: $code_pid"
  
  # Give VS Code more time to process the command and start the container
  echo "Waiting for VS Code to start the container..."
  sleep 10
}

# Wait for container to start and exec into it
exec_into_container() {
  local -r max_wait=600
  local -r spin=("-" "\\" "|" "/")
  local count=0 rot=0 docker_id
  
  docker_id=$(docker container ls -f "name=${container_name}" -q)
  
  if [[ -z "$docker_id" ]]; then
    echo -e "${BLUE}Waiting up to 10 minutes for the dev container to start ${NO_NEW_LINE}"
  fi

  while [[ -z "$docker_id" && $count -lt $max_wait ]]; do
    sleep 1
    docker_id=$(docker container ls -f "name=${container_name}" -q)
    ((count++))

    if ((count == 20)); then
      echo -ne "\b"
      echo -e "${YELLOW}The dev container is taking a while to start, VS Code could be downloading a new version or you may need to manually open it from within VS Code.${BLUE}"
    fi
    
    echo -ne "\b${spin[$rot]}"
    rot=$(( (rot + 1) % 4 ))
  done
  
  if [[ -z "$docker_id" ]]; then
    echo -e "\b${RED}Timeout waiting for dev container to start.${NC}"
    exit 1
  fi
  
  echo -ne "\b"
  echo -e "${GREEN}Dev container started, execing into it.${NC}"
  
  if [[ -n "$docker_exec_command" ]]; then
    echo -e "${BLUE}You can use the \"${docker_exec_command}\" command to exec into the dev container from another terminal.${NC}"
  fi

  docker exec -u "${container_user}" -w "/workspaces/${project_name}" -it "${container_name}" zsh
}

# Main function
main() {
  source_colors
  add_docker_exec_command

  # If the dev container is not running, open VS Code
  if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
    open_vs_code
  fi

  exec_into_container
}

# Run main if script is executed directly
if ! (return 0 2>/dev/null); then
  main "$@"
fi
