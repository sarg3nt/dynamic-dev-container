#!/bin/bash
#
# This script will start the dev container and open an interactive prompt into it.
#
# cSpell:ignore wslpath

set -euo pipefail
IFS=$'\n\t'

# User customizable variables - modify these as needed
docker_exec_command="gdc" # What quick two letter command do we want to use for this dev container / project. If empty, no command will be installed.
project_name="dynamic-dev-container" # Name of the project folder
container_name="dynamic-dev-container" # Name of the container
container_user="vscode" # User being created in the container

# Source colors library
source_colors() {
  # Define colors directly instead of sourcing external file
  # shellcheck disable=SC2034
  RED="\033[1;31m"
  YELLOW="\033[1;33m"
  GREEN="\033[1;32m"
  BLUE="\033[1;34m"
  # shellcheck disable=SC2034
  CYAN="\033[1;36m"
  NC="\033[0m"
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
  
  # Check if container exists and is running
  docker_id=$(docker container ls -f "name=${container_name}" -q)
  
  if [[ -z "$docker_id" ]]; then
    echo -ne "${YELLOW}Waiting up to 10 minutes for the dev container to start   ${NC}"
  fi

  while [[ -z "$docker_id" && $count -lt $max_wait ]]; do
    sleep 1
    docker_id=$(docker container ls -f "name=${container_name}" -q)
    count=$((count + 1))
    rot=$(( (rot + 1) % 4 ))
    echo -ne "\b${spin[$rot]}"
  done
  
  if [[ -z "$docker_id" ]]; then
    echo -ne "\r\033[K"  # Clear line and return to beginning
    echo -e "${RED}Timeout waiting for dev container to start.${NC}"
    exit 1
  fi
  
  echo -ne "\r\033[K"  # Clear line and return to beginning
  echo -e "${GREEN}Dev container started, execing into it.${NC}"
  
  if [[ -n "$docker_exec_command" ]]; then
    echo -e "${BLUE}You can use the \"${docker_exec_command}\" command to exec into the dev container from another terminal.${NC}"
  fi

  docker exec -u "${container_user}" -w "/workspaces/${project_name}" -it "${container_name}" zsh
}

# Clean up VS Code server processes
cleanup_vscode_processes() {
  # Kill VS Code server processes related to remote containers
  pkill -f "vscode-remote-containers" 2>/dev/null || true
  # Also kill any VS Code server processes that might be hanging around
  pkill -f "vscode-server.*node.*--dns-result-order" 2>/dev/null || true
  sleep 3
}

# Check if VS Code might be in an orphaned state
check_vscode_orphaned_state() {
  # Check if VS Code server with remote containers extension is running
  local vscode_remote_containers_processes
  vscode_remote_containers_processes=$(pgrep -f "vscode-remote-containers" 2>/dev/null || true)
  
  # Check if container exists
  local docker_id
  docker_id=$(docker container ls -f "name=${container_name}" -q)
  
  # If VS Code remote containers processes are running but container doesn't exist
  if [[ -n "$vscode_remote_containers_processes" && -z "$docker_id" ]]; then
    echo -e "${YELLOW}Warning: VS Code appears to be running with remote containers extension, but the container '${container_name}' doesn't exist.${NC}"
    echo -e "${YELLOW}This usually happens when the container was manually removed while VS Code was still connected.${NC}"
    echo ""
    
    # Show the orphaned processes for debugging
    echo -e "${YELLOW}Found these VS Code remote container processes:${NC}"
    ps -f -p ${vscode_remote_containers_processes} 2>/dev/null || true
    echo ""
    
    echo -e "${YELLOW}Options:${NC}"
    echo -e "${YELLOW}1. Close VS Code windows manually on Windows and run this script again${NC}"
    echo -e "${YELLOW}2. Clean up server processes and continue. VS Code will display a dialog asking if you want to \"Reload Window\" or \"Cancel\", select \"Reload Window\"${NC}"
    echo ""
    
    read -r -p "Choose option [1/2]: " response
    
    case "$response" in
      1)
        echo -e "${BLUE}Please close VS Code windows on Windows and run this script again.${NC}"
        exit 0
        ;;
      2|*)
        if [[ "$response" == "2" ]]; then
          echo -e "${BLUE}Cleaning up server processes...${NC}"
        else
          echo "Invalid response. Cleaning up server processes..."
        fi
        cleanup_vscode_processes
        return 0  # Start fresh
        ;;
    esac
  fi
  
  return 1  # No orphaned state detected
}

# Main function
main() {
  local force_restart=false
  
  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --force|--restart|-f)
        force_restart=true
        shift
        ;;
      --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --force, --restart, -f    Force restart by removing container and cleaning server processes"
        echo "                           (Note: VS Code windows on Windows need to be closed manually)"
        echo "  --help, -h                Show this help message"
        echo ""
        echo "This script manages a VS Code dev container in WSL. When the container is manually"
        echo "removed while VS Code is connected, use --force to clean up and start fresh."
        exit 0
        ;;
      *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
  done
  
  source_colors
  add_docker_exec_command

  # Check if the dev container is already running
  local docker_id
  docker_id=$(docker container ls -f "name=${container_name}" -q)
  
  if [[ "$force_restart" == true ]]; then
    echo -e "${BLUE}Force restart requested.${NC}"
    echo -e "${YELLOW}Note: You may need to manually close VS Code windows on Windows.${NC}"
    echo -e "${BLUE}Cleaning up any existing container and server processes...${NC}"
    
    # Remove existing container if it exists
    if docker container ls -a -f "name=${container_name}" -q | grep -q .; then
      echo -e "${BLUE}Removing existing container '${container_name}'...${NC}"
      docker rm -f "${container_name}" 2>/dev/null || true
    fi
    
    # Clean up any lingering server processes
    cleanup_vscode_processes
    
    echo -e "${BLUE}Starting VS Code with fresh container...${NC}"
    open_vs_code
  elif [[ -n "$docker_id" ]]; then
    echo -e "${GREEN}Dev container '${container_name}' is already running.${NC}"
    echo -e "${BLUE}Connecting to existing container...${NC}"
  else
    # Check for orphaned VS Code state and handle it
    if check_vscode_orphaned_state; then
      echo -e "${BLUE}Starting VS Code fresh after cleanup...${NC}"
      open_vs_code
    else
      echo -e "${BLUE}Dev container '${container_name}' not found. Starting VS Code...${NC}"
      open_vs_code
    fi
  fi

  exec_into_container
}

# Run main if script is executed directly
if ! (return 0 2>/dev/null); then
  main "$@"
fi
