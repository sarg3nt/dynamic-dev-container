#!/bin/bash
#
# TUI version of install.sh using dialog for a better user experience.
# Installs .devcontainer and other files into a project directory to use the dev container in a new project.
# cspell:ignore openbao myapp sudermanjr kubens DIALOGRC defaultno noconfirm pyproject sles

set -euo pipefail
IFS=$'\n\t'

# Global decision tracking variables
INSTALL_SECTIONS=()

# Individual tool flags - will be populated dynamically
declare -A TOOL_SELECTED
declare -A TOOL_VERSION_CONFIGURABLE
declare -A TOOL_VERSION_VALUE

# Extension flags
INCLUDE_PYTHON_EXTENSIONS=${INCLUDE_PYTHON_EXTENSIONS:-false}
INCLUDE_MARKDOWN_EXTENSIONS=${INCLUDE_MARKDOWN_EXTENSIONS:-false}
INCLUDE_SHELL_EXTENSIONS=${INCLUDE_SHELL_EXTENSIONS:-false}
INCLUDE_JS_EXTENSIONS=${INCLUDE_JS_EXTENSIONS:-false}

# Python Project Setup Configuration
INSTALL_PYTHON_TOOLS=false

# Python package repository configuration
PYTHON_PUBLISH_URL=""
PYTHON_INDEX_URL=""
PYTHON_EXTRA_INDEX_URL=""
PYTHON_DEV_SUFFIX=""
PYTHON_PROD_SUFFIX=""
PYTHON_REPOSITORY_TYPE=""

# Python project metadata configuration
PYTHON_PROJECT_NAME=""
PYTHON_PROJECT_DESCRIPTION=""
PYTHON_AUTHOR_NAME=""
PYTHON_AUTHOR_EMAIL=""
PYTHON_GITHUB_USERNAME=""
PYTHON_GITHUB_PROJECT=""
PYTHON_LICENSE=""
PYTHON_KEYWORDS=""

# PSI Header configuration
INSTALL_PSI_HEADER=false
PSI_HEADER_COMPANY=""
PSI_HEADER_TEMPLATES=()
declare -A PSI_HEADER_LANG_CONFIG

# Files and directories to copy to new projects
FILES_TO_COPY=(
  ".gitignore"
  ".krew_plugins"
  ".packages"
  "cspell.json"
  "dev.sh"
  "package.json"
  "run.sh"
  ".mise.toml"
)

# Python-specific files (copied only when INSTALL_PYTHON_TOOLS=true)
PYTHON_FILES_TO_COPY=(
  "pyproject.toml"
  "requirements.txt"
  "pybuild.py"
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

# Function to detect available container runtime
detect_container_runtime() {
  local container_cmd=""
  local runtime_type=""
  
  # Check for available container runtimes in order of preference
  if command -v docker >/dev/null 2>&1; then
    container_cmd="docker"
    runtime_type="docker"
  elif command -v podman >/dev/null 2>&1; then
    container_cmd="podman"
    runtime_type="podman"
  elif command -v nerdctl >/dev/null 2>&1; then
    container_cmd="nerdctl"
    runtime_type="nerdctl"
  elif command -v crictl >/dev/null 2>&1; then
    # crictl doesn't support running containers like docker/podman
    echo "ERROR: crictl found but it doesn't support running containers. Please install docker, podman, or nerdctl." >&2
    return 1
  elif command -v buildah >/dev/null 2>&1; then
    # buildah is primarily for building, not running containers
    echo "ERROR: buildah found but it's for building images. Please install docker, podman, or nerdctl for running containers." >&2
    return 1
  else
    return 1
  fi
  
  echo "$container_cmd:$runtime_type"
  return 0
}

# Function to run container command based on detected runtime
run_container_command() {
  local image="$1"
  shift
  local container_info
  local container_cmd
  local runtime_type
  
  container_info=$(detect_container_runtime 2>/dev/null)
  if [[ $? -ne 0 ]]; then
    return 1
  fi
  
  container_cmd=$(echo "$container_info" | cut -d':' -f1)
  runtime_type=$(echo "$container_info" | cut -d':' -f2)
  
  case "$runtime_type" in
    "docker"|"podman"|"nerdctl")
      $container_cmd run --rm --quiet "$image" "$@" 2>/dev/null
      ;;
    *)
      return 1
      ;;
  esac
}

# Get latest major versions for a tool
get_latest_major_versions() {
  local tool_name="$1"
  local versions
  
  # Special handling for Python versions
  if [[ "$tool_name" == "python" ]]; then
    # Fetch remote versions using mise, handle potential errors, and filter for standard CPython versions
    if command -v mise >/dev/null 2>&1; then
      versions=$(mise ls-remote "$tool_name" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | grep -v -E 'rc|alpha|beta' 2>/dev/null || echo "")
    elif detect_container_runtime >/dev/null 2>&1; then
      versions=$(run_container_command jdxcode/mise mise ls-remote "$tool_name" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | grep -v -E 'rc|alpha|beta' 2>/dev/null || echo "")
    else
      echo "ERROR: Neither mise nor any container runtime (docker/podman/nerdctl) is available." >&2
      echo ""
      return
    fi
    
    if [[ -z "$versions" ]]; then
      # Fallback to common Python versions if mise fails
      echo "(e.g., 3.13, 3.12, 3.11, 3.10)"
      return
    fi
    
    # For Python, get major.minor versions (e.g., 3.13, 3.12, 3.11)
    local major_versions
    major_versions=$(echo "$versions" | awk -F. '{print $1"."$2}' | sort -rV | uniq | head -n 5 | tr '\n' ',' | sed 's/,$//')
    
    if [[ -n "$major_versions" ]]; then
      echo "(e.g., ${major_versions})"
    else
      echo "(e.g., 3.13, 3.12, 3.11, 3.10)"
    fi
    return
  fi
  
  # Fetch remote versions using mise, handle potential errors, and filter out pre-release versions
  if command -v mise >/dev/null 2>&1; then
    versions=$(mise ls-remote "$tool_name" 2>/dev/null | grep -v -E 'rc|alpha|beta' 2>/dev/null || echo "")
  elif detect_container_runtime >/dev/null 2>&1; then
    versions=$(run_container_command jdxcode/mise mise ls-remote "$tool_name" 2>/dev/null | grep -v -E 'rc|alpha|beta' 2>/dev/null || echo "")
  else
    echo "ERROR: Neither mise nor any container runtime (docker/podman/nerdctl) is available." >&2
    echo ""
    return
  fi
  
  if [[ -z "$versions" ]]; then
    echo ""
    return
  fi
  
  local major_versions
  # Parse versions to get unique major versions, sorted numerically
  if [[ "$tool_name" == "kubectl" || "$tool_name" == "go" || "$tool_name" == "golang" || "$tool_name" == "opentofu" || "$tool_name" == "openbao" || "$tool_name" == "packer" ]]; then
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

# Parse tool sections from .mise.toml
parse_mise_sections() {
  local file=".mise.toml"
  local in_tools_section=false
  local current_section=""
  local current_section_name=""
  local current_tools=()
  local previous_line=""
  
  # Clear global arrays
  INSTALL_SECTIONS=()
  
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Check if we're entering the [tools] section
    if [[ "$line" == "[tools]" ]]; then
      in_tools_section=true
      continue
    fi
    
    # Check if we're leaving the [tools] section
    if [[ "$in_tools_section" == true && "$line" =~ ^\[.*\] ]]; then
      # Save the last section if it exists
      if [[ -n "$current_section" ]]; then
        INSTALL_SECTIONS+=("$current_section")
      fi
      break
    fi
    
    # Only process lines within the [tools] section
    if [[ "$in_tools_section" == true ]]; then
      # Check for section start marker
      if [[ "$line" =~ ^####\ Begin\ (.+)$ ]]; then
        # Save previous section if it exists
        if [[ -n "$current_section" ]]; then
          INSTALL_SECTIONS+=("$current_section")
        fi
        
        # Start new section
        current_section_name="${BASH_REMATCH[1]}"
        current_section="$current_section_name"
        current_tools=()
        continue
      fi
      
      # Check for section end marker
      if [[ "$line" =~ ^####\ End\ (.+)$ ]]; then
        # Save current section
        if [[ -n "$current_section" ]]; then
          INSTALL_SECTIONS+=("$current_section")
        fi
        current_section=""
        current_section_name=""
        continue
      fi
      
      # Check for tool definition within a section
      if [[ -n "$current_section" && "$line" =~ ^([a-zA-Z0-9_-]+)\ *=\ * ]]; then
        local tool_name="${BASH_REMATCH[1]}"
        current_tools+=("$tool_name")
        
        # Check if previous line had #version# marker for this specific tool
        if [[ "$previous_line" == "#version#" ]]; then
          TOOL_VERSION_CONFIGURABLE["$tool_name"]=true
        else
          TOOL_VERSION_CONFIGURABLE["$tool_name"]=false
        fi
        
        # Initialize tool as not selected
        TOOL_SELECTED["$tool_name"]=false
        TOOL_VERSION_VALUE["$tool_name"]="latest"
      fi
    fi
    
    previous_line="$line"
  done < "$file"
  
  # Save the last section if it exists
  if [[ -n "$current_section" ]]; then
    INSTALL_SECTIONS+=("$current_section")
  fi
}

# Get tools from a specific section
get_section_tools() {
  local section_name="$1"
  local file=".mise.toml"
  local in_section=false
  local tools=()
  
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "#### Begin $section_name" ]]; then
      in_section=true
      continue
    fi
    
    if [[ "$line" == "#### End $section_name" ]]; then
      break
    fi
    
    if [[ "$in_section" == true && "$line" =~ ^([a-zA-Z0-9_-]+)\ *=\ * ]]; then
      tools+=("${BASH_REMATCH[1]}")
    fi
  done < "$file"
  
  printf '%s\n' "${tools[@]}"
}

#TUI input dialog with default value
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

# Configure Python package repositories
configure_python_repositories() {
  local repo_type
  repo_type=$(dialog --title "Python Package Repository" \
                    --menu "Choose your Python package repository type:" \
                    $DIALOG_HEIGHT $DIALOG_WIDTH 10 \
                    "pypi" "PyPI (python.org) - Default public repository" \
                    "artifactory" "JFrog Artifactory - Enterprise repository" \
                    "nexus" "Nexus Repository - Enterprise repository" \
                    "custom" "Custom repository URLs" \
                    3>&1 1>&2 2>&3 3>&-)
  
  case "$repo_type" in
    "pypi")
      PYTHON_REPOSITORY_TYPE="pypi"
      PYTHON_PUBLISH_URL="https://upload.pypi.org/legacy/"
      PYTHON_INDEX_URL="https://pypi.org/simple/"
      PYTHON_EXTRA_INDEX_URL=""
      PYTHON_DEV_SUFFIX=""
      PYTHON_PROD_SUFFIX=""
      ;;
    "artifactory")
      PYTHON_REPOSITORY_TYPE="artifactory"
      configure_artifactory_urls
      ;;
    "nexus")
      PYTHON_REPOSITORY_TYPE="nexus"
      configure_nexus_urls
      ;;
    "custom")
      PYTHON_REPOSITORY_TYPE="custom"
      configure_custom_urls
      ;;
    *)
      # Default to PyPI if cancelled
      PYTHON_REPOSITORY_TYPE="pypi"
      PYTHON_PUBLISH_URL="https://upload.pypi.org/legacy/"
      PYTHON_INDEX_URL="https://pypi.org/simple/"
      PYTHON_EXTRA_INDEX_URL=""
      PYTHON_DEV_SUFFIX=""
      PYTHON_PROD_SUFFIX=""
      ;;
  esac
}

