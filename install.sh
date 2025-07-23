#!/bin/bash
#
# TUI version of install.sh using dialog for a better user experience.
# Installs .devcontainer and other files into a project directory to use the dev container in a new project.
# cspell:ignore openbao myapp sudermanjr kubens DIALOGRC defaultno noconfirm pyproject sles

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
INSTALL_COSIGN=false

# Version variables for tools
GOLANG_VERSION="latest"
DOTNET_SDK_VERSION="latest"
KUBECTL_VERSION="latest"
OPENBAO_VERSION="latest"
OPENTOFU_VERSION="latest"
PACKER_VERSION="latest"

# Files and directories to copy to new projects
FILES_TO_COPY=(
  ".gitignore"
  ".krew_plugins"
  ".packages"
  "cspell.json"
  "dev.sh"
  "pyproject.toml"
  "requirements.txt"
  "run.sh"
  ".mise.toml"
)

DIRECTORIES_TO_COPY=(
  ".devcontainer"
)

# TUI Configuration
DIALOG_HEIGHT=25
DIALOG_WIDTH=85
DIALOG_CHECKLIST_HEIGHT=20

# Colors for dialog
export DIALOGRC=/tmp/dialogrc
cat > $DIALOGRC << 'EOF'
# Dialog color configuration
screen_color = (CYAN,BLUE,ON)
shadow_color = (BLACK,BLACK,ON)
dialog_color = (WHITE,BLUE,ON)
title_color = (YELLOW,BLUE,ON)
border_color = (WHITE,BLUE,ON)
button_active_color = (WHITE,RED,ON)
button_inactive_color = (WHITE,BLUE,OFF)
button_key_active_color = (WHITE,RED,ON)
button_key_inactive_color = (RED,BLUE,OFF)
button_label_active_color = (YELLOW,RED,ON)
button_label_inactive_color = (WHITE,BLUE,OFF)
inputbox_color = (WHITE,BLUE,OFF)
inputbox_border_color = (WHITE,BLUE,ON)
searchbox_color = (WHITE,BLUE,OFF)
searchbox_title_color = (YELLOW,BLUE,ON)
searchbox_border_color = (WHITE,BLUE,ON)
position_indicator_color = (YELLOW,BLUE,ON)
menubox_color = (WHITE,BLUE,OFF)
menubox_border_color = (WHITE,BLUE,ON)
item_color = (WHITE,BLUE,OFF)
item_selected_color = (WHITE,RED,ON)
tag_color = (YELLOW,BLUE,ON)
tag_selected_color = (YELLOW,RED,ON)
tag_key_color = (YELLOW,BLUE,ON)
tag_key_selected_color = (YELLOW,RED,ON)
check_color = (WHITE,BLUE,OFF)
check_selected_color = (WHITE,RED,ON)
uarrow_color = (GREEN,BLUE,ON)
darrow_color = (GREEN,BLUE,ON)
itemhelp_color = (WHITE,BLACK,OFF)
form_active_text_color = (WHITE,BLUE,ON)
form_text_color = (WHITE,CYAN,ON)
form_item_readonly_color = (CYAN,BLUE,ON)
gauge_color = (BLUE,BLUE,ON)
border2_color = (WHITE,BLUE,ON)
inputbox_border2_color = (WHITE,BLUE,ON)
searchbox_border2_color = (WHITE,BLUE,ON)
menubox_border2_color = (WHITE,BLUE,ON)
EOF

# Detect OS and package manager
detect_os_and_package_manager() {
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    case "$ID" in
      rocky|rhel|centos|fedora|almalinux)
        if command -v dnf >/dev/null 2>&1; then
          echo "dnf"
        elif command -v yum >/dev/null 2>&1; then
          echo "yum"
        else
          echo "unknown"
        fi
        ;;
      ubuntu|debian)
        if command -v apt-get >/dev/null 2>&1; then
          echo "apt-get"
        elif command -v apt >/dev/null 2>&1; then
          echo "apt"
        else
          echo "unknown"
        fi
        ;;
      arch|manjaro)
        if command -v pacman >/dev/null 2>&1; then
          echo "pacman"
        else
          echo "unknown"
        fi
        ;;
      opensuse*|sles)
        if command -v zypper >/dev/null 2>&1; then
          echo "zypper"
        else
          echo "unknown"
        fi
        ;;
      alpine)
        if command -v apk >/dev/null 2>&1; then
          echo "apk"
        else
          echo "unknown"
        fi
        ;;
      *)
        echo "unknown"
        ;;
    esac
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew >/dev/null 2>&1; then
      echo "brew"
    else
      echo "unknown"
    fi
  else
    echo "unknown"
  fi
}

# Install dialog using detected package manager
install_dialog() {
  local package_manager="$1"
  local install_cmd=""
  local package_name="dialog"
  
  case "$package_manager" in
    dnf|yum)
      install_cmd="sudo $package_manager install -y $package_name"
      ;;
    apt-get|apt)
      install_cmd="sudo $package_manager update && sudo $package_manager install -y $package_name"
      ;;
    pacman)
      install_cmd="sudo pacman -Sy --noconfirm $package_name"
      ;;
    zypper)
      install_cmd="sudo zypper install -y $package_name"
      ;;
    apk)
      install_cmd="sudo apk add $package_name"
      ;;
    brew)
      install_cmd="brew install $package_name"
      ;;
    *)
      echo "Error: Unknown package manager. Please install dialog manually:"
      echo "  On Rocky Linux/RHEL/CentOS/Fedora: dnf install dialog"
      echo "  On Ubuntu/Debian: apt-get install dialog"
      echo "  On Arch/Manjaro: pacman -S dialog"
      echo "  On openSUSE: zypper install dialog"
      echo "  On Alpine: apk add dialog"
      echo "  On macOS: brew install dialog"
      return 1
      ;;
  esac
  
  echo "Installing dialog using: $install_cmd"
  eval "$install_cmd"
  
  # Verify installation
  if command -v dialog >/dev/null 2>&1; then
    echo "Dialog installed successfully!"
    return 0
  else
    echo "Error: Failed to install dialog. Please install it manually."
    return 1
  fi
}

