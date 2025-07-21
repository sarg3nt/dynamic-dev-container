#!/bin/bash
#
# Installs .devcontainer and other files into a project directory to use the dev container in a new project.
# cspell:ignore openbao myapp sudermanjr kubens

set -euo pipefail
IFS=$'\n\t'

# Global decision tracking variables
INSTALL_OPENTOFU=false
INSTALL_KUBERNETES=false
INSTALL_GO=false
INSTALL_DOTNET=false
INSTALL_JAVASCRIPT=false
INSTALL_PACKER=false
INSTALL_POWERSHELL=false
INCLUDE_PYTHON_EXTENSIONS=false
INCLUDE_MARKDOWN_EXTENSIONS=false
INCLUDE_SHELL_EXTENSIONS=false
INCLUDE_JS_EXTENSIONS=false

# Individual tool flags (default false)
INSTALL_OPENBAO=false
INSTALL_KUBECTL=false
INSTALL_KUBECTX=false
INSTALL_KUBENS=false
INSTALL_K9S=false
INSTALL_HELM=false
INSTALL_KREW=false
INSTALL_DIVE=false
INSTALL_KUBEBENCH=false
INSTALL_POPEYE=false
INSTALL_TRIVY=false
INSTALL_CMCTL=false
INSTALL_K3D=false
INSTALL_GOLANG=false
INSTALL_GORELEASER=false
INSTALL_DOTNET_SDK=false
INSTALL_NODE=false
INSTALL_PNPM=false
INSTALL_YARN=false
INSTALL_DENO=false
INSTALL_BUN=false
INSTALL_GITUI=false
INSTALL_TEALDEER=false
INSTALL_MICRO=false

# Version variables for tools
GOLANG_VERSION="latest"
DOTNET_SDK_VERSION="latest"
KUBECTL_VERSION="latest"
OPENBAO_VERSION="latest"
OPENTOFU_VERSION="latest"
PACKER_VERSION="latest"

# Source colors library
source_colors() {
  # Define colors directly instead of sourcing external file
  # shellcheck disable=SC2034
  RED="\033[1;31m"
  YELLOW="\033[1;33m"
  GREEN="\033[1;32m"
  BLUE="\033[1;34m"
  CYAN="\033[1;36m"
  NC="\033[0m"
  # shellcheck disable=SC2034
  NO_NEW_LINE='\033[0K\r'
}

# Ask yes/no question
ask_yes_no() {
  local question="$1"
  local default="${2:-}"  # Optional default parameter
  local prompt_suffix="(y/n)"
  local default_response=""
  
  # Set prompt and default based on parameter
  if [[ "$default" == "n" || "$default" == "N" ]]; then
    prompt_suffix="(y/N)"
    default_response="n"
  elif [[ "$default" == "y" || "$default" == "Y" ]]; then
    prompt_suffix="(Y/n)"
    default_response="y"
  fi
  
  local response
  while true; do
    read -r -p "$(echo -e "${CYAN}${question} ${prompt_suffix}: ${NC}")" response
    
    # Use default if response is empty
    if [[ -z "$response" && -n "$default_response" ]]; then
      response="$default_response"
    fi
    
    case "$response" in
      [yY]|[yY][eE][sS]) return 0 ;;
      [nN]|[nN][oO]) return 1 ;;
      *) echo -e "${YELLOW}Please answer y or n.${NC}" ;;
    esac
  done
}

# Ask for user input with default value
ask_with_default() {
  local prompt="$1"
  local default="$2"
  local response
  read -r -p "$(echo -e "${CYAN}${prompt} [${default}]: ${NC}")" response
  echo "${response:-$default}"
}

# Ask for user input (required)
ask_required() {
  local prompt="$1"
  local response
  while true; do
    read -r -p "$(echo -e "${CYAN}${prompt}: ${NC}")" response
    if [[ -n "$response" ]]; then
      echo "$response"
      return
    fi
    echo -e "${YELLOW}This field is required. Please enter a value.${NC}"
  done
}