# Configure Artifactory URLs
configure_artifactory_urls() {
  local form_result
  form_result=$(tui_form "Artifactory Configuration" \
                        "Enter your Artifactory repository configuration:" \
                        "Server URL:" 1 1 "https://your-artifactory.com" 1 15 50 0 \
                        "Repository Name:" 2 1 "your-pypi-repo" 2 20 30 0 \
                        "Dev Suffix:" 3 1 "-dev" 3 15 20 0 \
                        "Prod Suffix:" 4 1 "" 4 16 20 0)
  
  if [[ -n "$form_result" ]]; then
    local server_url repository_name dev_suffix prod_suffix
    server_url=$(echo "$form_result" | sed -n '1p')
    repository_name=$(echo "$form_result" | sed -n '2p')
    dev_suffix=$(echo "$form_result" | sed -n '3p')
    prod_suffix=$(echo "$form_result" | sed -n '4p')
    
    PYTHON_PUBLISH_URL="${server_url}/artifactory/api/pypi/${repository_name}"
    PYTHON_INDEX_URL="${server_url}/artifactory/api/pypi/${repository_name}/simple"
    PYTHON_EXTRA_INDEX_URL=""
    PYTHON_DEV_SUFFIX="$dev_suffix"
    PYTHON_PROD_SUFFIX="$prod_suffix"
  fi
}

# Configure Nexus URLs
configure_nexus_urls() {
  local form_result
  form_result=$(tui_form "Nexus Configuration" \
                        "Enter your Nexus repository configuration:" \
                        "Server URL:" 1 1 "https://your-nexus.com" 1 15 50 0 \
                        "Repository Name:" 2 1 "pypi-internal" 2 20 30 0 \
                        "Dev Suffix:" 3 1 "-dev" 3 15 20 0 \
                        "Prod Suffix:" 4 1 "" 4 16 20 0)
  
  if [[ -n "$form_result" ]]; then
    local server_url repository_name dev_suffix prod_suffix
    server_url=$(echo "$form_result" | sed -n '1p')
    repository_name=$(echo "$form_result" | sed -n '2p')
    dev_suffix=$(echo "$form_result" | sed -n '3p')
    prod_suffix=$(echo "$form_result" | sed -n '4p')
    
    PYTHON_PUBLISH_URL="${server_url}/repository/${repository_name}/"
    PYTHON_INDEX_URL="${server_url}/repository/${repository_name}/simple"
    PYTHON_EXTRA_INDEX_URL=""
    PYTHON_DEV_SUFFIX="$dev_suffix"
    PYTHON_PROD_SUFFIX="$prod_suffix"
  fi
}

# Configure custom URLs
configure_custom_urls() {
  local form_result
  form_result=$(tui_form "Custom Repository Configuration" \
                        "Enter your custom repository URLs:" \
                        "Publish URL:" 1 1 "" 1 15 60 0 \
                        "Index URL:" 2 1 "" 2 13 60 0 \
                        "Extra Index URL:" 3 1 "" 3 19 60 0 \
                        "Dev Suffix:" 4 1 "-dev" 4 15 20 0 \
                        "Prod Suffix:" 5 1 "" 5 16 20 0)
  
  if [[ -n "$form_result" ]]; then
    PYTHON_PUBLISH_URL=$(echo "$form_result" | sed -n '1p')
    PYTHON_INDEX_URL=$(echo "$form_result" | sed -n '2p')
    PYTHON_EXTRA_INDEX_URL=$(echo "$form_result" | sed -n '3p')
    PYTHON_DEV_SUFFIX=$(echo "$form_result" | sed -n '4p')
    PYTHON_PROD_SUFFIX=$(echo "$form_result" | sed -n '5p')
  fi
}

# Configure Python project metadata
configure_python_project() {
  if ! tui_yesno "Python Project Configuration" "Configure Python project metadata in pyproject.toml?" "y"; then
    return
  fi

  # Project basic information
  local form_result
  form_result=$(tui_form "Python Project Information" \
                        "Enter your Python project details:" \
                        "Project Name:" 1 1 "$PROJECT_NAME" 1 15 40 0 \
                        "Description:" 2 1 "A brief description of your project" 2 14 60 0 \
                        "License:" 3 1 "MIT" 3 11 20 0 \
                        "Keywords:" 4 1 "python,cli,automation" 4 12 50 0)
  
  if [[ -n "$form_result" ]]; then
    PYTHON_PROJECT_NAME=$(echo "$form_result" | sed -n '1p')
    PYTHON_PROJECT_DESCRIPTION=$(echo "$form_result" | sed -n '2p')
    PYTHON_LICENSE=$(echo "$form_result" | sed -n '3p')
    PYTHON_KEYWORDS=$(echo "$form_result" | sed -n '4p')
  fi

  # Author information
  form_result=$(tui_form "Author Information" \
                        "Enter author details:" \
                        "Author Name:" 1 1 "Your Name" 1 15 40 0 \
                        "Author Email:" 2 1 "your.email@example.com" 2 16 50 0)
  
  if [[ -n "$form_result" ]]; then
    PYTHON_AUTHOR_NAME=$(echo "$form_result" | sed -n '1p')
    PYTHON_AUTHOR_EMAIL=$(echo "$form_result" | sed -n '2p')
  fi

  # GitHub information for URLs
  form_result=$(tui_form "GitHub Repository Information" \
                        "Enter GitHub details for project URLs:" \
                        "GitHub Username:" 1 1 "yourusername" 1 18 30 0 \
                        "GitHub Project:" 2 1 "${PYTHON_PROJECT_NAME:-my-awesome-project}" 2 17 40 0)
  
  if [[ -n "$form_result" ]]; then
    PYTHON_GITHUB_USERNAME=$(echo "$form_result" | sed -n '1p')
    PYTHON_GITHUB_PROJECT=$(echo "$form_result" | sed -n '2p')
  fi
}

# Configure PSI Header extension and settings
configure_psi_header() {
  if ! tui_yesno "PSI Header Configuration" "Would you like to install and configure the PSI Header extension?\n\nPSI Header automatically adds file headers to your source code files with information like author, company, creation date, etc." "n"; then
    INSTALL_PSI_HEADER=false
    return
  fi
  
  INSTALL_PSI_HEADER=true
  
  # Get company name
  PSI_HEADER_COMPANY=$(tui_input "Company Information" \
                                 "Enter your company name for file headers:" \
                                 "My Company")
  
  if [[ -z "$PSI_HEADER_COMPANY" ]]; then
    PSI_HEADER_COMPANY="My Company"
  fi
  
  # Configure templates for each selected language
  local available_languages=()
  local language_descriptions=()
  
  # Determine which languages to configure based on selected tools
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      case "$tool" in
        "go"|"golang")
          available_languages+=("go")
          language_descriptions+=("go" "Go programming language files")
          ;;
        "dotnet")
          available_languages+=("csharp")
          language_descriptions+=("csharp" "C# programming language files")
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          available_languages+=("javascript" "typescript")
          language_descriptions+=("javascript" "JavaScript files" "typescript" "TypeScript files")
          ;;
        "python")
          available_languages+=("python")
          language_descriptions+=("python" "Python programming language files")
          ;;
        "powershell")
          available_languages+=("powershell")
          language_descriptions+=("powershell" "PowerShell script files")
          ;;
        "opentofu")
          available_languages+=("terraform")
          language_descriptions+=("terraform" "Terraform/OpenTofu configuration files")
          ;;
      esac
    fi
  done
  
  # Always include common languages
  available_languages+=("shellscript" "markdown")
  language_descriptions+=("shellscript" "Shell/Bash script files" "markdown" "Markdown documentation files")
  
  # Remove duplicates and sort
  mapfile -t available_languages < <(printf '%s\n' "${available_languages[@]}" | sort -u)
  
  # Configure templates for each language
  for language in "${available_languages[@]}"; do
    local template_text
    local default_template
    default_template="Copyright © $(date +%Y) $PSI_HEADER_COMPANY. All rights reserved."
    
    case "$language" in
      "powershell")
        default_template=".DESCRIPTION - Copyright © $(date +%Y) $PSI_HEADER_COMPANY. All rights reserved."
        ;;
      "markdown")
        default_template="Copyright © $(date +%Y) $PSI_HEADER_COMPANY. All rights reserved."
        ;;
    esac
    
    # Special instructions for PowerShell
    local input_prompt="Enter the template text for $language files:\n\nThis text will be automatically added to the top of new $language files."
    if [[ "$language" == "powershell" ]]; then
        input_prompt="Enter the template text for PowerShell files:\n\nNote: For PowerShell, use '.DESCRIPTION - ' followed by your text.\nThe script will automatically format it correctly as:\n.DESCRIPTION\nYour text here"
    fi
    
    template_text=$(tui_input "Template for $language" \
                              "$input_prompt" \
                              "$default_template")
    
    if [[ -n "$template_text" ]]; then
      # Special processing for PowerShell templates
      if [[ "$language" == "powershell" && "$template_text" == *".DESCRIPTION - "* ]]; then
        # Convert ".DESCRIPTION - text" to proper multiline format
        local description_text="${template_text#*.DESCRIPTION - }"
        template_text=".DESCRIPTION