# Check if dialog is installed and offer to install it if missing
check_dependencies() {
  if ! command -v dialog >/dev/null 2>&1; then
    echo "The 'dialog' utility is required for the Terminal User Interface (TUI)."
    echo ""
    
    # Detect OS and package manager
    local package_manager
    package_manager=$(detect_os_and_package_manager)
    
    if [[ "$package_manager" == "unknown" ]]; then
      echo "Error: Could not detect your package manager. Please install dialog manually:"
      echo "  On Rocky Linux/RHEL/CentOS/Fedora: dnf install dialog"
      echo "  On Ubuntu/Debian: apt-get install dialog"
      echo "  On Arch/Manjaro: pacman -S dialog"
      echo "  On openSUSE: zypper install dialog"
      echo "  On Alpine: apk add dialog"
      echo "  On macOS: brew install dialog"
      exit 1
    fi
    
    echo "Detected package manager: $package_manager"
    echo ""
    
    # Ask for permission to install
    echo -n "Would you like to install dialog automatically? [Y/n]: "
    read -r response
    
    # Default to yes if empty response
    response=${response:-Y}
    
    case "$response" in
      [Yy]|[Yy][Ee][Ss])
        echo "Installing dialog..."
        if install_dialog "$package_manager"; then
          echo "Dialog installation completed. Continuing with setup..."
          echo ""
        else
          exit 1
        fi
        ;;
      [Nn]|[Nn][Oo])
        echo "Installation cancelled. Please install dialog manually and run this script again."
        exit 1
        ;;
      *)
        echo "Invalid response. Please install dialog manually and run this script again."
        exit 1
        ;;
    esac
  fi
}

# Source colors library (for non-TUI output)
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

# Get latest major versions for a tool
get_latest_major_versions() {
  local tool_name="$1"
  local versions
  
  # Fetch remote versions using mise, handle potential errors, and filter out pre-release versions
  versions=$(mise ls-remote "$tool_name" 2>/dev/null | grep -v -E 'rc|alpha|beta' || echo "")
  
  if [[ -z "$versions" ]]; then
    echo ""
    return
  fi
  
  local major_versions
  # Parse versions to get unique major versions, sorted numerically
  if [[ "$tool_name" == "kubectl" || "$tool_name" == "go" || "$tool_name" == "opentofu" || "$tool_name" == "openbao" || "$tool_name" == "packer" ]]; then
    # For versions like 1.31.2, major is 1.31
    major_versions=$(echo "$versions" | awk -F. '{print $1"."$2}' | sort -rV | uniq | head -n 5 | tr '\n' ',' | sed 's/,$//')
  else
    # For versions like 22.10.0, major is 22
    major_versions=$(echo "$versions" | awk -F. '{print $1}' | sort -rV | uniq | head -n 5 | tr '\n' ',' | sed 's/,$//')
  fi
  
  if [[ -n "$major_versions" ]]; then
    echo "(e.g., ${major_versions})"
  else
    echo ""
  fi
}

# TUI input dialog with default value
tui_input() {
  local title="$1"
  local prompt="$2"
  local default="$3"
  local result
  
  result=$(dialog --title "$title" \
                 --inputbox "$prompt" \
                 $DIALOG_HEIGHT $DIALOG_WIDTH \
                 "$default" \
                 3>&1 1>&2 2>&3 3>&-)
  
  echo "$result"
}

# TUI form dialog for multiple inputs
tui_form() {
  local title="$1"
  local text="$2"
  shift 2
  local fields=("$@")
  
  dialog --title "$title" \
         --form "$text" \
         $DIALOG_HEIGHT $DIALOG_WIDTH 4 \
         "${fields[@]}" \
         3>&1 1>&2 2>&3 3>&-
}

# TUI yes/no dialog
tui_yesno() {
  local title="$1"
  local question="$2"
  local default="${3:-n}"
  
  if [[ "$default" == "y" || "$default" == "Y" ]]; then
    dialog --title "$title" --defaultno --yesno "$question" $DIALOG_HEIGHT $DIALOG_WIDTH
  else
    dialog --title "$title" --yesno "$question" $DIALOG_HEIGHT $DIALOG_WIDTH
  fi
}

# TUI multi-select checklist
tui_checklist() {
  local title="$1"
  local text="$2"
  shift 2
  local options=("$@")
  
  dialog --title "$title" \
         --checklist "$text" \
         $DIALOG_HEIGHT $DIALOG_WIDTH $DIALOG_CHECKLIST_HEIGHT \
         "${options[@]}" \
         3>&1 1>&2 2>&3 3>&-
}

# Show welcome screen
show_welcome() {
  dialog --title "Dynamic Dev Container Setup" \
         --msgbox "Welcome to the Dynamic Dev Container TUI Setup!\n\nThis wizard will guide you through configuring your development container with the tools and extensions you need.\n\nNavigation:\n• Use TAB/SHIFT+TAB to navigate between buttons\n• Use SPACE to select/deselect checkboxes\n• Use ENTER to confirm selections\n• Mouse support is enabled for clicking\n\nPress OK to continue..." \
         $DIALOG_HEIGHT $DIALOG_WIDTH
}