# Create project directory if it doesn't exist
create_project_directory() {
  local project_path="$1"
  
  if [[ ! -d "${project_path}" ]]; then
    echo -e "${YELLOW}The path '${project_path}' does not exist.${NC}"
    local response
    read -r -p "$(echo -e "${CYAN}Would you like to create it? (Y/n): ${NC}")" response
    response=${response:-Y}  # Default to Y if empty
    case "$response" in
      [yY]|[yY][eE][sS])
        echo -e "${BLUE}Creating directory: ${project_path}${NC}"
        mkdir -p "${project_path}"
        ;;
      [nN]|[nN][oO])
        echo -e "${RED}Aborting installation.${NC}"
        exit 1
        ;;
      *)
        echo -e "${YELLOW}Invalid response. Please answer Y or n.${NC}"
        create_project_directory "$project_path"  # Recursively ask again
        ;;
    esac
  fi
}

# Extract sections from .mise.toml
extract_mise_section() {
  local start_marker="$1"
  local end_marker="$2"
  local file=".mise.toml"
  
  awk "/${start_marker}/,/${end_marker}/" "$file"
}

# Extract sections from devcontainer.json
extract_devcontainer_section() {
  local start_marker="$1"
  local end_marker="$2"
  local file=".devcontainer/devcontainer.json"
  
  # Escape forward slashes for awk pattern matching
  local escaped_start_marker="${start_marker//\//\\/}"
  local escaped_end_marker="${end_marker//\//\\/}"
  
  awk "/${escaped_start_marker}/,/${escaped_end_marker}/" "$file"
}