$description_text"
      fi
      
      # Use a delimiter that won't appear in templates
      PSI_HEADER_TEMPLATES+=("$language|||$template_text")
    fi
  done
}

# Development tools selection
# shellcheck disable=SC2120  # Function uses positional parameters set by eval
select_development_tools() {
  # Parse the .mise.toml file to discover sections and tools
  parse_mise_sections
  
  # Process each section found in .mise.toml
  for section in "${INSTALL_SECTIONS[@]}"; do
    local section_tools=()
    
    # Get tools for this section
    while IFS= read -r tool; do
      [[ -n "$tool" ]] && section_tools+=("$tool")
    done < <(get_section_tools "$section")
    
    # Skip empty sections
    if [[ ${#section_tools[@]} -eq 0 ]]; then
      continue
    fi
    
    # Ask user if they want to install tools from this section
    if tui_yesno "$section" "Install $section?" "n"; then
      
      # Build options for all tools in this section
      local tool_options=()
      for tool in "${section_tools[@]}"; do
        local description
        description=$(get_tool_description "$tool")
        
        # Add version info to description for version-configurable tools
        if [[ "${TOOL_VERSION_CONFIGURABLE[$tool]:-false}" == "true" ]]; then
          local version_examples
          version_examples=$(get_latest_major_versions "$tool")
          description="$description (version configurable $version_examples)"
        fi
        
        tool_options+=("$tool" "$description" "on")
      done
      
      # Show checklist for all tools in this section
      local selected_tools
      selected_tools=$(tui_checklist "$section Tools" \
                                     "Select tools to install from $section:" \
                                     "${tool_options[@]}")
      
      # Mark selected tools and ask for versions if needed
      # Parse the quoted tool names returned by dialog
      eval "set -- $selected_tools"
      for tool in "$@"; do
        TOOL_SELECTED["$tool"]=true
        
        # If this tool is version-configurable, ask for the version
        if [[ "${TOOL_VERSION_CONFIGURABLE[$tool]:-false}" == "true" ]]; then
          local version_examples
          version_examples=$(get_latest_major_versions "$tool")
          local tool_desc
          tool_desc=$(get_tool_description "$tool")
          
          local version
          version=$(tui_input "$tool Configuration" \
                             "Enter $tool version to install $version_examples\n\n$tool_desc:" \
                             "latest")
          
          TOOL_VERSION_VALUE["$tool"]="$version"
        else
          TOOL_VERSION_VALUE["$tool"]="latest"
        fi
        
        # Special handling for Python: configure Python project after Python tool is selected
        if [[ "$tool" == "python" ]]; then
          INSTALL_PYTHON_TOOLS=true
          INCLUDE_PYTHON_EXTENSIONS=true  # Ensure Python extensions are included
          
          # Ask if user wants to configure a Python project
          if tui_yesno "Python Project Setup" "Configure Python project files and metadata?\n\nThis will:\n• Copy Python build tools (pybuild.py)\n• Copy Python configuration files (pyproject.toml, requirements.txt)\n• Guide you through project configuration\n\nSelect 'No' if you only want Python runtime without project setup." "y"; then
            configure_python_repositories
            configure_python_project
          fi
        fi
      done
    fi
  done

  # VS Code Extensions (for tools without automatic extensions)
  local extensions
  extensions=$(tui_checklist "VS Code Extensions" \
                            "Select VS Code extension categories to include.\nNote: Extensions for selected dev tools are automatically included:" \
                            "markdown" "Markdown - Enhanced editing and preview extensions" on \
                            "shell" "Shell/Bash - Scripting and development extensions" on)
  
  # Parse the quoted dialog output properly
  if [[ -n "$extensions" ]]; then
    eval "set -- $extensions"
    for ext in "$@"; do
      case "$ext" in
        "markdown") INCLUDE_MARKDOWN_EXTENSIONS=true ;;
        "shell") INCLUDE_SHELL_EXTENSIONS=true ;;
      esac
    done
  fi
  
  # Configure PSI Header extension
  configure_psi_header
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
  
  # Count and display selected tools by section
  local tool_count=0
  local tools_section=""
  
  # Group tools by their sections
  for section in "${INSTALL_SECTIONS[@]}"; do
    local section_tools=()
    local section_has_selected=false
    
    # Get all tools in this section and check if any are selected
    while IFS= read -r tool; do
      if [[ -n "$tool" && "${TOOL_SELECTED[$tool]}" == "true" ]]; then
        section_tools+=("$tool")
        section_has_selected=true
      fi
    done < <(get_section_tools "$section")
    
    # If this section has selected tools, add to summary
    if [[ "$section_has_selected" == "true" && ${#section_tools[@]} -gt 0 ]]; then
      tools_section+="  ✓ $section: "
      local tool_list=""
      for tool in "${section_tools[@]}"; do
        local version="${TOOL_VERSION_VALUE[$tool]:-latest}"
        if [[ "$version" != "latest" ]]; then
          tool_list+="$tool ($version), "
        else
          tool_list+="$tool, "
        fi
      done
      # Remove trailing comma and space
      tool_list=${tool_list%, }
      tools_section+="$tool_list\n"
      ((tool_count++))
    fi
  done
  
  if [[ $tool_count -gt 0 ]]; then
    summary+="Development Tools ($tool_count sections):\n$tools_section"
  else
    summary+="Development Tools: None selected\n"
  fi
  summary+="\n"
  
  # VS Code extensions
  local ext_count=0
  local ext_list=""
  
  # Automatic extensions based on selected tools
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      case "$tool" in
        "go") ext_list+="Go "; ((ext_count++)) ;;
        "dotnet") ext_list+=".NET "; ((ext_count++)) ;;
        "node") ext_list+="JavaScript/Node.js "; ((ext_count++)) ;;
        "kubectl"|"helm"|"k9s") ext_list+="Kubernetes/Helm "; ((ext_count++)) ;;
        "opentofu") ext_list+="Terraform/OpenTofu "; ((ext_count++)) ;;
        "packer") ext_list+="Packer "; ((ext_count++)) ;;
        "powershell") ext_list+="PowerShell "; ((ext_count++)) ;;
      esac
    fi
  done
  
  # Optional extensions selected by user
  [[ "$INCLUDE_PYTHON_EXTENSIONS" == "true" ]] && { ext_list+="Python "; ((ext_count++)); }
  [[ "$INCLUDE_MARKDOWN_EXTENSIONS" == "true" ]] && { ext_list+="Markdown "; ((ext_count++)); }
  [[ "$INCLUDE_SHELL_EXTENSIONS" == "true" ]] && { ext_list+="Shell/Bash "; ((ext_count++)); }
  [[ "$INSTALL_PSI_HEADER" == "true" ]] && { ext_list+="PSI Header "; ((ext_count++)); }
  
  if [[ $ext_count -gt 0 ]]; then
    summary+="VS Code Extensions: GitHub + Core + $ext_list\n"
  else
    summary+="VS Code Extensions: GitHub + Core extensions only\n"
  fi
  
  # PSI Header configuration
  if [[ "$INSTALL_PSI_HEADER" == "true" ]]; then
    summary+="\nPSI Header Configuration:\n"
    summary+="  • Company: $PSI_HEADER_COMPANY\n"
    summary+="  • Templates configured for: ${#PSI_HEADER_TEMPLATES[@]} languages\n"
  fi
  
  # Python repository configuration
  if [[ "$INSTALL_PYTHON_TOOLS" == "true" && -n "$PYTHON_PUBLISH_URL" ]]; then
    summary+="\nPython Package Repository:\n"
    summary+="  • Publish URL: $PYTHON_PUBLISH_URL\n"
    summary+="  • Index URL: $PYTHON_INDEX_URL\n"
    [[ -n "$PYTHON_EXTRA_INDEX_URL" ]] && summary+="  • Extra Index: $PYTHON_EXTRA_INDEX_URL\n"
    [[ -n "$PYTHON_DEV_SUFFIX" ]] && summary+="  • Dev Suffix: $PYTHON_DEV_SUFFIX\n"
  fi
  
  # Python project configuration
  if [[ "$INSTALL_PYTHON_TOOLS" == "true" && -n "$PYTHON_PROJECT_NAME" ]]; then
    summary+="\nPython Project Configuration:\n"
    summary+="  • Project Name: $PYTHON_PROJECT_NAME\n"
    [[ -n "$PYTHON_PROJECT_DESCRIPTION" ]] && summary+="  • Description: $PYTHON_PROJECT_DESCRIPTION\n"
    [[ -n "$PYTHON_AUTHOR_NAME" ]] && summary+="  • Author: $PYTHON_AUTHOR_NAME\n"
    [[ -n "$PYTHON_AUTHOR_EMAIL" ]] && summary+="  • Email: $PYTHON_AUTHOR_EMAIL\n"
    [[ -n "$PYTHON_LICENSE" ]] && summary+="  • License: $PYTHON_LICENSE\n"
    [[ -n "$PYTHON_GITHUB_USERNAME" && -n "$PYTHON_GITHUB_PROJECT" ]] && summary+="  • GitHub: $PYTHON_GITHUB_USERNAME/$PYTHON_GITHUB_PROJECT\n"
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
    "golangci-lint") echo "golangci-lint - Fast Go linters runner" ;;
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
  
  if [[ ! -f "$file" ]]; then
    return 1
  fi
  
  # Escape forward slashes for sed pattern matching
  local escaped_start_marker="${start_marker//\//\\/}"
  local escaped_end_marker="${end_marker//\//\\/}"
  
  # Use sed to extract the specific section between exact markers
  sed -n "/${escaped_start_marker}/,/${escaped_end_marker}/p" "$file"
}