# Collect project information
collect_project_info() {
  local project_path="$1"
  
  # Extract default project name from path
  local default_project_name
  default_project_name=$(basename "$project_path")
  
  # Generate default display name
  local default_display_name
  default_display_name=$(echo "$default_project_name" | sed 's/[-_]/ /g' | sed 's/\b\w/\U&/g')
  
  # Generate default container name
  local default_container_name="${default_project_name}-container"
  
  # Generate default docker exec command
  local default_docker_exec_command
  default_docker_exec_command=$(echo "$default_project_name" | sed 's/[-_]/ /g' | awk '{for(i=1;i<=NF;i++) printf("%s", substr($i,1,1))}')
  
  # Collect all project information in one form
  local form_result
  form_result=$(tui_form "Project Configuration" \
                        "Enter your project configuration details:" \
                        "Project Name:" 1 1 "$default_project_name" 1 20 40 0 \
                        "Display Name:" 2 1 "$default_display_name" 2 20 40 0 \
                        "Container Name:" 3 1 "$default_container_name" 3 20 40 0 \
                        "Docker Command:" 4 1 "$default_docker_exec_command" 4 20 40 0)
  
  if [[ -z "$form_result" ]]; then
    # User cancelled project configuration - ask for confirmation
    if tui_yesno "Exit Confirmation" "Are you sure you want to exit the setup?" "n"; then
      clear
      exit 0
    else
      # User wants to continue, ask for project configuration again
      form_result=$(tui_form "Project Configuration" \
                            "Enter your project configuration details:" \
                            "Project Name:" 1 1 "$default_project_name" 1 20 40 0 \
                            "Display Name:" 2 1 "$default_display_name" 2 20 40 0 \
                            "Container Name:" 3 1 "$default_container_name" 3 20 40 0 \
                            "Docker Command:" 4 1 "$default_docker_exec_command" 4 20 40 0)
      
      # If they cancel again, exit gracefully
      if [[ -z "$form_result" ]]; then
        clear
        exit 0
      fi
    fi
  fi
  
  # Parse form result (each field on a separate line)
  PROJECT_NAME=$(echo "$form_result" | sed -n '1p')
  DISPLAY_NAME=$(echo "$form_result" | sed -n '2p')
  CONTAINER_NAME=$(echo "$form_result" | sed -n '3p')
  DOCKER_EXEC_COMMAND=$(echo "$form_result" | sed -n '4p')
  
  # Validate required fields
  if [[ -z "$PROJECT_NAME" ]]; then
    dialog --title "Error" --msgbox "Project name is required!" 10 40
    return 1
  fi
  
  # Use project name for display name if empty
  if [[ -z "$DISPLAY_NAME" ]]; then
    DISPLAY_NAME="$PROJECT_NAME"
  fi
  
  # Use default container name if empty
  if [[ -z "$CONTAINER_NAME" ]]; then
    CONTAINER_NAME="${PROJECT_NAME}-container"
  fi
}