# Generate custom .mise.toml
generate_mise_toml() {
  local project_path="$1"
  local temp_file="${project_path}/.mise.toml.tmp"
  
  # Start with the header and environment section from source
  echo "# cspell:ignore cmctl gitui krew kubebench kubectx kubens direnv dotenv looztra kompiro kforsthoevel sarg kubeseal stefansedich nlamirault zufardhiyaulhaq sudermanjr" > "$temp_file"
  # shellcheck disable=SC2129
  extract_mise_section "#### Begin Environment ####" "#### End Environment ####" >> "$temp_file"
  echo "" >> "$temp_file"
  echo "[tools]" >> "$temp_file"
  echo "" >> "$temp_file"

  # HashiCorp tools
  if [ "$INSTALL_OPENTOFU" = true ]; then
    echo "opentofu = \"${OPENTOFU_VERSION}\"" >> "$temp_file"
  fi
  if [ "$INSTALL_OPENBAO" = true ]; then
    echo "openbao = \"${OPENBAO_VERSION}\"" >> "$temp_file"
  fi
  if [ "$INSTALL_PACKER" = true ]; then
    echo "packer = \"${PACKER_VERSION}\"" >> "$temp_file"
  fi

  # Go
  if [ "$INSTALL_GOLANG" = true ] || [ "$INSTALL_GORELEASER" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin Go Development ####" >> "$temp_file"
    [ "$INSTALL_GOLANG" = true ] && echo "golang = \"${GOLANG_VERSION}\"" >> "$temp_file"
    [ "$INSTALL_GORELEASER" = true ] && echo 'goreleaser = "latest"' >> "$temp_file"
    echo "#### End Go Development ####" >> "$temp_file"
  fi

  # .NET
  if [ "$INSTALL_DOTNET_SDK" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin .NET Development ####" >> "$temp_file"
    echo "dotnet = \"${DOTNET_SDK_VERSION}\"" >> "$temp_file"
    echo "#### End .NET Development ####" >> "$temp_file"
  fi

  # JavaScript/Node
  if [ "$INSTALL_NODE" = true ] || [ "$INSTALL_PNPM" = true ] || [ "$INSTALL_YARN" = true ] || [ "$INSTALL_DENO" = true ] || [ "$INSTALL_BUN" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin JavaScript/Node.js Development ####" >> "$temp_file"
    [ "$INSTALL_NODE" = true ] && echo 'node = "19"' >> "$temp_file"
    [ "$INSTALL_PNPM" = true ] && echo 'pnpm = "latest"' >> "$temp_file"
    [ "$INSTALL_YARN" = true ] && echo 'yarn = "latest"' >> "$temp_file"
    [ "$INSTALL_DENO" = true ] && echo 'deno = "latest"' >> "$temp_file"
    [ "$INSTALL_BUN" = true ] && echo 'bun = "latest"' >> "$temp_file"
    echo "#### End JavaScript/Node.js Development ####" >> "$temp_file"
  fi

  # Kubernetes/Helm
  if [ "$INSTALL_KUBECTL" = true ] || [ "$INSTALL_KUBECTX" = true ] || [ "$INSTALL_KUBENS" = true ] || [ "$INSTALL_K9S" = true ] || [ "$INSTALL_HELM" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin Kubernetes/Helm ####" >> "$temp_file"
    [ "$INSTALL_KUBECTL" = true ] && echo "kubectl = \"${KUBECTL_VERSION}\"" >> "$temp_file"
    [ "$INSTALL_KUBECTX" = true ] && echo 'kubectx = "latest"' >> "$temp_file"
    [ "$INSTALL_KUBENS" = true ] && echo 'kubens = "latest"' >> "$temp_file"
    [ "$INSTALL_K9S" = true ] && echo 'k9s = "latest"' >> "$temp_file"
    [ "$INSTALL_HELM" = true ] && echo 'helm = "latest"' >> "$temp_file"
    echo "#### End Kubernetes/Helm ####" >> "$temp_file"
  fi

  # Kubernetes Utilities
  if [ "$INSTALL_KREW" = true ] || [ "$INSTALL_DIVE" = true ] || [ "$INSTALL_KUBEBENCH" = true ] || [ "$INSTALL_POPEYE" = true ] || [ "$INSTALL_TRIVY" = true ] || [ "$INSTALL_CMCTL" = true ] || [ "$INSTALL_K3D" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin Kubernetes Utilities ####" >> "$temp_file"
    [ "$INSTALL_KREW" = true ] && echo 'krew = "latest"' >> "$temp_file"
    [ "$INSTALL_DIVE" = true ] && echo 'dive = "latest"' >> "$temp_file"
    [ "$INSTALL_KUBEBENCH" = true ] && echo 'kubebench = "latest"' >> "$temp_file"
    [ "$INSTALL_POPEYE" = true ] && echo 'popeye = "latest"' >> "$temp_file"
    [ "$INSTALL_TRIVY" = true ] && echo 'trivy = "latest"' >> "$temp_file"
    [ "$INSTALL_CMCTL" = true ] && echo 'cmctl = "latest"' >> "$temp_file"
    [ "$INSTALL_K3D" = true ] && echo 'k3d = "latest"' >> "$temp_file"
    echo "#### End Kubernetes Utilities ####" >> "$temp_file"
  fi

  # Miscellaneous
  [ "$INSTALL_GITUI" = true ] && echo 'gitui = "latest"' >> "$temp_file"
  [ "$INSTALL_TEALDEER" = true ] && echo 'tealdeer = "latest"' >> "$temp_file"
  [ "$INSTALL_MICRO" = true ] && echo 'micro = "latest"' >> "$temp_file"
  [ "$INSTALL_POWERSHELL" = true ] && echo 'powershell = "latest"' >> "$temp_file"

  # Add aliases and settings sections from source
  # shellcheck disable=SC2129
  echo "" >> "$temp_file"
  extract_mise_section "#### Begin Aliases ####" "#### End Aliases ####" >> "$temp_file"
  echo "" >> "$temp_file"
  extract_mise_section "#### Begin Settings ####" "#### End Settings ####" >> "$temp_file"

  mv "$temp_file" "${project_path}/.mise.toml"
}

# Update dev.sh with project settings
update_dev_sh() {
  local project_path="$1"
  local docker_exec_command="$2"
  local project_name="$3"
  local container_name="$4"
  local temp_file="${project_path}/dev.sh.tmp"
  
  # Copy dev.sh and update the variables
  cp "dev.sh" "$temp_file"
  
  # Update the variables at the top of the file
  sed -i "s/docker_exec_command=\"[^\"]*\"/docker_exec_command=\"${docker_exec_command}\"/" "$temp_file"
  sed -i "s/project_name=\"[^\"]*\"/project_name=\"${project_name}\"/" "$temp_file"
  sed -i "s/container_name=\"[^\"]*\"/container_name=\"${container_name}\"/" "$temp_file"
  
  mv "$temp_file" "${project_path}/dev.sh"
  chmod +x "${project_path}/dev.sh"
}

# Generate custom devcontainer.json
generate_devcontainer_json() {
  local project_path="$1"
  local project_name="$2"
  local container_name="$3"
  local display_name="$4"
  local temp_file="${project_path}/.devcontainer/devcontainer.json.tmp"
  
  echo ""
  echo -e "${BLUE}Configuring devcontainer.json plugins and settings:${NC}"
  
  # Read the base devcontainer.json up to extensions
  awk '/^      "extensions": \[/,/^      \],$/{if(/^      "extensions": \[/) print; else if(/^      \],$/) exit; else next} !/^      "extensions": \[/' .devcontainer/devcontainer.json | head -n -1 > "$temp_file"
  
  # Update the name and runArgs in the temp file
  sed -i "s/\"name\": \"[^\"]*\"/\"name\": \"${display_name}\"/" "$temp_file"
  sed -i "s/--name=dynamic-dev-container/--name=${container_name}/g" "$temp_file"
  sed -i "s/dynamic-dev-container-shellhistory/${container_name}-shellhistory/g" "$temp_file"
  sed -i "s/dynamic-dev-container-plugins/${container_name}-plugins/g" "$temp_file"
  
  # Start extensions array
  echo '      "extensions": [' >> "$temp_file"
  
  # Always include GitHub extensions
  extract_devcontainer_section "// #### Begin Github ####" "// #### End Github ####" | grep -E '^\s*".*",' >> "$temp_file"
  
  # Include Go extensions if Go was installed
  if [ "$INSTALL_GO" = true ]; then
    echo -e "${GREEN}✓ Including Go development extensions (Go tools were installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Go ####" "// #### End Go ####" >> "$temp_file"
  fi
  
  # Include .NET extensions if .NET was installed
  if [ "$INSTALL_DOTNET" = true ]; then
    echo -e "${GREEN}✓ Including .NET development extensions (.NET tools were installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin .NET ####" "// #### End .NET ####" >> "$temp_file"
  fi
  
  # Include JavaScript/Node.js extensions if JavaScript tools were installed
  if [ "$INSTALL_JAVASCRIPT" = true ]; then
    echo -e "${GREEN}✓ Including JavaScript/Node.js development extensions (Node.js tools were installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/Node.js ####" "// #### End JavaScript/Node.js ####" >> "$temp_file"
  fi
  
  # Ask about Python extensions (no corresponding tool installation)
  if ask_yes_no "Include Python development extensions?" "Y"; then
    INCLUDE_PYTHON_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Python ####" "// #### End Python ####" >> "$temp_file"
  fi
  
  # Ask about Markdown extensions (no corresponding tool installation)
  if ask_yes_no "Include Markdown editing extensions?" "Y"; then
    INCLUDE_MARKDOWN_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Markdown ####" "// #### End Markdown ####" >> "$temp_file"
  fi
  
  # Ask about Shell/Bash extensions (always useful, no specific tool)
  if ask_yes_no "Include Shell/Bash development extensions?" "Y"; then
    INCLUDE_SHELL_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Shell/Bash ####" "// #### End Shell/Bash ####" >> "$temp_file"
  fi
  
  # Include Kubernetes extensions if any Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ] || [ "$INSTALL_KREW" = true ]; then
    echo -e "${GREEN}✓ Including Kubernetes/Helm extensions (Kubernetes tools were installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Kubernetes/Helm ####" "// #### End Kubernetes/Helm ####" >> "$temp_file"
  fi
  
  # Include Terraform/OpenTofu extensions if OpenTofu was installed
  if [ "$INSTALL_OPENTOFU" = true ]; then
    echo -e "${GREEN}✓ Including Terraform/OpenTofu extensions (OpenTofu was installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Terraform/OpenTofu ####" "// #### End Terraform/OpenTofu ####" >> "$temp_file"
  fi
  
  # Include JavaScript/TypeScript extensions if Node.js was installed
  if [ "$INSTALL_NODE" = true ]; then
    INCLUDE_JS_EXTENSIONS=true
    echo -e "${GREEN}✓ Including JavaScript/TypeScript development extensions (Node.js was installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript ####" "// #### End JavaScript/TypeScript ####" >> "$temp_file"
  fi
  
  # Include Packer extensions if Packer was installed
  if [ "$INSTALL_PACKER" = true ]; then
    echo -e "${GREEN}✓ Including Packer extensions (Packer was installed)${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Packer ####" "// #### End Packer ####" >> "$temp_file"
  fi
  
  # Always include Core Extensions
  # shellcheck disable=SC2129
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin Core Extensions ####" "// #### End Core Extensions ####" >> "$temp_file"
  
  # Close extensions array and add settings
  echo "      ]," >> "$temp_file"
  
  # Add settings section
  echo '      "settings": {' >> "$temp_file"
  
  # Always include Core VS Code Settings
  extract_devcontainer_section "// #### Begin Core VS Code Settings ####" "// #### End Core VS Code Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  echo "," >> "$temp_file"
  
  # Add settings based on user choices (automatically include for installed tools)
  echo -e "${BLUE}Now configuring VS Code settings...${NC}"
  
  # Include Go settings if Go was installed
  if [ "$INSTALL_GO" = true ]; then
    echo -e "${GREEN}✓ Including Go language settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Go Settings ####" "// #### End Go Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include .NET settings if .NET was installed
  if [ "$INSTALL_DOTNET" = true ]; then
    echo -e "${GREEN}✓ Including .NET language settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin .NET Settings ####" "// #### End .NET Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include JavaScript/Node.js settings if JavaScript tools were installed
  if [ "$INSTALL_JAVASCRIPT" = true ]; then
    echo -e "${GREEN}✓ Including JavaScript/Node.js language settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/Node.js Settings ####" "// #### End JavaScript/Node.js Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Python settings if Python extensions were selected
  if [ "$INCLUDE_PYTHON_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Python language settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Python Settings ####" "// #### End Python Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Markdown settings if Markdown extensions were selected
  if [ "$INCLUDE_MARKDOWN_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Markdown settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Markdown Settings ####" "// #### End Markdown Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Shell/Bash settings if Shell extensions were selected
  if [ "$INCLUDE_SHELL_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Shell/Bash settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Shell/Bash Settings ####" "// #### End Shell/Bash Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Kubernetes settings if any Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ] || [ "$INSTALL_KREW" = true ]; then
    echo -e "${GREEN}✓ Including Kubernetes/Helm settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Kubernetes/Helm Settings ####" "// #### End Kubernetes/Helm Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include JavaScript/TypeScript settings if JS extensions were selected
  if [ "$INCLUDE_JS_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including JavaScript/TypeScript settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript Settings ####" "// #### End JavaScript/TypeScript Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include PowerShell settings if PowerShell was installed
  if [ "$INSTALL_POWERSHELL" = true ]; then
    echo -e "${GREEN}✓ Including PowerShell settings${NC}"
    # shellcheck disable=SC2129
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin PowerShell Settings ####" "// #### End PowerShell Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Always include Spell Checker, TODO Tree, and PSI Header settings
  # shellcheck disable=SC2129
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin Spell Checker Settings ####" "// #### End Spell Checker Settings ####" >> "$temp_file"
  echo "," >> "$temp_file"
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin TODO Tree Settings ####" "// #### End TODO Tree Settings ####" >> "$temp_file"
  echo "," >> "$temp_file"
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin PSI Header Settings ####" "// #### End PSI Header Settings ####" >> "$temp_file"
  
  # Close settings and customizations
  echo "      }" >> "$temp_file"
  echo "    }" >> "$temp_file"
  echo "  }" >> "$temp_file"
  echo "}" >> "$temp_file"
  
  mv "$temp_file" "${project_path}/.devcontainer/devcontainer.json"
}

# Main function
main() {
  source_colors
  
  # Verify we're in the correct directory by checking for required files
  if [[ ! -f ".devcontainer/devcontainer.json" ]] || [[ ! -f ".mise.toml" ]]; then
    echo -e "${RED}Error: Required template files not found.${NC}"
    echo "This script must be run from the root of the dynamic-dev-container project directory."
    echo "Expected files: .devcontainer/devcontainer.json and .mise.toml"
    exit 1
  fi
  
  local project_path=""
  project_path="${1-}"
  if [[ -z "${project_path}" ]]; then
    echo -e "${RED}The path to your project was not passed in and is required.${NC}"
    echo -e "${CYAN}Usage:${NC} $0 <path-to-your-project>"
    exit 1
  fi

  # Remove trailing slash from project_path if it exists
  project_path="${project_path%/}"

  # Create project directory if it doesn't exist
  create_project_directory "$project_path"

  echo -e "${BLUE}This script will configure and copy the following files into${NC} ${project_path}"
  echo -e "  All files from .devcontainer/ (devcontainer.json will be customized)"
  echo -e "  .mise.toml (customized based on your choices)"
  echo -e "  cspell.json"
  echo -e "  dev.sh (customized with your project settings)"
  echo -e "  run.sh"
  echo -e "  .gitignore (if not already present)"
  echo -e "  pyproject.toml & requirements.txt (if Python extensions selected and not already present)"
  echo ""
  
  local response
  read -r -p "$(echo -e "${CYAN}Do you wish to continue with the interactive configuration? (Y/n): ${NC}")" response
  response=${response:-Y}  # Default to Y if empty
  case "$response" in
    [yY]|[yY][eE][sS]) ;;
    [nN]|[nN][oO])
      echo -e "${RED}Aborting.${NC}"
      exit 1
      ;;
    *)
      echo -e "${YELLOW}Invalid response. Please answer Y or n.${NC}"
      main "$@"  # Restart the process
      return
      ;;
  esac
  echo ""

  echo -e "${BLUE}Starting interactive configuration...${NC}"
  echo ""
  
  # Collect project information first
  echo -e "${BLUE}Project Configuration${NC}"
  echo ""
  
  # Extract default project name from path
  local default_project_name
  default_project_name=$(basename "$project_path")
  
  # Ask for project name with default
  echo -e "${YELLOW}Project Name:${NC} This should be the name of your git repository."
  echo -e "Examples: my-awesome-project, web-app, infrastructure-as-code"
  local project_name
  project_name=$(ask_with_default "Enter project name" "$default_project_name")
  echo ""
  
  # Generate default display name (convert - and _ to spaces, capitalize words)
  local default_display_name
  default_display_name=$(echo "$project_name" | sed 's/[-_]/ /g' | sed 's/\b\w/\U&/g')
  
  # Ask for display name with smart default
  echo -e "${YELLOW}Display Name:${NC} This is the friendly name shown in VS Code."
  echo -e "Examples: My Awesome Project, Web Application Dev, Infrastructure Development"
  local display_name
  display_name=$(ask_with_default "Enter display name" "$default_display_name")
  echo ""
  
  # Ask for container name with default
  echo -e "${YELLOW}Container Name:${NC} This is the Docker container name that will be created."
  local default_container_name="${project_name}-container"
  local container_name
  container_name=$(ask_with_default "Enter container name" "$default_container_name")
  echo ""
  
  # Generate default docker exec command (first letter of each word)
  local default_docker_exec_command
  default_docker_exec_command=$(echo "$project_name" | sed 's/[-_]/ /g' | awk '{for(i=1;i<=NF;i++) printf("%s", substr($i,1,1))}')
  
  # Ask for docker exec command with smart default
  echo -e "${YELLOW}Docker Exec Command:${NC} This creates a shortcut command to quickly access your container."
  echo -e "Examples: 'myapp' creates a command to run: docker exec -it ${container_name} zsh"
  echo -e "Press Enter to use '${default_docker_exec_command}', or type 'none' to skip."
  local docker_exec_command
  read -r -p "$(echo -e "${CYAN}Enter docker exec command [${default_docker_exec_command}]: ${NC}")" docker_exec_command
  # Handle default and 'none' cases
  if [[ -z "$docker_exec_command" ]]; then
    docker_exec_command="$default_docker_exec_command"
  elif [[ "$docker_exec_command" == "none" ]]; then
    docker_exec_command=""
  fi
  echo ""

  echo -e "${BLUE}Starting tool and language configuration...${NC}"
  echo ""

  echo -e "${BLUE}Go Development Tools:${NC}"
  if ask_yes_no "Install Go programming language?" "N"; then
    INSTALL_GO=true
    INSTALL_GOLANG=true
    GOLANG_VERSION=$(ask_with_default "    Enter Go version to install" "latest")
    if ask_yes_no "Install GoReleaser?" "Y"; then
      INSTALL_GORELEASER=true
    fi
  fi
  echo ""

  echo -e "${BLUE}.NET Development Tools:${NC}"
  if ask_yes_no "Install .NET SDK?" "N"; then
    INSTALL_DOTNET=true
    INSTALL_DOTNET_SDK=true
    DOTNET_SDK_VERSION=$(ask_with_default "    Enter .NET SDK version to install" "latest")
  fi
  echo ""

  echo -e "${BLUE}JavaScript/Node.js Development Tools:${NC}"
  echo -e "${YELLOW}Note:${NC} Node.js is fixed to v19 due to compatibility issues."
  echo -e "See the project's README.md for more details on customizing the Node.js version."
  if ask_yes_no "Install Node.js (v19)?" "N"; then
    INSTALL_JAVASCRIPT=true
    INSTALL_NODE=true
    if ask_yes_no "Install pnpm?" "Y"; then
      INSTALL_PNPM=true
    fi
    if ask_yes_no "Install yarn?" "Y"; then
      INSTALL_YARN=true
    fi
    if ask_yes_no "Install Deno?" "Y"; then
      INSTALL_DENO=true
    fi
    if ask_yes_no "Install Bun?" "Y"; then
      INSTALL_BUN=true
    fi
  fi
  echo ""

  echo -e "${BLUE}Kubernetes/Helm Tools:${NC}"
  if ask_yes_no "Install kubectl?" "N"; then
    INSTALL_KUBERNETES=true
    INSTALL_KUBECTL=true
    KUBECTL_VERSION=$(ask_with_default "    Enter kubectl version to install" "latest")
    if ask_yes_no "Install Helm?" "Y"; then
      INSTALL_HELM=true
    fi
    if ask_yes_no "Install k9s?" "Y"; then
      INSTALL_K9S=true
    fi
    if ask_yes_no "Install kubectx/kubens?" "Y"; then
      INSTALL_KUBECTX=true
      INSTALL_KUBENS=true
    fi
  fi
  echo ""

  echo -e "${BLUE}Kubernetes Utilities:${NC}"
  if ask_yes_no "Install krew (kubectl plugin manager)?" "N"; then
    INSTALL_KREW=true
    if ask_yes_no "Install dive (Docker image explorer)?" "Y"; then
      INSTALL_DIVE=true
    fi
    if ask_yes_no "Install kubebench (Kubernetes benchmark tool)?" "Y"; then
      INSTALL_KUBEBENCH=true
    fi
    if ask_yes_no "Install popeye (Kubernetes cluster sanitizer)?" "Y"; then
      INSTALL_POPEYE=true
    fi
    if ask_yes_no "Install trivy (vulnerability scanner)?" "Y"; then
      INSTALL_TRIVY=true
    fi
    if ask_yes_no "Install cmctl (cert-manager CLI)?" "Y"; then
      INSTALL_CMCTL=true
    fi
    if ask_yes_no "Install k3d (lightweight Development Kubernetes)?" "Y"; then
      INSTALL_K3D=true
    fi
  fi
  echo ""

  echo -e "${BLUE}HashiCorp Tools:${NC}"
  if ask_yes_no "Install OpenTofu (Terraform alternative)?" "N"; then
    INSTALL_OPENTOFU=true
    OPENTOFU_VERSION=$(ask_with_default "    Enter OpenTofu version to install" "latest")
  fi
  if ask_yes_no "Install OpenBao (Vault alternative)?" "N"; then
    INSTALL_OPENBAO=true
    OPENBAO_VERSION=$(ask_with_default "    Enter OpenBao version to install" "latest")
  fi
  if ask_yes_no "Install Packer (HashiCorp image builder)?" "N"; then
    INSTALL_PACKER=true
    PACKER_VERSION=$(ask_with_default "    Enter Packer version to install" "latest")
  fi
  echo ""

  echo -e "${BLUE}Miscellaneous Tools:${NC}"
  if ask_yes_no "Install gitui (terminal-based git client)?" "N"; then
    INSTALL_GITUI=true
  fi
  if ask_yes_no "Install tealdeer (fast tldr client)?" "N"; then
    INSTALL_TEALDEER=true
  fi
  if ask_yes_no "Install micro (terminal-based text editor)?" "N"; then
    INSTALL_MICRO=true
  fi
  if ask_yes_no "Install PowerShell?" "N"; then
    INSTALL_POWERSHELL=true
  fi
  echo ""

  # Create .devcontainer directory
  mkdir -p "${project_path}/.devcontainer"

  # First, copy all source files to the destination
  echo -e "${BLUE}Copying template files...${NC}"
  cp -r ./* "${project_path}/"
  # We need to copy hidden files like .gitignore as well
  cp .gitignore "${project_path}/.gitignore"
  cp .krew_plugins "${project_path}/.krew_plugins"
  echo ""

  # Now, generate the customized configuration files, overwriting the copied templates
  echo -e "${BLUE}Generating custom configuration files...${NC}"
  generate_mise_toml "$project_path"
  generate_devcontainer_json "$project_path" "$project_name" "$container_name" "$display_name"
  echo ""

  # Update dev.sh with project settings
  echo -e "${BLUE}Updating dev.sh with project settings...${NC}"
  update_dev_sh "$project_path" "$docker_exec_command" "$project_name" "$container_name"
  echo ""

  # Remove files that are not needed in the new project
  echo -e "${BLUE}Cleaning up installation files...${NC}"
  rm -f "${project_path}/install.sh"
  rm -f "${project_path}/LICENSE"
  rm -f "${project_path}/README.md"
  rm -f "${project_path}/SECURITY.md"
  echo ""

  echo -e "${GREEN}Installation completed successfully!${NC}"
  echo ""
  echo -e "${CYAN}Project Settings Applied:${NC}"
  echo -e "  Project Name: ${project_name}"
  echo -e "  Container Name: ${container_name}"
  echo -e "  Display Name: ${display_name}"
  [[ -n "$docker_exec_command" ]] && echo -e "  Docker Exec Command: ${docker_exec_command}"
  echo ""
  echo -e "${CYAN}Next steps:${NC}"
  echo -e "1. ${YELLOW}Recommended:${NC} Set GITHUB_TOKEN environment variable to avoid API rate limits"
  echo -e "   export GITHUB_TOKEN=\"your_github_token_here\""
  echo -e "2. Review and adjust settings in ${project_path}/.devcontainer/devcontainer.json if needed"
  echo -e "3. Review and adjust tool versions in ${project_path}/.mise.toml if needed"
  echo -e "4. See README.md for detailed configuration instructions"
  echo ""
  echo -e "${BLUE}You can now run:${NC} cd ${project_path} && ./dev.sh"
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