# Generate custom .mise.toml
generate_mise_toml() {
  local project_path="$1"
  local temp_file="${project_path}/.mise.toml.tmp"
  
  # Start with the header and environment section from source
  echo "# cspell:ignore cmctl gitui krew kubebench kubectx kubens direnv dotenv looztra kompiro kforsthoevel sarg kubeseal stefansedich nlamirault zufardhiyaulhaq sudermanjr" > "$temp_file"
  # shellcheck disable=SC2129
  extract_mise_section "#### Begin Environment" "#### End Environment" >> "$temp_file"
  echo "" >> "$temp_file"
  echo "[tools]" >> "$temp_file"
  echo "" >> "$temp_file"

  # Generate sections based on selected tools and their sections
  for section in "${INSTALL_SECTIONS[@]}"; do
    local section_has_tools=false
    local section_tools=()
    
    # Collect selected tools for this section
    while IFS= read -r tool; do
      if [[ -n "$tool" && "${TOOL_SELECTED[$tool]}" == "true" ]]; then
        section_tools+=("$tool")
        section_has_tools=true
      fi
    done < <(get_section_tools "$section")
    
    # If section has selected tools, generate the section
    if [[ "$section_has_tools" == "true" && ${#section_tools[@]} -gt 0 ]]; then
      echo "#### Begin $section" >> "$temp_file"
      
      for tool in "${section_tools[@]}"; do
        local version="${TOOL_VERSION_VALUE[$tool]:-latest}"
        echo "$tool = \"$version\"" >> "$temp_file"
      done
      
      echo "#### End $section" >> "$temp_file"
      echo "" >> "$temp_file"
    fi
  done

  # Add alias section from source (if it exists)
  if grep -q "^\[alias\]" .mise.toml; then
    echo "" >> "$temp_file"
    # Extract everything from [alias] to the next section or end of file
    awk '/^\[alias\]/{found=1} found && /^\[/ && !/^\[alias\]/{found=0} found{print}' .mise.toml >> "$temp_file"
  fi
  
  # Add settings section from source (if it exists)  
  if grep -q "^\[settings\]" .mise.toml; then
    echo "" >> "$temp_file"
    # Extract everything from [settings] to the end of file
    awk '/^\[settings\]/{found=1} found{print}' .mise.toml >> "$temp_file"
  fi

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

# Generate the [tool.pybuild] section based on selected repository type
generate_pybuild_section() {
  local pyproject_file="$1"
  
  # Find the start and end of the [tool.pybuild] section
  local start_line end_line
  start_line=$(grep -n "^# Python Package Repository Configuration" "$pyproject_file" | cut -d: -f1)
  end_line=$(grep -n "^# Development environment configuration for Hatch" "$pyproject_file" | cut -d: -f1)
  
  if [[ -n "$start_line" && -n "$end_line" ]]; then
    # Create the new pybuild section content
    local new_content=""
    case "$PYTHON_REPOSITORY_TYPE" in
      "pypi")
        new_content="# Python Package Repository Configuration
# Configure these settings for your package repository (PyPI, Artifactory, Nexus, etc.)
[tool.pybuild]
# PyPI configuration (public repository)
publish_base_url = \"$PYTHON_PUBLISH_URL\"
install_index_url = \"$PYTHON_INDEX_URL\"
install_extra_index_url = \"$PYTHON_EXTRA_INDEX_URL\"

# Environment suffixes (optional) - used for environment-specific repository URLs
dev_suffix = \"$PYTHON_DEV_SUFFIX\"
prod_suffix = \"$PYTHON_PROD_SUFFIX\"

# Authentication Note:
# Set these environment variables for repository authentication:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
# These variables are used by the pybuild.py script for repository authentication.
"
        ;;
      "artifactory")
        new_content="# Python Package Repository Configuration
# Configure these settings for your package repository (PyPI, Artifactory, Nexus, etc.)
[tool.pybuild]
# JFrog Artifactory configuration
publish_base_url = \"$PYTHON_PUBLISH_URL\"
install_index_url = \"$PYTHON_INDEX_URL\"
install_extra_index_url = \"$PYTHON_EXTRA_INDEX_URL\"

# Environment suffixes for development/production environments
dev_suffix = \"$PYTHON_DEV_SUFFIX\"
prod_suffix = \"$PYTHON_PROD_SUFFIX\"

# Authentication Note:
# Set these environment variables for repository authentication:
#   export HATCH_INDEX_USER=your_artifactory_username
#   export HATCH_INDEX_AUTH=your_artifactory_password_or_token
# These variables are used by the pybuild.py script for repository authentication.
"
        ;;
      "nexus")
        new_content="# Python Package Repository Configuration
# Configure these settings for your package repository (PyPI, Artifactory, Nexus, etc.)
[tool.pybuild]
# Nexus Repository configuration
publish_base_url = \"$PYTHON_PUBLISH_URL\"
install_index_url = \"$PYTHON_INDEX_URL\"
install_extra_index_url = \"$PYTHON_EXTRA_INDEX_URL\"

# Environment suffixes for development/production environments
dev_suffix = \"$PYTHON_DEV_SUFFIX\"
prod_suffix = \"$PYTHON_PROD_SUFFIX\"

# Authentication Note:
# Set these environment variables for repository authentication:
#   export HATCH_INDEX_USER=your_nexus_username
#   export HATCH_INDEX_AUTH=your_nexus_password_or_token
# These variables are used by the pybuild.py script for repository authentication.
"
        ;;
      "custom")
        new_content="# Python Package Repository Configuration
# Configure these settings for your package repository (PyPI, Artifactory, Nexus, etc.)
[tool.pybuild]
# Custom repository configuration
publish_base_url = \"$PYTHON_PUBLISH_URL\"
install_index_url = \"$PYTHON_INDEX_URL\"
install_extra_index_url = \"$PYTHON_EXTRA_INDEX_URL\"

# Environment suffixes for development/production environments
dev_suffix = \"$PYTHON_DEV_SUFFIX\"
prod_suffix = \"$PYTHON_PROD_SUFFIX\"

# Authentication Note:
# Set these environment variables for repository authentication:
#   export HATCH_INDEX_USER=your_username
#   export HATCH_INDEX_AUTH=your_password_or_token
# These variables are used by the pybuild.py script for repository authentication.
"
        ;;
    esac
    
    # Create a temporary file with the replacement content
    local temp_file="${pyproject_file}.tmp"
    head -n $((start_line - 1)) "$pyproject_file" > "$temp_file"
    echo -n "$new_content" >> "$temp_file"
    tail -n +$((end_line)) "$pyproject_file" >> "$temp_file"
    
    # Replace the original file
    mv "$temp_file" "$pyproject_file"
  fi
}