# Development tools selection
select_development_tools() {
  # Go Development Tools
  if tui_yesno "Go Development" "Install Go programming language?" "n"; then
    INSTALL_GO=true
    INSTALL_GOLANG=true
    local version_examples
    version_examples=$(get_latest_major_versions "go")
    GOLANG_VERSION=$(tui_input "Go Configuration" \
                              "Enter Go version to install $version_examples\n\nGo is a programming language developed by Google:" \
                              "latest")
    
    if tui_yesno "Go Tools" "Install GoReleaser?" "y"; then
      INSTALL_GORELEASER=true
    fi
  fi

  # .NET Development Tools  
  if tui_yesno ".NET Development" "Install .NET SDK?" "n"; then
    INSTALL_DOTNET=true
    INSTALL_DOTNET_SDK=true
    local version_examples
    version_examples=$(get_latest_major_versions "dotnet")
    DOTNET_SDK_VERSION=$(tui_input ".NET Configuration" \
                                  "Enter .NET SDK version to install $version_examples\n\n.NET is Microsoft's cross-platform development framework:" \
                                  "latest")
  fi

  # JavaScript/Node.js Development Tools
  if tui_yesno "JavaScript/Node.js Development" "Install Node.js (v19)?\n\nNote: Node.js is fixed to v19 due to compatibility issues.\nSee README.md for details on customizing the Node.js version." "n"; then
    INSTALL_JAVASCRIPT=true
    INSTALL_NODE=true
    
    # Select additional JavaScript tools
    local js_tools
    js_tools=$(tui_checklist "JavaScript/Node.js Package Managers & Runtimes" \
                            "Select additional JavaScript tools to install:" \
                            "pnpm" "pnpm - Fast, disk space efficient package manager" on \
                            "yarn" "yarn - Popular alternative package manager" on \
                            "deno" "Deno - Secure TypeScript/JavaScript runtime" on \
                            "bun" "Bun - Fast all-in-one JavaScript runtime" on)
    
    for tool in $js_tools; do
      case "$tool" in
        "pnpm") INSTALL_PNPM=true ;;
        "yarn") INSTALL_YARN=true ;;
        "deno") INSTALL_DENO=true ;;
        "bun") INSTALL_BUN=true ;;
      esac
    done
  fi

  # Kubernetes/Helm Tools
  local k8s_helm_tools
  k8s_helm_tools=$(get_tools_from_section "Kubernetes/Helm")
  
  if [[ -n "$k8s_helm_tools" ]] && tui_yesno "Kubernetes/Helm Tools" "Install kubectl and other Kubernetes/Helm tools?" "n"; then
    INSTALL_KUBERNETES=true
    
    # Build checklist options dynamically, with kubectl required and others optional
    local k8s_options=()
    for tool in $k8s_helm_tools; do
      local description
      description=$(get_tool_description "$tool")
      if [[ "$tool" == "kubectl" ]]; then
        k8s_options+=("$tool" "$description" "on")  # kubectl is required
      else
        k8s_options+=("$tool" "$description" "on")  # others default to on
      fi
    done
    
    if [[ ${#k8s_options[@]} -gt 0 ]]; then
      local selected_k8s
      selected_k8s=$(tui_checklist "Kubernetes/Helm Tools" \
                                  "Select Kubernetes/Helm tools to install:" \
                                  "${k8s_options[@]}")
      
      for tool in $selected_k8s; do
        case "$tool" in
          "kubectl") 
            INSTALL_KUBECTL=true
            local version_examples
            version_examples=$(get_latest_major_versions "kubectl")
            KUBECTL_VERSION=$(tui_input "Kubernetes Configuration" \
                                        "Enter kubectl version to install $version_examples\n\nkubectl is the command-line tool for Kubernetes:" \
                                        "latest")
            ;;
          "helm") INSTALL_HELM=true ;;
          "k9s") INSTALL_K9S=true ;;
          "kubectx") INSTALL_KUBECTX=true ;;
          "kubens") INSTALL_KUBENS=true ;;
        esac
      done
    fi
  fi

  # Kubernetes Utilities
  local k8s_utils_list
  k8s_utils_list=$(get_tools_from_section "Kubernetes Utilities")
  
  if [[ -n "$k8s_utils_list" ]] && tui_yesno "Kubernetes Utilities" "Install krew and other Kubernetes utilities?" "n"; then
    INSTALL_KREW=true
    
    # Build checklist options dynamically
    local k8s_utils_options=()
    for tool in $k8s_utils_list; do
      local description
      description=$(get_tool_description "$tool")
      k8s_utils_options+=("$tool" "$description" "on")
    done
    
    if [[ ${#k8s_utils_options[@]} -gt 0 ]]; then
      local selected_k8s_utils
      selected_k8s_utils=$(tui_checklist "Kubernetes Utilities" \
                                        "Select Kubernetes utilities to install:" \
                                        "${k8s_utils_options[@]}")
      
      for tool in $selected_k8s_utils; do
        case "$tool" in
          "krew") INSTALL_KREW=true ;;
          "dive") INSTALL_DIVE=true ;;
          "kubebench") INSTALL_KUBEBENCH=true ;;
          "popeye") INSTALL_POPEYE=true ;;
          "trivy") INSTALL_TRIVY=true ;;
          "cmctl") INSTALL_CMCTL=true ;;
          "k3d") INSTALL_K3D=true ;;
        esac
      done
    fi
  fi

  # HashiCorp Tools
  local hashicorp_tools
  hashicorp_tools=$(get_tools_from_section "HashiCorp Tools")
  
  if [[ -n "$hashicorp_tools" ]]; then
    # Build checklist options dynamically
    local hashicorp_options=()
    for tool in $hashicorp_tools; do
      local description
      description=$(get_tool_description "$tool")
      hashicorp_options+=("$tool" "$description" "off")
    done
    
    if [[ ${#hashicorp_options[@]} -gt 0 ]]; then
      local selected_hashicorp
      selected_hashicorp=$(tui_checklist "HashiCorp Tools" \
                                        "Select HashiCorp tools to install:" \
                                        "${hashicorp_options[@]}")
      
      for tool in $selected_hashicorp; do
        case "$tool" in
          "opentofu") 
            INSTALL_OPENTOFU=true
            local version_examples
            version_examples=$(get_latest_major_versions "opentofu")
            OPENTOFU_VERSION=$(tui_input "OpenTofu Configuration" \
                                         "Enter OpenTofu version to install $version_examples\n\nOpenTofu is an open-source Terraform alternative:" \
                                         "latest")
            ;;
          "openbao") 
            INSTALL_OPENBAO=true
            local version_examples
            version_examples=$(get_latest_major_versions "openbao")
            OPENBAO_VERSION=$(tui_input "OpenBao Configuration" \
                                        "Enter OpenBao version to install $version_examples\n\nOpenBao is an open-source Vault alternative:" \
                                        "latest")
            ;;
          "packer") 
            INSTALL_PACKER=true
            local version_examples
            version_examples=$(get_latest_major_versions "packer")
            PACKER_VERSION=$(tui_input "Packer Configuration" \
                                       "Enter Packer version to install $version_examples\n\nPacker builds machine images from configuration:" \
                                       "latest")
            ;;
        esac
      done
    fi
  fi

  # Miscellaneous Tools
  local misc_tools_list
  misc_tools_list=$(get_tools_from_section "Miscellaneous Tools")
  
  if [[ -n "$misc_tools_list" ]]; then
    # Build checklist options dynamically
    local misc_options=()
    for tool in $misc_tools_list; do
      local description
      description=$(get_tool_description "$tool")
      misc_options+=("$tool" "$description" "off")
    done
    
    if [[ ${#misc_options[@]} -gt 0 ]]; then
      local selected_misc
      selected_misc=$(tui_checklist "Miscellaneous Development Tools" \
                                   "Select miscellaneous tools to install:" \
                                   "${misc_options[@]}")
      
      for tool in $selected_misc; do
        case "$tool" in
          "gitui") INSTALL_GITUI=true ;;
          "tealdeer") INSTALL_TEALDEER=true ;;
          "micro") INSTALL_MICRO=true ;;
          "powershell") INSTALL_POWERSHELL=true ;;
          "cosign") INSTALL_COSIGN=true ;;
        esac
      done
    fi
  fi

  # VS Code Extensions (for tools without automatic extensions)
  local extensions
  extensions=$(tui_checklist "VS Code Extensions" \
                            "Select VS Code extension categories to include.\nNote: Extensions for selected dev tools are automatically included:" \
                            "python" "Python - Development extensions for Python programming" on \
                            "markdown" "Markdown - Enhanced editing and preview extensions" on \
                            "shell" "Shell/Bash - Scripting and development extensions" on)
  
  for ext in $extensions; do
    case "$ext" in
      "python") INCLUDE_PYTHON_EXTENSIONS=true ;;
      "markdown") INCLUDE_MARKDOWN_EXTENSIONS=true ;;
      "shell") INCLUDE_SHELL_EXTENSIONS=true ;;
    esac
  done
}



