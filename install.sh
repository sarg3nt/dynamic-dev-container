#!/bin/bash
#
# Installs .devcontainer and other files into a project directory to use the dev container in a new project.
#

set -euo pipefail
IFS=$'\n\t'

# Global decision tracking variables
INSTALL_OPENTOFU=false
INSTALL_KUBERNETES=false
INSTALL_GO=false
INSTALL_PACKER=false
INSTALL_POWERSHELL=false
INCLUDE_PYTHON_EXTENSIONS=false
INCLUDE_MARKDOWN_EXTENSIONS=false
INCLUDE_SHELL_EXTENSIONS=false
INCLUDE_JS_EXTENSIONS=false

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
  NO_NEW_LINE='\033[0K\r'
}

# Ask yes/no question
ask_yes_no() {
  local question="$1"
  local response
  while true; do
    read -r -p "$(echo -e "${CYAN}${question} (y/n): ${NC}")" response
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
  
  echo -e "${BLUE}Configuring .mise.toml...${NC}"
  
  # Start with the header
  cat > "$temp_file" << 'EOF'
# cspell:ignore cmctl gitui krew kubebench kubectx direnv dotenv looztra kompiro kforsthoevel sarg kubeseal stefansedich nlamirault zufardhiyaulhaq sudermanjr
[env]
MISE_PYTHON_COMPILE = false

[tools]

EOF

  # Ask about OpenTofu/Terraform
  if ask_yes_no "Install OpenTofu (Terraform alternative)?"; then
    INSTALL_OPENTOFU=true
    {
      echo "# https://github.com/opentofu/opentofu"
      echo 'opentofu = "1.10.2"'
    } >> "$temp_file"
  fi

  # Ask about OpenBao
  if ask_yes_no "Install OpenBao (Vault alternative)?"; then
    {
      echo "# https://github.com/openbao/openbao/releases"
      echo 'openbao = "2.3.1"'
    } >> "$temp_file"
  fi

  # Ask about Kubernetes/Helm tools
  if ask_yes_no "Install Kubernetes/Helm tools (kubectl, helm, k9s, kubectx)?"; then
    INSTALL_KUBERNETES=true
    {
      echo ""
      echo "#### Begin Kubernetes/Helm ####"
      echo 'kubectl = "1.32"'
      echo 'kubectx = "latest"'
      echo 'k9s = "latest"'
      echo 'helm = "latest"'
      echo "#### End Kubernetes/Helm ####"
    } >> "$temp_file"
    
    # Ask about individual Kubernetes utilities
    echo ""
    echo -e "${BLUE}Additional Kubernetes utilities:${NC}"
    
    local kube_utils_added=false
    
    if ask_yes_no "Install krew (kubectl plugin manager)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'krew = "latest"' >> "$temp_file"
    fi
    
    if ask_yes_no "Install dive (Docker image explorer)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'dive = "latest"' >> "$temp_file"
    fi
    
    if ask_yes_no "Install popeye (Kubernetes cluster sanitizer)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'popeye = "latest"' >> "$temp_file"
    fi
    
    if ask_yes_no "Install trivy (vulnerability scanner)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'trivy = "latest"' >> "$temp_file"
    fi
    
    if ask_yes_no "Install k3d (lightweight Kubernetes)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'k3d = "latest"' >> "$temp_file"
    fi
    
    if ask_yes_no "Install cmctl (cert-manager CLI)?"; then
      if [ "$kube_utils_added" = false ]; then
        {
          echo ""
          echo "#### Begin Kubernetes Utilities ####"
        } >> "$temp_file"
        kube_utils_added=true
      fi
      echo 'cmctl = "latest"' >> "$temp_file"
    fi
    
    if [ "$kube_utils_added" = true ]; then
      echo "#### End Kubernetes Utilities ####" >> "$temp_file"
    fi
  fi

  # Ask about individual tools
  if ask_yes_no "Install Git UI (gitui)?"; then
    echo 'gitui = "latest"' >> "$temp_file"
  fi

  if ask_yes_no "Install Go programming language?"; then
    INSTALL_GO=true
    {
      echo 'golang = "latest"'
      echo 'goreleaser = "latest"'
    } >> "$temp_file"
  fi

  if ask_yes_no "Install Packer (HashiCorp image builder)?"; then
    INSTALL_PACKER=true
    echo 'packer = "latest"' >> "$temp_file"
  fi

  if ask_yes_no "Install TealDeer (fast tldr client)?"; then
    echo 'tealdeer = "latest"' >> "$temp_file"
  fi

  if ask_yes_no "Install PowerShell?"; then
    INSTALL_POWERSHELL=true
    echo 'powershell = "latest"' >> "$temp_file"
  fi

  # Add aliases section
  {
    echo ""
    echo "# See: https://mise.jdx.dev/dev-tools/aliases.html for specs on the alias section."
    echo "[alias]"
    echo "kubebench = 'asdf:sarg3nt/asdf-kube-bench'"
    echo "tealdeer = 'asdf:sarg3nt/asdf-tealdeer'"
    echo ""
    echo "[settings]"
    echo "experimental = true"
    echo 'http_timeout = "90s"'
    echo "jobs = 1"
    echo "yes = true"
  } >> "$temp_file"

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
  
  echo -e "${BLUE}Configuring devcontainer.json...${NC}"
  
  # Read the base devcontainer.json up to extensions
  awk '/^      "extensions": \[/,/^      \],$/{if(/^      "extensions": \[/) print; else if(/^      \],$/) exit; else next} !/^      "extensions": \[/' .devcontainer/devcontainer.json | head -n -1 > "$temp_file"
  
  # Update the name and runArgs in the temp file
  sed -i "s/\"name\": \"[^\"]*\"/\"name\": \"${display_name}\"/" "$temp_file"
  sed -i "s/--name=generic-dev-container/--name=${container_name}/g" "$temp_file"
  sed -i "s/generic-dev-container-shellhistory/${container_name}-shellhistory/g" "$temp_file"
  sed -i "s/generic-dev-container-plugins/${container_name}-plugins/g" "$temp_file"
  
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
  
  # Ask about Python extensions (no corresponding tool installation)
  if ask_yes_no "Include Python development extensions?"; then
    INCLUDE_PYTHON_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Python ####" "// #### End Python ####" >> "$temp_file"
  fi
  
  # Ask about Markdown extensions (no corresponding tool installation)
  if ask_yes_no "Include Markdown editing extensions?"; then
    INCLUDE_MARKDOWN_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Markdown ####" "// #### End Markdown ####" >> "$temp_file"
  fi
  
  # Ask about Shell/Bash extensions (always useful, no specific tool)
  if ask_yes_no "Include Shell/Bash development extensions?"; then
    INCLUDE_SHELL_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Shell/Bash ####" "// #### End Shell/Bash ####" >> "$temp_file"
  fi
  
  # Include Kubernetes extensions if Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ]; then
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
  
  # Ask about JavaScript/TypeScript extensions (no corresponding tool installation)
  if ask_yes_no "Include JavaScript/TypeScript development extensions?"; then
    INCLUDE_JS_EXTENSIONS=true
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
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Go Settings ####" "// #### End Go Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Python settings if Python extensions were selected
  if [ "$INCLUDE_PYTHON_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Python language settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Python Settings ####" "// #### End Python Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Markdown settings if Markdown extensions were selected
  if [ "$INCLUDE_MARKDOWN_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Markdown settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Markdown Settings ####" "// #### End Markdown Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Shell/Bash settings if Shell extensions were selected
  if [ "$INCLUDE_SHELL_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including Shell/Bash settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Shell/Bash Settings ####" "// #### End Shell/Bash Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include Kubernetes settings if Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ]; then
    echo -e "${GREEN}✓ Including Kubernetes/Helm settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Kubernetes/Helm Settings ####" "// #### End Kubernetes/Helm Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include JavaScript/TypeScript settings if JS extensions were selected
  if [ "$INCLUDE_JS_EXTENSIONS" = true ]; then
    echo -e "${GREEN}✓ Including JavaScript/TypeScript settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript Settings ####" "// #### End JavaScript/TypeScript Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Include PowerShell settings if PowerShell was installed
  if [ "$INSTALL_POWERSHELL" = true ]; then
    echo -e "${GREEN}✓ Including PowerShell settings${NC}"
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin PowerShell Settings ####" "// #### End PowerShell Settings ####" >> "$temp_file"
    echo "," >> "$temp_file"
  fi
  
  # Always include Spell Checker, TODO Tree, and PSI Header settings
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
    echo "This script must be run from the root of the generic-dev-container project directory."
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
  echo -e "  .devcontainer/ (customized based on your choices)"
  echo -e "  .mise.toml (customized based on your choices)"
  echo -e "  cspell.json"
  echo -e "  dev.sh (customized with your project settings)"
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

  echo -e "${BLUE}Starting interactive configuration...${NC}"
  echo ""

  # Create .devcontainer directory
  mkdir -p "${project_path}/.devcontainer"

  # Generate customized files
  generate_mise_toml "$project_path"
  generate_devcontainer_json "$project_path" "$project_name" "$container_name" "$display_name"

  # Copy and update dev.sh
  echo -e "${BLUE}Updating dev.sh with project settings...${NC}"
  update_dev_sh "$project_path" "$docker_exec_command" "$project_name" "$container_name"

  # Copy remaining files as-is
  echo -e "${BLUE}Copying remaining files...${NC}"
  echo -e "  ${GREEN}Copying${NC} cspell.json"
  cp "cspell.json" "${project_path}/"
  
  # Copy devcontainer scripts
  echo -e "  ${GREEN}Copying${NC} .devcontainer scripts"
  cp .devcontainer/*.sh "${project_path}/.devcontainer/"
  
  # Copy devcontainer utils directory
  echo -e "  ${GREEN}Copying${NC} .devcontainer/utils directory"
  cp -r .devcontainer/utils "${project_path}/.devcontainer/"

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
  echo -e "1. Review and adjust settings in ${project_path}/.devcontainer/devcontainer.json if needed"
  echo -e "2. Review and adjust tool versions in ${project_path}/.mise.toml if needed"
  echo -e "3. See README.md for detailed configuration instructions"
  echo ""
  echo -e "${BLUE}You can now run:${NC} cd ${project_path} && ./dev.sh"
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