# Generate custom PSI Header settings
generate_psi_header_settings() {
  local temp_file="$1"
  
  echo "DEBUG: Starting generate_psi_header_settings function" >&2
  echo "DEBUG: PSI_HEADER_COMPANY: $PSI_HEADER_COMPANY" >&2
  echo "DEBUG: PSI_HEADER_TEMPLATES array length: ${#PSI_HEADER_TEMPLATES[@]}" >&2
  
  # Add PSI Header settings comment
  echo "DEBUG: Adding PSI Header settings comment" >&2
  echo '        // #### Begin PSI Header Settings ####' >> "$temp_file"
  
  # Company configuration - escape quotes in company name
  echo "DEBUG: Adding company configuration" >&2
  local escaped_company
  escaped_company=$(echo "$PSI_HEADER_COMPANY" | sed 's/"/\\"/g')
  echo '        "psi-header.config": {' >> "$temp_file"
  echo "          \"company\": \"$escaped_company\"" >> "$temp_file"
  echo '        },' >> "$temp_file"
  
  # Changes tracking configuration
  echo "DEBUG: Adding changes tracking configuration" >&2
  echo '        "psi-header.changes-tracking": {' >> "$temp_file"
  echo '          "autoHeader": "autoSave",' >> "$temp_file"
  echo '          "exclude": ["json"],' >> "$temp_file"
  echo '          "excludeGlob": ["**/.git/**"]' >> "$temp_file"
  echo '        },' >> "$temp_file"
  
  # Project creation year (current year)
  echo "DEBUG: Adding project creation year" >&2
  local current_year
  current_year=$(date +%Y)
  echo "        \"psi-header.variables\": [[\"projectCreationYear\", \"$current_year\"]]," >> "$temp_file"
  
  # Language configurations - include all available languages from the devcontainer.json
  echo "DEBUG: Starting language configurations" >&2
  echo '        "psi-header.lang-config": [' >> "$temp_file"
  
  # Default configuration for all languages
  echo '          {' >> "$temp_file"
  echo '            "language": "*",' >> "$temp_file"
  echo '            "begin": "",' >> "$temp_file"
  echo '            "end": "",' >> "$temp_file"
  echo '            "prefix": "// "' >> "$temp_file"
  echo '          },' >> "$temp_file"
  
  # Add language-specific configurations only if tools are selected
  local added_languages=()
  
  # Helper function to check if language is already added
  language_already_added() {
    local lang="$1"
    local element
    for element in "${added_languages[@]}"; do
      [[ "$element" == "$lang" ]] && return 0
    done
    return 1
  }
  
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      case "$tool" in
        "go"|"golang")
          if ! language_already_added "go"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "go",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "// "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("go")
          fi
          ;;
        "dotnet")
          if ! language_already_added "csharp"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "csharp",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "// "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("csharp")
          fi
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          if ! language_already_added "javascript"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "javascript",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "// "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("javascript")
          fi
          if ! language_already_added "typescript"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "typescript",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "// "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("typescript")
          fi
          ;;
        "python")
          if ! language_already_added "python"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "python",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "# "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("python")
          fi
          ;;
        "powershell")
          if ! language_already_added "powershell"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "powershell",' >> "$temp_file"
            echo '            "begin": "<#",' >> "$temp_file"
            echo '            "end": "#>",' >> "$temp_file"
            echo '            "prefix": ""' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("powershell")
          fi
          ;;
        "opentofu")
          if ! language_already_added "terraform"; then
            echo '          {' >> "$temp_file"
            echo '            "language": "terraform",' >> "$temp_file"
            echo '            "begin": "",' >> "$temp_file"
            echo '            "end": "",' >> "$temp_file"
            echo '            "prefix": "# "' >> "$temp_file"
            echo '          },' >> "$temp_file"
            added_languages+=("terraform")
          fi
          ;;
      esac
    fi
  done
  
  # Always include common languages
  if ! language_already_added "dockerfile"; then
    echo '          {' >> "$temp_file"
    echo '            "language": "dockerfile",' >> "$temp_file"
    echo '            "begin": "",' >> "$temp_file"
    echo '            "end": "",' >> "$temp_file"
    echo '            "prefix": "# "' >> "$temp_file"
    echo '          },' >> "$temp_file"
    added_languages+=("dockerfile")
  fi
  
  # Always include shellscript since shell scripts are common in dev environments
  if ! language_already_added "shellscript"; then
    echo '          {' >> "$temp_file"
    echo '            "language": "shellscript",' >> "$temp_file"
    echo '            "begin": "",' >> "$temp_file"
    echo '            "end": "",' >> "$temp_file"
    echo '            "prefix": "# "' >> "$temp_file"
    echo '          },' >> "$temp_file"
    added_languages+=("shellscript")
  fi
  
  if [[ "$INCLUDE_MARKDOWN_EXTENSIONS" == "true" ]] && ! language_already_added "markdown"; then
    echo '          {' >> "$temp_file"
    echo '            "language": "markdown",' >> "$temp_file"
    echo '            "begin": "",' >> "$temp_file"
    echo '            "end": "",' >> "$temp_file"
    echo '            "prefix": "> "' >> "$temp_file"
    echo '          },' >> "$temp_file"
    added_languages+=("markdown")
  fi
  
  # Always include YAML and env files
  if ! language_already_added "yaml"; then
    echo '          {' >> "$temp_file"
    echo '            "language": "yaml",' >> "$temp_file"
    echo '            "begin": "",' >> "$temp_file"
    echo '            "end": "",' >> "$temp_file"
    echo '            "prefix": "# "' >> "$temp_file"
    echo '          },' >> "$temp_file"
    added_languages+=("yaml")
  fi
  
  if ! language_already_added "env"; then
    echo '          {' >> "$temp_file"
    echo '            "language": "env",' >> "$temp_file"
    echo '            "begin": "",' >> "$temp_file"
    echo '            "end": "",' >> "$temp_file"
    echo '            "prefix": "# "' >> "$temp_file"
    echo '          }' >> "$temp_file"
    added_languages+=("env")
  fi
  
  echo '        ],' >> "$temp_file"
  
  # Generate templates section
  echo "DEBUG: Starting templates section" >&2
  echo '        "psi-header.templates": [' >> "$temp_file"
  
  local template_count=0
  echo "DEBUG: Initialized template_count to: $template_count" >&2
  
  # Only iterate if array has elements
  if [[ ${#PSI_HEADER_TEMPLATES[@]} -gt 0 ]]; then
    echo "DEBUG: Processing ${#PSI_HEADER_TEMPLATES[@]} custom templates" >&2
    for template_entry in "${PSI_HEADER_TEMPLATES[@]}"; do
      echo "DEBUG: Processing template entry: $template_entry" >&2
      local language="${template_entry%%|||*}"
      local template_text="${template_entry#*|||}"
      echo "DEBUG: Extracted language: $language" >&2
      echo "DEBUG: Extracted template_text: $template_text" >&2
      
      # Escape quotes and newlines in template text for JSON
      echo "DEBUG: Starting template text escaping" >&2
      local escaped_template
      # First escape backslashes, then quotes, then handle newlines, then copyright symbol
      escaped_template=$(echo "$template_text" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/©/\\u00A9/g')
      echo "DEBUG: Escaped template: $escaped_template" >&2
      
      if [[ $template_count -gt 0 ]]; then
        echo "DEBUG: Adding comma separator" >&2
        echo ',' >> "$temp_file"
      fi
      
      echo "DEBUG: Adding template JSON structure" >&2
      echo '          {' >> "$temp_file"
      echo "            \"language\": \"$language\"," >> "$temp_file"
      
      # Handle PowerShell special case with .DESCRIPTION
      if [[ "$language" == "powershell" && "$template_text" == *".DESCRIPTION"* ]]; then
        echo "DEBUG: Processing PowerShell special case" >&2
        # Split .DESCRIPTION and content for PowerShell
        local description_part
        local content_part
        description_part=$(echo "$template_text" | head -n1)
        content_part=$(echo "$template_text" | tail -n+2)
        
        # Escape each part separately
        local escaped_description
        local escaped_content
        escaped_description=$(echo "$description_part" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/©/\\u00A9/g')
        escaped_content=$(echo "$content_part" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/©/\\u00A9/g')
        
        echo "            \"template\": [\"$escaped_description\", \"$escaped_content\"]" >> "$temp_file"
      else
        echo "DEBUG: Processing regular template" >&2
        echo "            \"template\": [\"$escaped_template\"]" >> "$temp_file"
      fi
      
      echo "DEBUG: Closing template JSON structure" >&2
      echo -n '          }' >> "$temp_file"
      
      echo "DEBUG: Incrementing template count" >&2
      template_count=$((template_count + 1))
      echo "DEBUG: Template count is now: $template_count" >&2
      echo "DEBUG: Completed processing template for language: $language" >&2
    done
    echo "DEBUG: Finished processing all templates" >&2
  else
    echo "DEBUG: No custom templates found, PSI_HEADER_TEMPLATES array is empty" >&2
  fi
  echo "DEBUG: Template processing section completed" >&2
  
  # Add default template if no custom templates were configured
  if [[ $template_count -eq 0 ]]; then
    echo "DEBUG: Adding default template since no custom templates were configured" >&2
    local default_template_text
    local escaped_default
    default_template_text="Copyright © $(date +%Y) $PSI_HEADER_COMPANY. All rights reserved."
    escaped_default=$(echo "$default_template_text" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/©/\\u00A9/g')
    
    echo '          {' >> "$temp_file"
    echo '            "language": "*",' >> "$temp_file"
    echo "            \"template\": [\"$escaped_default\"]" >> "$temp_file"
    echo '          }' >> "$temp_file"
  else
    echo "DEBUG: Using custom templates, adding newline" >&2
    echo '' >> "$temp_file"
  fi
  
  echo "DEBUG: Closing templates section" >&2
  echo '        ]' >> "$temp_file"
  echo '        // #### End PSI Header Settings ####' >> "$temp_file"
  echo "DEBUG: generate_psi_header_settings function completed successfully" >&2
}

# Update pyproject.toml with Python project configuration
update_pyproject_toml() {
  local project_path="$1"
  local pyproject_file="${project_path}/pyproject.toml"
  
  # Only proceed if Python extensions are enabled
  if [[ "$INCLUDE_PYTHON_EXTENSIONS" != "true" ]]; then
    return
  fi

  # Replace the entire [tool.pybuild] section with the selected repository configuration
  if [[ -n "$PYTHON_REPOSITORY_TYPE" ]]; then
    generate_pybuild_section "$pyproject_file"
  fi

  # Update project metadata if provided
  if [[ -n "$PYTHON_PROJECT_NAME" ]]; then
    # Convert project name to package name (lowercase, underscores, alphanumeric only)
    local package_name
    package_name=$(echo "$PYTHON_PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/_\+/_/g' | sed 's/^_\|_$//g')
    
    # Ensure package name is valid (starts with letter, no consecutive underscores)
    if [[ ! "$package_name" =~ ^[a-z][a-z0-9_]*$ ]]; then
      package_name="my_${package_name}"
    fi
    
    # Update project name and package references
    sed -i "s|name = \"my-awesome-project\"|name = \"$PYTHON_PROJECT_NAME\"|" "$pyproject_file"
    sed -i "s|my_awesome_project|$package_name|g" "$pyproject_file"
    
    # Create the package directory structure
    mkdir -p "${project_path}/src/${package_name}"
    echo "__version__ = \"0.1.0\"" > "${project_path}/src/${package_name}/__about__.py"
    echo "# ${PYTHON_PROJECT_DESCRIPTION:-$PYTHON_PROJECT_NAME}" > "${project_path}/src/${package_name}/__init__.py"
  fi

  # Update project description
  if [[ -n "$PYTHON_PROJECT_DESCRIPTION" ]]; then
    sed -i "s|description = \"A brief description of your project\"|description = \"$PYTHON_PROJECT_DESCRIPTION\"|" "$pyproject_file"
  fi

  # Update license
  if [[ -n "$PYTHON_LICENSE" ]]; then
    sed -i "s|license = \"MIT\"|license = \"$PYTHON_LICENSE\"|" "$pyproject_file"
  fi

  # Update keywords
  if [[ -n "$PYTHON_KEYWORDS" ]]; then
    # Convert comma-separated keywords to proper TOML array format
    # Remove spaces, split by comma, and format as TOML array
    local keywords_array
    keywords_array=$(echo "$PYTHON_KEYWORDS" | sed 's/ //g' | sed 's/,/", "/g' | sed 's/^/["/' | sed 's/$/"]/')
    sed -i "s|keywords = \[\"python\", \"cli\", \"automation\"\]|keywords = $keywords_array|" "$pyproject_file"
  fi

  # Update author information
  if [[ -n "$PYTHON_AUTHOR_NAME" && -n "$PYTHON_AUTHOR_EMAIL" ]]; then
    sed -i "s|{ name = \"Your Name\", email = \"your.email@example.com\" }|{ name = \"$PYTHON_AUTHOR_NAME\", email = \"$PYTHON_AUTHOR_EMAIL\" }|" "$pyproject_file"
  fi

  # Update GitHub URLs
  if [[ -n "$PYTHON_GITHUB_USERNAME" && -n "$PYTHON_GITHUB_PROJECT" ]]; then
    local base_url="https://github.com/${PYTHON_GITHUB_USERNAME}/${PYTHON_GITHUB_PROJECT}"
    sed -i "s|https://github.com/yourusername/my-awesome-project/blob/main/README.md|${base_url}/blob/main/README.md|" "$pyproject_file"
    sed -i "s|https://github.com/yourusername/my-awesome-project/issues|${base_url}/issues|" "$pyproject_file"
    sed -i "s|https://github.com/yourusername/my-awesome-project|${base_url}|g" "$pyproject_file"
  fi
}

# Generate custom devcontainer.json
generate_devcontainer_json() {
  echo "DEBUG: generate_devcontainer_json function started" >&2
  echo "DEBUG: Parameters: project_path='$1', project_name='$2', container_name='$3', display_name='$4'" >&2
  
  local project_path="$1"
  local project_name="$2"
  local container_name="$3"
  local display_name="$4"
  local temp_file="${project_path}/.devcontainer/devcontainer.json.tmp"
  
  echo "DEBUG: temp_file will be: $temp_file" >&2
  
  # Ensure .devcontainer directory exists
  echo "DEBUG: Creating .devcontainer directory..." >&2
  mkdir -p "${project_path}/.devcontainer"
  echo "DEBUG: Directory created successfully" >&2
  
  # Read the base devcontainer.json up to extensions
  echo "DEBUG: About to process base devcontainer.json with awk..." >&2
  awk '/^      "extensions": \[/,/^      \],$/{if(/^      "extensions": \[/) print; else if(/^      \],$/) exit; else next} !/^      "extensions": \[/' .devcontainer/devcontainer.json | head -n -1 > "$temp_file"
  local awk_exit=$?
  echo "DEBUG: Base awk processing completed with exit code: $awk_exit" >&2
  
  if [[ $awk_exit -ne 0 ]]; then
    echo "DEBUG: ERROR - Initial awk processing failed!" >&2
    return 1
  fi
  
  echo "DEBUG: Base file written to temp_file, checking size..." >&2
  if [[ -f "$temp_file" ]]; then
    echo "DEBUG: temp_file exists, size: $(wc -l < "$temp_file") lines" >&2
  else
    echo "DEBUG: ERROR - temp_file was not created!" >&2
    return 1
  fi
  
  # Update the name and runArgs in the temp file
  sed -i "s/\"name\": \"[^\"]*\"/\"name\": \"${display_name}\"/" "$temp_file"
  sed -i "s/--name=dynamic-dev-container/--name=${container_name}/g" "$temp_file"
  sed -i "s/dynamic-dev-container-shellhistory/${container_name}-shellhistory/g" "$temp_file"
  sed -i "s/dynamic-dev-container-plugins/${container_name}-plugins/g" "$temp_file"
  
  # Start extensions array
  echo '      "extensions": [' >> "$temp_file"
  
  # Always include GitHub extensions
  echo "DEBUG: About to extract GitHub extensions..." >&2
  extract_devcontainer_section "// #### Begin Github ####" "// #### End Github ####" | grep -E '^\s*".*",' >> "$temp_file"
  local github_exit=$?
  echo "DEBUG: GitHub extensions extraction completed with exit code: $github_exit" >&2
  
  if [[ $github_exit -ne 0 ]]; then
    echo "DEBUG: ERROR - GitHub extensions extraction failed!" >&2
    return 1
  fi

  # Include extensions based on selected tools
  echo "DEBUG: Starting tools loop - TOOL_SELECTED array processing..." >&2
  if [[ ${#TOOL_SELECTED[@]} -gt 0 ]]; then
    for tool in "${!TOOL_SELECTED[@]}"; do
      echo "DEBUG: Processing tool: $tool, selected: ${TOOL_SELECTED[$tool]}" >&2
      if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
        echo "DEBUG: Tool $tool is selected, processing case statement..." >&2
      case "$tool" in
        "go"|"goreleaser")
          echo "DEBUG: Extracting Go extensions for tool: $tool" >&2
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Go ####" "// #### End Go ####" >> "$temp_file"
          echo "DEBUG: Go extensions extracted successfully for tool: $tool" >&2
          ;;
        "dotnet")
          echo "DEBUG: Extracting .NET extensions for tool: $tool" >&2
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin .NET ####" "// #### End .NET ####" >> "$temp_file"
          echo "DEBUG: .NET extensions extracted successfully for tool: $tool" >&2
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          # JavaScript/Node.js extensions (avoid duplicates)
          echo "DEBUG: Checking JavaScript/Node.js extensions for tool: $tool" >&2
          if ! grep -q "// #### Begin JavaScript/Node.js ####" "$temp_file"; then
            echo "DEBUG: Extracting JavaScript/Node.js extensions for tool: $tool" >&2
            echo "" >> "$temp_file"
            extract_devcontainer_section "// #### Begin JavaScript/Node.js ####" "// #### End JavaScript/Node.js ####" >> "$temp_file"
            echo "DEBUG: JavaScript/Node.js extensions extracted successfully for tool: $tool" >&2
          else
            echo "DEBUG: JavaScript/Node.js extensions already present, skipping for tool: $tool" >&2
          fi
          ;;
        "kubectl"|"helm"|"k9s"|"kubectx"|"kubens"|"krew"|"dive"|"kubebench"|"popeye"|"trivy"|"cmctl"|"k3d")
          # Kubernetes extensions (avoid duplicates)
          echo "DEBUG: Checking Kubernetes extensions for tool: $tool" >&2
          if ! grep -q "// #### Begin Kubernetes/Helm ####" "$temp_file"; then
            echo "DEBUG: Extracting Kubernetes/Helm extensions for tool: $tool" >&2
            echo "" >> "$temp_file"
            extract_devcontainer_section "// #### Begin Kubernetes/Helm ####" "// #### End Kubernetes/Helm ####" >> "$temp_file"
            echo "DEBUG: Kubernetes/Helm extensions extracted successfully for tool: $tool" >&2
          else
            echo "DEBUG: Kubernetes/Helm extensions already present, skipping for tool: $tool" >&2
          fi
          ;;
        "opentofu")
          echo "DEBUG: Extracting Terraform/OpenTofu extensions for tool: $tool" >&2
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Terraform/OpenTofu ####" "// #### End Terraform/OpenTofu ####" >> "$temp_file"
          echo "DEBUG: Terraform/OpenTofu extensions extracted successfully for tool: $tool" >&2
          ;;
        "packer")
          echo "DEBUG: Extracting Packer extensions for tool: $tool" >&2
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Packer ####" "// #### End Packer ####" >> "$temp_file"
          echo "DEBUG: Packer extensions extracted successfully for tool: $tool" >&2
          ;;
        "powershell")
          echo "DEBUG: Extracting PowerShell extensions for tool: $tool" >&2
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin PowerShell ####" "// #### End PowerShell ####" >> "$temp_file"
          echo "DEBUG: PowerShell extensions extracted successfully for tool: $tool" >&2
          ;;
        "python")
          # Python extensions (avoid duplicates)
          echo "DEBUG: Checking Python extensions for tool: $tool" >&2
          if ! grep -q "// #### Begin Python ####" "$temp_file"; then
            echo "DEBUG: Extracting Python extensions for tool: $tool" >&2
            echo "" >> "$temp_file"
            extract_devcontainer_section "// #### Begin Python ####" "// #### End Python ####" >> "$temp_file"
            echo "DEBUG: Python extensions extracted successfully for tool: $tool" >&2
          else
            echo "DEBUG: Python extensions already present, skipping for tool: $tool" >&2
          fi
          ;;
        *)
          echo "DEBUG: No specific extension handling for tool: $tool" >&2
          ;;
      esac
    else
      echo "DEBUG: Tool $tool is not selected" >&2
    fi
  done
  fi
  echo "DEBUG: Completed tools loop" >&2
  
  # Include Python extensions if selected
  echo "DEBUG: Checking INCLUDE_PYTHON_EXTENSIONS: $INCLUDE_PYTHON_EXTENSIONS" >&2
  if [[ "$INCLUDE_PYTHON_EXTENSIONS" == "true" ]]; then
    if ! grep -q "// #### Begin Python ####" "$temp_file"; then
      echo "DEBUG: Including Python extensions" >&2
      echo "" >> "$temp_file"
      extract_devcontainer_section "// #### Begin Python ####" "// #### End Python ####" >> "$temp_file"
      echo "DEBUG: Python extensions included successfully" >&2
    else
      echo "DEBUG: Python extensions already present, skipping INCLUDE_PYTHON_EXTENSIONS" >&2
    fi
  fi
  
  # Include Markdown extensions if selected
  echo "DEBUG: Checking INCLUDE_MARKDOWN_EXTENSIONS: $INCLUDE_MARKDOWN_EXTENSIONS" >&2
  if [[ "$INCLUDE_MARKDOWN_EXTENSIONS" == "true" ]]; then
    if ! grep -q "// #### Begin Markdown ####" "$temp_file"; then
      echo "DEBUG: Including Markdown extensions" >&2
      echo "" >> "$temp_file"
      extract_devcontainer_section "// #### Begin Markdown ####" "// #### End Markdown ####" >> "$temp_file"
      echo "DEBUG: Markdown extensions included successfully" >&2
    else
      echo "DEBUG: Markdown extensions already present, skipping INCLUDE_MARKDOWN_EXTENSIONS" >&2
    fi
  fi
  
  # Include Shell/Bash extensions if selected
  echo "DEBUG: Checking INCLUDE_SHELL_EXTENSIONS: $INCLUDE_SHELL_EXTENSIONS" >&2
  if [[ "$INCLUDE_SHELL_EXTENSIONS" == "true" ]]; then
    if ! grep -q "// #### Begin Shell/Bash ####" "$temp_file"; then
      echo "DEBUG: Including Shell/Bash extensions" >&2
      echo "" >> "$temp_file"
      extract_devcontainer_section "// #### Begin Shell/Bash ####" "// #### End Shell/Bash ####" >> "$temp_file"
      echo "DEBUG: Shell/Bash extensions included successfully" >&2
    else
      echo "DEBUG: Shell/Bash extensions already present, skipping INCLUDE_SHELL_EXTENSIONS" >&2
    fi
  fi
  
  # Include PSI Header extension if selected
  echo "DEBUG: Checking INSTALL_PSI_HEADER: $INSTALL_PSI_HEADER" >&2
  if [[ "$INSTALL_PSI_HEADER" == "true" ]]; then
    if ! grep -q "// #### Begin PSI Header ####" "$temp_file"; then
      echo "DEBUG: Including PSI Header extensions" >&2
      echo "" >> "$temp_file"
      extract_devcontainer_section "// #### Begin PSI Header ####" "// #### End PSI Header ####" >> "$temp_file"
      echo "DEBUG: PSI Header extensions included successfully" >&2
    else
      echo "DEBUG: PSI Header extensions already present, skipping INSTALL_PSI_HEADER" >&2
    fi
  fi
  
  # Include JavaScript/TypeScript extensions if Node.js was installed
  echo "DEBUG: Checking TOOL_SELECTED[node]: ${TOOL_SELECTED[node]:-false}" >&2
  if [[ "${TOOL_SELECTED[node]:-false}" == "true" ]]; then
    if ! grep -q "// #### Begin JavaScript/TypeScript ####" "$temp_file"; then
      echo "DEBUG: Including JavaScript/TypeScript extensions" >&2
      INCLUDE_JS_EXTENSIONS=true
      echo "" >> "$temp_file"
      extract_devcontainer_section "// #### Begin JavaScript/TypeScript ####" "// #### End JavaScript/TypeScript ####" >> "$temp_file"
      echo "DEBUG: JavaScript/TypeScript extensions included successfully" >&2
    else
      echo "DEBUG: JavaScript/TypeScript extensions already present, skipping Node.js check" >&2
    fi
  fi
  
  # Always include Core Extensions
  echo "DEBUG: Including Core extensions" >&2
  # shellcheck disable=SC2129
  echo "" >> "$temp_file"
  extract_devcontainer_section "// #### Begin Core Extensions ####" "// #### End Core Extensions ####" >> "$temp_file"
  echo "DEBUG: Core extensions included successfully" >&2

  # Remove trailing comma from the last extension entry
  echo "DEBUG: Removing trailing comma from last extension entry" >&2
  last_ext_line=$(grep -n '^\s*".*",' "$temp_file" | tail -n 1 | cut -d: -f1)
  if [[ -n "$last_ext_line" ]]; then
    echo "DEBUG: Found trailing comma at line $last_ext_line, removing it" >&2
    sed -i "${last_ext_line}s/,$//" "$temp_file"
    echo "DEBUG: Trailing comma removed successfully" >&2
  else
    echo "DEBUG: No trailing comma found" >&2
  fi

  # Close extensions array and add settings
  echo "DEBUG: Closing extensions array and adding settings" >&2
  echo "      ]," >> "$temp_file"
  echo "DEBUG: Extensions array closed successfully" >&2

  # Add settings section
  echo "DEBUG: Adding settings section" >&2
  echo '      "settings": {' >> "$temp_file"
  echo "DEBUG: Settings section opened" >&2

  # Always include Core VS Code Settings
  echo "DEBUG: Including Core VS Code Settings" >&2
  extract_devcontainer_section "// #### Begin Core VS Code Settings ####" "// #### End Core VS Code Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  echo "DEBUG: Core VS Code Settings included successfully" >&2
  
  # Include settings based on selected tools
  echo "DEBUG: Starting settings processing loop" >&2
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      echo "DEBUG: Processing settings for tool: $tool" >&2
      case "$tool" in
        "go"|"goreleaser")
          # Go settings (avoid duplicates)
          echo "DEBUG: Checking Go settings for tool: $tool" >&2
          if ! grep -q "go.toolsManagement.autoUpdate" "$temp_file"; then
            echo "DEBUG: Adding Go settings for tool: $tool" >&2
            # shellcheck disable=SC2129
            extract_devcontainer_section "// #### Begin Go Settings ####" "// #### End Go Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
            echo "DEBUG: Go settings added successfully for tool: $tool" >&2
          else
            echo "DEBUG: Go settings already present, skipping for tool: $tool" >&2
          fi
          ;;
        "dotnet")
          echo "DEBUG: Adding .NET settings for tool: $tool" >&2
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin .NET Settings ####" "// #### End .NET Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          echo "DEBUG: .NET settings added successfully for tool: $tool" >&2
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          # JavaScript/Node.js settings (avoid duplicates)
          echo "DEBUG: Checking JavaScript/Node.js settings for tool: $tool" >&2
          if ! grep -q "typescript.preferences.includePackageJsonAutoImports" "$temp_file"; then
            echo "DEBUG: Adding JavaScript/Node.js settings for tool: $tool" >&2
            # shellcheck disable=SC2129
            extract_devcontainer_section "// #### Begin JavaScript/Node.js Settings ####" "// #### End JavaScript/Node.js Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
            echo "DEBUG: JavaScript/Node.js settings added successfully for tool: $tool" >&2
          else
            echo "DEBUG: JavaScript/Node.js settings already present, skipping for tool: $tool" >&2
          fi
          ;;
        "kubectl"|"helm"|"k9s"|"kubectx"|"kubens"|"krew"|"dive"|"kubebench"|"popeye"|"trivy"|"cmctl"|"k3d")
          echo "DEBUG: Checking Kubernetes settings for tool: $tool" >&2
          # Kubernetes settings (avoid duplicates)
          if ! grep -q "helm-intellisense.lintFileOnSave" "$temp_file"; then
            echo "DEBUG: Adding Kubernetes/Helm settings for tool: $tool" >&2
            # shellcheck disable=SC2129
            extract_devcontainer_section "// #### Begin Kubernetes/Helm Settings ####" "// #### End Kubernetes/Helm Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
            echo "DEBUG: Kubernetes/Helm settings added successfully for tool: $tool" >&2
          else
            echo "DEBUG: Kubernetes/Helm settings already present, skipping for tool: $tool" >&2
          fi
          ;;
        "powershell")
          echo "DEBUG: Adding PowerShell settings for tool: $tool" >&2
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin PowerShell Settings ####" "// #### End PowerShell Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          echo "DEBUG: PowerShell settings added successfully for tool: $tool" >&2
          ;;
        *)
          echo "DEBUG: No specific settings handling for tool: $tool" >&2
          ;;
      esac
    else
      echo "DEBUG: Tool $tool is not selected for settings" >&2
    fi
  done
  echo "DEBUG: Completed settings processing loop" >&2
  
  # Include Python settings if Python extensions were selected
  echo "DEBUG: Checking INCLUDE_PYTHON_EXTENSIONS for settings: $INCLUDE_PYTHON_EXTENSIONS" >&2
  if [[ "$INCLUDE_PYTHON_EXTENSIONS" == "true" ]]; then
    if ! grep -q "python.defaultInterpreterPath" "$temp_file"; then
      echo "DEBUG: Including Python settings" >&2
      # shellcheck disable=SC2129
      extract_devcontainer_section "// #### Begin Python Settings ####" "// #### End Python Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
      echo "DEBUG: Python settings included successfully" >&2
    else
      echo "DEBUG: Python settings already present, skipping INCLUDE_PYTHON_EXTENSIONS" >&2
    fi
  fi
  
  # Include Markdown settings if Markdown extensions were selected
  echo "DEBUG: Checking INCLUDE_MARKDOWN_EXTENSIONS for settings: $INCLUDE_MARKDOWN_EXTENSIONS" >&2
  if [[ "$INCLUDE_MARKDOWN_EXTENSIONS" == "true" ]]; then
    if ! grep -q "markdown.extension.orderedList.autoRenumber" "$temp_file"; then
      echo "DEBUG: Including Markdown settings" >&2
      # shellcheck disable=SC2129
      extract_devcontainer_section "// #### Begin Markdown Settings ####" "// #### End Markdown Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
      echo "DEBUG: Markdown settings included successfully" >&2
    else
      echo "DEBUG: Markdown settings already present, skipping INCLUDE_MARKDOWN_EXTENSIONS" >&2
    fi
  fi
  
  # Include Shell/Bash settings if Shell extensions were selected
  echo "DEBUG: Checking INCLUDE_SHELL_EXTENSIONS for settings: $INCLUDE_SHELL_EXTENSIONS" >&2
  if [[ "$INCLUDE_SHELL_EXTENSIONS" == "true" ]]; then
    if ! grep -q "shellcheck.customArgs" "$temp_file"; then
      echo "DEBUG: Including Shell/Bash settings" >&2
      # shellcheck disable=SC2129
      extract_devcontainer_section "// #### Begin Shell/Bash Settings ####" "// #### End Shell/Bash Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
      echo "DEBUG: Shell/Bash settings included successfully" >&2
    else
      echo "DEBUG: Shell/Bash settings already present, skipping INCLUDE_SHELL_EXTENSIONS" >&2
    fi
  fi
  
  # Include JavaScript/TypeScript settings if JS extensions were selected
  echo "DEBUG: Checking INCLUDE_JS_EXTENSIONS for settings: $INCLUDE_JS_EXTENSIONS" >&2
  if [[ "$INCLUDE_JS_EXTENSIONS" == "true" ]]; then
    if ! grep -q "typescript.preferences.includePackageJsonAutoImports" "$temp_file"; then
      echo "DEBUG: Including JavaScript/TypeScript settings" >&2
      # shellcheck disable=SC2129
      extract_devcontainer_section "// #### Begin JavaScript/TypeScript Settings ####" "// #### End JavaScript/TypeScript Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
      echo "DEBUG: JavaScript/TypeScript settings included successfully" >&2
    else
      echo "DEBUG: JavaScript/TypeScript settings already present, skipping INCLUDE_JS_EXTENSIONS" >&2
    fi
  fi
  
  # Always include spell checker settings
  echo "DEBUG: Including Spell Checker settings" >&2
  extract_devcontainer_section "// #### Begin Spell Checker Settings ####" "// #### End Spell Checker Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  echo "DEBUG: Spell Checker settings included successfully" >&2
  
  # Always include Mise settings (since Mise extension is in Core Extensions)
  echo "DEBUG: Including Mise settings" >&2
  extract_devcontainer_section "// #### Begin Mise Settings ####" "// #### End Mise Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  echo "DEBUG: Mise settings included successfully" >&2
  
  # Include TODO Tree settings
  echo "DEBUG: Including TODO Tree settings" >&2
  extract_devcontainer_section "// #### Begin TODO Tree Settings ####" "// #### End TODO Tree Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
  echo "DEBUG: TODO Tree settings included successfully" >&2
  
  # Include PSI Header settings if configured, otherwise include default ones
  echo "DEBUG: Checking INSTALL_PSI_HEADER for settings: $INSTALL_PSI_HEADER" >&2
  if [[ "$INSTALL_PSI_HEADER" == "true" ]]; then
    echo "DEBUG: Generating PSI Header settings" >&2
    generate_psi_header_settings "$temp_file"
    echo "DEBUG: PSI Header settings generated successfully" >&2
  else
    echo "DEBUG: Including default PSI Header settings" >&2
    extract_devcontainer_section "// #### Begin PSI Header Settings ####" "// #### End PSI Header Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
    echo "DEBUG: Default PSI Header settings included successfully" >&2
  fi
  
  # Fix settings entries to ensure proper JSON formatting
  echo "DEBUG: Starting JSON formatting fixes..." >&2
  
  # Simple approach: just ensure all setting lines have commas except the very last one
  # Get all setting property lines (8 spaces + quoted property)
  setting_line_numbers=$(grep -n '^        "[^"]*":' "$temp_file" | grep -v '[\{\[][\s]*$' | cut -d: -f1)
  
  if [[ -n "$setting_line_numbers" ]]; then
    echo "DEBUG: Found setting lines to process" >&2
    
    # Add commas to all setting lines first
    while read -r line_num; do
      [[ -n "$line_num" ]] || continue
      # Only add comma if line doesn't already have one
      if ! sed -n "${line_num}p" "$temp_file" | grep -q ',$'; then
        sed -i "${line_num}s/$/,/" "$temp_file"
      fi
    done <<< "$setting_line_numbers"
    
    # Find the very last setting line and remove its comma
    last_setting_line=$(grep -n '^        "[^"]*":' "$temp_file" | tail -n 1 | cut -d: -f1)
    if [[ -n "$last_setting_line" ]]; then
      echo "DEBUG: Removing comma from last setting line: $last_setting_line" >&2
      sed -i "${last_setting_line}s/,$//" "$temp_file"
    fi
  fi
  
  echo "DEBUG: JSON formatting completed" >&2

  # Close settings and customizations
  echo "DEBUG: Closing JSON structure..." >&2
  echo '      }' >> "$temp_file"
  echo '    }' >> "$temp_file"
  echo '  }' >> "$temp_file"
  echo '}' >> "$temp_file"
  echo "DEBUG: JSON structure closed" >&2
  
  echo "DEBUG: Moving temp file to final location..." >&2
  echo "DEBUG: Source: $temp_file" >&2
  echo "DEBUG: Destination: ${project_path}/.devcontainer/devcontainer.json" >&2
  
  if [[ -f "$temp_file" ]]; then
    echo "DEBUG: temp_file exists, moving..." >&2
    mv "$temp_file" "${project_path}/.devcontainer/devcontainer.json"
    local mv_exit=$?
    echo "DEBUG: mv exit code: $mv_exit" >&2
    if [[ $mv_exit -ne 0 ]]; then
      echo "DEBUG: ERROR - mv command failed!" >&2
      return 1
    fi
  else
    echo "DEBUG: ERROR - temp_file does not exist!" >&2
    return 1
  fi
  
  echo "DEBUG: generate_devcontainer_json function completed successfully" >&2
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
  echo "DEBUG: Starting post-TUI installation phase"

  # Create .devcontainer directory
  echo "DEBUG: Creating .devcontainer directory"
  mkdir -p "${project_path}/.devcontainer"
  echo "DEBUG: .devcontainer directory created successfully"

  # Copy directories to the destination
  echo "DEBUG: Starting directory copy phase"
  for dir in "${DIRECTORIES_TO_COPY[@]}"; do
    echo "DEBUG: Processing directory: $dir"
    if [[ -d "$dir" ]]; then
      echo "DEBUG: Copying directory $dir to ${project_path}/$dir/"
      cp -r "$dir"/* "${project_path}/$dir/" 2>/dev/null || true
      echo "DEBUG: Directory $dir copied successfully"
    else
      echo "DEBUG: Directory $dir not found"
    fi
  done
  echo "DEBUG: Directory copy phase completed"
  
  # Copy files to the destination
  echo "DEBUG: Starting file copy phase"
  for file in "${FILES_TO_COPY[@]}"; do
    echo "DEBUG: Processing file: $file"
    # Skip if file already exists in the target directory
    if [[ -f "${project_path}/$file" ]]; then
      echo "Skipping $file - already exists in target directory"
      continue
    fi
    
    if [[ -f "$file" ]]; then
      echo "DEBUG: Copying file $file to ${project_path}/$file"
      cp "$file" "${project_path}/$file" 2>/dev/null || true
      echo "Copied $file"
      echo "DEBUG: File $file copied successfully"
    else
      echo "DEBUG: File $file not found"
    fi
  done
  echo "DEBUG: File copy phase completed"

  # Copy Python-specific files if Python tools are being installed
  echo "DEBUG: Checking if Python tools should be copied: INSTALL_PYTHON_TOOLS=$INSTALL_PYTHON_TOOLS"
  if [[ "$INSTALL_PYTHON_TOOLS" == "true" ]]; then
    echo "DEBUG: Starting Python files copy phase"
    for file in "${PYTHON_FILES_TO_COPY[@]}"; do
      echo "DEBUG: Processing Python file: $file"
      # Skip if file already exists in the target directory
      if [[ -f "${project_path}/$file" ]]; then
        echo "Skipping $file - already exists in target directory"
        continue
      fi
      
      if [[ -f "$file" ]]; then
        echo "DEBUG: Copying Python file $file to ${project_path}/$file"
        cp "$file" "${project_path}/$file" 2>/dev/null || true
        echo "Copied Python tool: $file"
        echo "DEBUG: Python file $file copied successfully"
      else
        echo "DEBUG: Python file $file not found"
      fi
    done
    echo "DEBUG: Python files copy phase completed"
  else
    echo "DEBUG: Skipping Python files copy (INSTALL_PYTHON_TOOLS=false)"
  fi

  # Generate the customized configuration files
  echo "DEBUG: === Starting configuration generation phase ==="
  echo "DEBUG: Calling generate_mise_toml with project_path=$project_path"
  generate_mise_toml "$project_path"
  echo "DEBUG: generate_mise_toml completed successfully"
  
  echo "DEBUG: Calling generate_devcontainer_json with PROJECT_NAME=$PROJECT_NAME, CONTAINER_NAME=$CONTAINER_NAME, DISPLAY_NAME=$DISPLAY_NAME"
  generate_devcontainer_json "$project_path" "$PROJECT_NAME" "$CONTAINER_NAME" "$DISPLAY_NAME"
  echo "DEBUG: generate_devcontainer_json completed successfully"

  # Update dev.sh with project settings
  echo "DEBUG: Calling update_dev_sh with DOCKER_EXEC_COMMAND=$DOCKER_EXEC_COMMAND, PROJECT_NAME=$PROJECT_NAME, CONTAINER_NAME=$CONTAINER_NAME"
  update_dev_sh "$project_path" "$DOCKER_EXEC_COMMAND" "$PROJECT_NAME" "$CONTAINER_NAME"
  echo "DEBUG: update_dev_sh completed successfully"

  # Update pyproject.toml with Python repository configuration (only if Python tools are installed)
  echo "DEBUG: Checking if Python pyproject.toml should be updated: INSTALL_PYTHON_TOOLS=$INSTALL_PYTHON_TOOLS"
  if [[ "$INSTALL_PYTHON_TOOLS" == "true" ]]; then
    echo "DEBUG: Calling update_pyproject_toml with project_path=$project_path"
    update_pyproject_toml "$project_path"
    echo "DEBUG: update_pyproject_toml completed successfully"
  else
    echo "DEBUG: Skipping pyproject.toml update (INSTALL_PYTHON_TOOLS=false)"
  fi

  # Clean up dialog config
  echo "DEBUG: Cleaning up dialog config file: $DIALOGRC"
  rm -f $DIALOGRC
  echo "DEBUG: Dialog config cleanup completed"

  echo "DEBUG: === Configuration generation phase completed successfully ==="
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
  if [[ "$INSTALL_PYTHON_TOOLS" == "true" ]]; then
    echo -e "4. ${YELLOW}Python Development:${NC} Your Python project has been automatically configured!"
    if [[ -n "$PYTHON_PROJECT_NAME" ]]; then
      echo -e "   - Project structure created in src/$(echo "$PYTHON_PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr '-' '_' | tr ' ' '_')/"
      echo -e "   - Project metadata configured with your provided information"
    fi
    if [[ -n "$PYTHON_PUBLISH_URL" ]]; then
      echo -e "   - Repository URLs configured for your package storage"
      echo -e "   - Set authentication: export HATCH_INDEX_USER=username HATCH_INDEX_AUTH=token"
    else
      echo -e "   - Review [tool.pybuild] repository settings if you plan to publish packages"
    fi
    echo -e "   - Run: cd ${project_path} && python pybuild.py --help"
    echo -e "5. See README.md and PYTHON_REPOSITORY_CONFIG.md for additional configuration"
  else
    echo -e "4. See README.md for detailed configuration instructions"
  fi
  echo ""
  echo -e "${BLUE}You can now run:${NC} cd ${project_path} && ./dev.sh"
}

# Make script executable and run main if not sourced
if ! (return 0 2>/dev/null); then
  (main "$@")
fi