# Show configuration summary
show_summary() {
  local summary="CONFIGURATION SUMMARY\n"
  summary+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
  summary+="Project Settings:\n"
  summary+="  • Name: $PROJECT_NAME\n"
  summary+="  • Display Name: $DISPLAY_NAME\n"
  summary+="  • Container: $CONTAINER_NAME\n"
  [[ -n "$DOCKER_EXEC_COMMAND" ]] && summary+="  • Exec Command: $DOCKER_EXEC_COMMAND\n"
  summary+="\n"
  
  # Count and display selected tools
  local tool_count=0
  local tools_section=""
  
  if [[ "$INSTALL_GO" == true ]]; then
    tools_section+="  ✓ Go ($GOLANG_VERSION)"
    [[ "$INSTALL_GORELEASER" == true ]] && tools_section+=" + GoReleaser"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  if [[ "$INSTALL_DOTNET" == true ]]; then
    tools_section+="  ✓ .NET SDK ($DOTNET_SDK_VERSION)\n"
    ((tool_count++))
  fi
  
  if [[ "$INSTALL_JAVASCRIPT" == true ]]; then
    tools_section+="  ✓ Node.js (v19)"
    [[ "$INSTALL_PNPM" == true ]] && tools_section+=" + pnpm"
    [[ "$INSTALL_YARN" == true ]] && tools_section+=" + yarn"
    [[ "$INSTALL_DENO" == true ]] && tools_section+=" + Deno"
    [[ "$INSTALL_BUN" == true ]] && tools_section+=" + Bun"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  if [[ "$INSTALL_KUBERNETES" == true ]]; then
    tools_section+="  ✓ kubectl ($KUBECTL_VERSION)"
    [[ "$INSTALL_HELM" == true ]] && tools_section+=" + Helm"
    [[ "$INSTALL_K9S" == true ]] && tools_section+=" + k9s"
    [[ "$INSTALL_KUBECTX" == true ]] && tools_section+=" + kubectx/kubens"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  if [[ "$INSTALL_KREW" == true ]]; then
    tools_section+="  ✓ Kubernetes utilities: krew"
    [[ "$INSTALL_DIVE" == true ]] && tools_section+=", dive"
    [[ "$INSTALL_KUBEBENCH" == true ]] && tools_section+=", kubebench"
    [[ "$INSTALL_POPEYE" == true ]] && tools_section+=", popeye"
    [[ "$INSTALL_TRIVY" == true ]] && tools_section+=", trivy"
    [[ "$INSTALL_CMCTL" == true ]] && tools_section+=", cmctl"
    [[ "$INSTALL_K3D" == true ]] && tools_section+=", k3d"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  if [[ "$INSTALL_OPENTOFU" == true || "$INSTALL_OPENBAO" == true || "$INSTALL_PACKER" == true ]]; then
    tools_section+="  ✓ HashiCorp tools:"
    [[ "$INSTALL_OPENTOFU" == true ]] && tools_section+=" OpenTofu ($OPENTOFU_VERSION)"
    [[ "$INSTALL_OPENBAO" == true ]] && tools_section+=" OpenBao ($OPENBAO_VERSION)"
    [[ "$INSTALL_PACKER" == true ]] && tools_section+=" Packer ($PACKER_VERSION)"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  [[ "$INSTALL_POWERSHELL" == true ]] && { tools_section+="  ✓ PowerShell\n"; ((tool_count++)); }
  
  if [[ "$INSTALL_GITUI" == true || "$INSTALL_TEALDEER" == true || "$INSTALL_MICRO" == true ]]; then
    tools_section+="  ✓ Misc tools:"
    [[ "$INSTALL_GITUI" == true ]] && tools_section+=" gitui"
    [[ "$INSTALL_TEALDEER" == true ]] && tools_section+=" tealdeer"
    [[ "$INSTALL_MICRO" == true ]] && tools_section+=" micro"
    tools_section+="\n"
    ((tool_count++))
  fi
  
  if [[ $tool_count -gt 0 ]]; then
    summary+="Development Tools ($tool_count categories):\n$tools_section"
  else
    summary+="Development Tools: None selected\n"
  fi
  summary+="\n"
  
  # VS Code extensions
  local ext_count=0
  local ext_list=""
  
  # Automatic extensions based on selected tools
  [[ "$INSTALL_GO" == true ]] && { ext_list+="Go "; ((ext_count++)); }
  [[ "$INSTALL_DOTNET" == true ]] && { ext_list+=".NET "; ((ext_count++)); }
  [[ "$INSTALL_JAVASCRIPT" == true ]] && { ext_list+="JavaScript/Node.js "; ((ext_count++)); }
  [[ "$INSTALL_KUBERNETES" == true || "$INSTALL_KREW" == true ]] && { ext_list+="Kubernetes/Helm "; ((ext_count++)); }
  [[ "$INSTALL_OPENTOFU" == true ]] && { ext_list+="Terraform/OpenTofu "; ((ext_count++)); }
  [[ "$INSTALL_NODE" == true ]] && { ext_list+="JavaScript/TypeScript "; ((ext_count++)); }
  [[ "$INSTALL_PACKER" == true ]] && { ext_list+="Packer "; ((ext_count++)); }
  [[ "$INSTALL_POWERSHELL" == true ]] && { ext_list+="PowerShell "; ((ext_count++)); }
  
  # Optional extensions selected by user
  [[ "$INCLUDE_PYTHON_EXTENSIONS" == true ]] && { ext_list+="Python "; ((ext_count++)); }
  [[ "$INCLUDE_MARKDOWN_EXTENSIONS" == true ]] && { ext_list+="Markdown "; ((ext_count++)); }
  [[ "$INCLUDE_SHELL_EXTENSIONS" == true ]] && { ext_list+="Shell/Bash "; ((ext_count++)); }
  
  if [[ $ext_count -gt 0 ]]; then
    summary+="VS Code Extensions: GitHub + Core + $ext_list\n"
  else
    summary+="VS Code Extensions: GitHub + Core extensions only\n"
  fi
  
  summary+="\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
  summary+="Proceed with installation?"
  
  dialog --title "Configuration Summary" \
         --yesno "$summary" \
         $DIALOG_HEIGHT $DIALOG_WIDTH
}

# Create project directory if it doesn't exist
create_project_directory() {
  local project_path="$1"
  
  if [[ ! -d "${project_path}" ]]; then
    if tui_yesno "Create Directory" "The path '${project_path}' does not exist.\n\nWould you like to create it?" "y"; then
      mkdir -p "${project_path}"
    else
      dialog --title "Error" --msgbox "Installation aborted." 8 30
      clear
      exit 0
    fi
  fi
}

# Import functions from original install.sh
# These are the file generation and processing functions

# Extract sections from .mise.toml
extract_mise_section() {
  local start_marker="$1"
  local end_marker="$2"
  local file=".mise.toml"
  
  # Use awk with proper handling of markers
  awk -v start="$start_marker" -v end="$end_marker" '
    $0 == start { found=1; next }
    $0 == end { found=0; next }
    found { print }
  ' "$file"
}

# Get tools from a specific section in .mise.toml
get_tools_from_section() {
  local section_name="$1"
  local start_marker="#### Begin ${section_name} ####"
  local end_marker="#### End ${section_name} ####"
  
  extract_mise_section "$start_marker" "$end_marker" | \
    grep -E '^[a-zA-Z0-9_-]+\s*=' | \
    grep -v '^#' | \
    grep -v '^\[' | \
    cut -d'=' -f1 | \
    sed 's/[[:space:]]*$//' | \
    sort
}

# Get tool description (hardcoded for now, could be enhanced later)
get_tool_description() {
  local tool="$1"
  case "$tool" in
    "opentofu") echo "OpenTofu - Open-source Terraform alternative" ;;
    "openbao") echo "OpenBao - Open-source Vault alternative" ;;
    "packer") echo "Packer - HashiCorp image builder" ;;
    "gitui") echo "gitui - Fast terminal UI for git repositories" ;;
    "tealdeer") echo "tealdeer - Fast implementation of tldr man pages" ;;
    "micro") echo "micro - Modern terminal-based text editor" ;;
    "powershell") echo "powershell - Microsoft PowerShell" ;;
    "cosign") echo "cosign - Container signing tool" ;;
    "kubectl") echo "kubectl - Kubernetes command-line tool" ;;
    "kubectx") echo "kubectx - Fast way to switch between clusters" ;;
    "kubens") echo "kubens - Fast way to switch between namespaces" ;;
    "k9s") echo "k9s - Terminal UI for Kubernetes clusters" ;;
    "helm") echo "Helm - The package manager for Kubernetes" ;;
    "krew") echo "krew - kubectl plugin manager" ;;
    "dive") echo "dive - Explore Docker image layers and optimize size" ;;
    "kubebench") echo "kubebench - CIS Kubernetes security benchmark" ;;
    "popeye") echo "popeye - Kubernetes cluster resource sanitizer" ;;
    "trivy") echo "trivy - Vulnerability scanner for containers & code" ;;
    "cmctl") echo "cmctl - CLI for cert-manager certificate management" ;;
    "k3d") echo "k3d - Lightweight Kubernetes for local development" ;;
    "golang") echo "golang - Go programming language" ;;
    "goreleaser") echo "goreleaser - Release automation tool for Go projects" ;;
    "dotnet") echo "dotnet - .NET SDK" ;;
    "node") echo "node - Node.js JavaScript runtime" ;;
    "pnpm") echo "pnpm - Fast, disk space efficient package manager" ;;
    "yarn") echo "yarn - Popular alternative package manager" ;;
    "deno") echo "deno - Secure TypeScript/JavaScript runtime" ;;
    "bun") echo "bun - Fast all-in-one JavaScript runtime" ;;
    *) echo "$tool - Development tool" ;;
  esac
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
  if [ "$INSTALL_OPENTOFU" = true ] || [ "$INSTALL_OPENBAO" = true ] || [ "$INSTALL_PACKER" = true ]; then
    echo "#### Begin HashiCorp Tools ####" >> "$temp_file"
    [ "$INSTALL_OPENTOFU" = true ] && echo "opentofu = \"${OPENTOFU_VERSION}\"" >> "$temp_file"
    [ "$INSTALL_OPENBAO" = true ] && echo "openbao = \"${OPENBAO_VERSION}\"" >> "$temp_file"
    [ "$INSTALL_PACKER" = true ] && echo "packer = \"${PACKER_VERSION}\"" >> "$temp_file"
    echo "#### End HashiCorp Tools ####" >> "$temp_file"
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

  # Miscellaneous Tools
  if [ "$INSTALL_GITUI" = true ] || [ "$INSTALL_TEALDEER" = true ] || [ "$INSTALL_MICRO" = true ] || [ "$INSTALL_POWERSHELL" = true ] || [ "$INSTALL_COSIGN" = true ]; then
    echo "" >> "$temp_file"
    echo "#### Begin Miscellaneous Tools ####" >> "$temp_file"
    [ "$INSTALL_GITUI" = true ] && echo 'gitui = "latest"' >> "$temp_file"
    [ "$INSTALL_TEALDEER" = true ] && echo 'tealdeer = "latest"' >> "$temp_file"
    [ "$INSTALL_MICRO" = true ] && echo 'micro = "latest"' >> "$temp_file"
    [ "$INSTALL_POWERSHELL" = true ] && echo 'powershell = "latest"' >> "$temp_file"
    [ "$INSTALL_COSIGN" = true ] && echo 'cosign = "latest"' >> "$temp_file"
    echo "#### End Miscellaneous Tools ####" >> "$temp_file"
  fi

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
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Go ####" "// #### End Go ####" >> "$temp_file"
  fi
  
  # Include .NET extensions if .NET was installed
  if [ "$INSTALL_DOTNET" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin .NET ####" "// #### End .NET ####" >> "$temp_file"
  fi
  
  # Include JavaScript/Node.js extensions if JavaScript tools were installed
  if [ "$INSTALL_JAVASCRIPT" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/Node.js ####" "// #### End JavaScript/Node.js ####" >> "$temp_file"
  fi
  
  # Include Python extensions if selected
  if [ "$INCLUDE_PYTHON_EXTENSIONS" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Python ####" "// #### End Python ####" >> "$temp_file"
  fi
  
  # Include Markdown extensions if selected
  if [ "$INCLUDE_MARKDOWN_EXTENSIONS" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Markdown ####" "// #### End Markdown ####" >> "$temp_file"
  fi
  
  # Include Shell/Bash extensions if selected
  if [ "$INCLUDE_SHELL_EXTENSIONS" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Shell/Bash ####" "// #### End Shell/Bash ####" >> "$temp_file"
  fi
  
  # Include Kubernetes extensions if any Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ] || [ "$INSTALL_KREW" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Kubernetes/Helm ####" "// #### End Kubernetes/Helm ####" >> "$temp_file"
  fi
  
  # Include Terraform/OpenTofu extensions if OpenTofu was installed
  if [ "$INSTALL_OPENTOFU" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Terraform/OpenTofu ####" "// #### End Terraform/OpenTofu ####" >> "$temp_file"
  fi
  
  # Include JavaScript/TypeScript extensions if Node.js was installed
  if [ "$INSTALL_NODE" = true ]; then
    INCLUDE_JS_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript ####" "// #### End JavaScript/TypeScript ####" >> "$temp_file"
  fi
  
  # Include Packer extensions if Packer was installed
  if [ "$INSTALL_PACKER" = true ]; then
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin Packer ####" "// #### End Packer ####" >> "$temp_file"
  fi
  
  # Always include Core Extensions
  # shellcheck disable=SC2129
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin Core Extensions ####" "// #### End Core Extensions ####" >> "$temp_file"

  # Remove trailing comma from the last extension entry
  last_ext_line=$(grep -n '^\s*".*",' "$temp_file" | tail -n 1 | cut -d: -f1)
  if [[ -n "$last_ext_line" ]]; then
    sed -i "${last_ext_line}s/,$//" "$temp_file"
  fi

  # Close extensions array and add settings
  echo "      ]," >> "$temp_file"

  # Add settings section
  echo '      "settings": {' >> "$temp_file"

  # Always include Core VS Code Settings
  extract_devcontainer_section "// #### Begin Core VS Code Settings ####" "// #### End Core VS Code Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  
  # Include Go settings if Go was installed
  if [ "$INSTALL_GO" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin Go Settings ####" "// #### End Go Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include .NET settings if .NET was installed
  if [ "$INSTALL_DOTNET" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin .NET Settings ####" "// #### End .NET Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include JavaScript/Node.js settings if JavaScript tools were installed
  if [ "$INSTALL_JAVASCRIPT" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin JavaScript/Node.js Settings ####" "// #### End JavaScript/Node.js Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include Python settings if Python extensions were selected
  if [ "$INCLUDE_PYTHON_EXTENSIONS" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin Python Settings ####" "// #### End Python Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include Markdown settings if Markdown extensions were selected
  if [ "$INCLUDE_MARKDOWN_EXTENSIONS" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin Markdown Settings ####" "// #### End Markdown Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include Shell/Bash settings if Shell extensions were selected
  if [ "$INCLUDE_SHELL_EXTENSIONS" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin Shell/Bash Settings ####" "// #### End Shell/Bash Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include Kubernetes settings if any Kubernetes tools were installed
  if [ "$INSTALL_KUBERNETES" = true ] || [ "$INSTALL_KREW" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin Kubernetes/Helm Settings ####" "// #### End Kubernetes/Helm Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include JavaScript/TypeScript settings if JS extensions were selected
  if [ "$INCLUDE_JS_EXTENSIONS" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript Settings ####" "// #### End JavaScript/TypeScript Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Include PowerShell settings if PowerShell was installed
  if [ "$INSTALL_POWERSHELL" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin PowerShell Settings ####" "// #### End PowerShell Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  fi
  
  # Always include the final settings blocks
  extract_devcontainer_section "// #### Begin Spell Checker Settings ####" "// #### End PSI Header Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  
  # Remove trailing comma from the last settings entry
  # Find the last line that's a top-level setting property (8 spaces indentation + quoted property)
  # This ensures we only target direct properties of the "settings" object, not nested properties
  last_setting_line=$(grep -n '^        "[^"]*":.*,$' "$temp_file" | tail -n 1 | cut -d: -f1)
  if [[ -n "$last_setting_line" ]]; then
      sed -i "${last_setting_line}s/,$//" "$temp_file"
  fi

  # Close settings and customizations
  echo '      }' >> "$temp_file"
  echo '    }' >> "$temp_file"
  echo '  }' >> "$temp_file"
  echo '}' >> "$temp_file"
  
  mv "$temp_file" "${project_path}/.devcontainer/devcontainer.json"
}

# Main TUI workflow
main() {
  # Handle help argument
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Dynamic Dev Container TUI Setup"
    echo ""
    echo "Usage: $0 <path-to-your-project>"
    echo ""
    echo "This script creates a development container configuration with a Terminal User Interface."
    echo "It will guide you through selecting development tools and configuring your project."
    echo ""
    echo "Arguments:"
    echo "  path-to-your-project    Path where the dev container will be created"
    echo ""
    echo "Options:"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 ~/my-project"
    echo "  $0 /workspace/new-project"
    exit 0
  fi
  
  check_dependencies
  source_colors
  
  # Verify we're in the correct directory by checking for required files
  if [[ ! -f ".devcontainer/devcontainer.json" ]] || [[ ! -f ".mise.toml" ]]; then
    dialog --title "Error" \
           --msgbox "Required template files not found.\n\nThis script must be run from the root of the dynamic-dev-container project directory.\n\nExpected files:\n- .devcontainer/devcontainer.json\n- .mise.toml" \
           12 60
    exit 1
  fi
  
  # Show welcome screen first
  show_welcome
  
  local project_path=""
  project_path="${1:-}"
  if [[ -z "${project_path}" ]]; then
    # Ask for project path via dialog
    project_path=$(tui_input "Project Path" \
                             "Enter the path where you want to create your development container:\n\nThis will be the root directory of your new project." \
                             "$HOME/my-new-project")
    
    if [[ -z "$project_path" ]]; then
      # User cancelled or provided empty path - ask for confirmation
      if tui_yesno "Exit Confirmation" "Are you sure you want to exit the setup?" "n"; then
        clear
        exit 0
      else
        # User wants to continue, ask for project path again
        project_path=$(tui_input "Project Path" \
                                 "Enter the path where you want to create your development container:\n\nThis will be the root directory of your new project." \
                                 "$HOME/my-new-project")
        
        # If they cancel again, exit gracefully
        if [[ -z "$project_path" ]]; then
          clear
          exit 0
        fi
      fi
    fi
  fi

  # Remove trailing slash from project_path if it exists
  project_path="${project_path%/}"

  # Create project directory if it doesn't exist
  create_project_directory "$project_path"

  # Collect project information
  if ! collect_project_info "$project_path"; then
    dialog --title "Error" --msgbox "Project configuration failed!" 8 40
    exit 1
  fi

  # Select development tools
  select_development_tools

  # Show configuration summary and confirm
  if ! show_summary; then
    clear
    dialog --title "Cancelled" --msgbox "Installation cancelled by user." 8 40
    exit 0
  fi

  # Clear screen and show progress
  clear
  echo "Installing dev container configuration..."
  echo "This may take a moment..."

  # Create .devcontainer directory
  mkdir -p "${project_path}/.devcontainer"

  # Copy directories to the destination
  for dir in "${DIRECTORIES_TO_COPY[@]}"; do
    if [[ -d "$dir" ]]; then
      cp -r "$dir"/* "${project_path}/$dir/" 2>/dev/null || true
    fi
  done
  
  # Copy files to the destination
  for file in "${FILES_TO_COPY[@]}"; do
    # Skip if file already exists in the target directory
    if [[ -f "${project_path}/$file" ]]; then
      echo "Skipping $file - already exists in target directory"
      continue
    fi
    
    if [[ -f "$file" ]]; then
      cp "$file" "${project_path}/$file" 2>/dev/null || true
      echo "Copied $file"
    fi
  done

  # Generate the customized configuration files
  generate_mise_toml "$project_path"
  generate_devcontainer_json "$project_path" "$PROJECT_NAME" "$CONTAINER_NAME" "$DISPLAY_NAME"

  # Update dev.sh with project settings
  update_dev_sh "$project_path" "$DOCKER_EXEC_COMMAND" "$PROJECT_NAME" "$CONTAINER_NAME"

  # Clean up dialog config
  rm -f $DIALOGRC

  # Show completion message
  clear
  echo -e "${GREEN}Installation completed successfully!${NC}"
  echo ""
  echo -e "${CYAN}Project Settings Applied:${NC}"
  echo -e "  Project Name: ${PROJECT_NAME}"
  echo -e "  Container Name: ${CONTAINER_NAME}"
  echo -e "  Display Name: ${DISPLAY_NAME}"
  [[ -n "$DOCKER_EXEC_COMMAND" ]] && echo -e "  Docker Exec Command: ${DOCKER_EXEC_COMMAND}"
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

# Make script executable and run main if not sourced
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
