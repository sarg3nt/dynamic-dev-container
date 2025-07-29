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
INCLUDE_PYTHON_EXTENSIONS=false
INCLUDE_MARKDOWN_EXTENSIONS=false
INCLUDE_SHELL_EXTENSIONS=false
INCLUDE_JS_EXTENSIONS=false

# Files and directories to copy to new projects
FILES_TO_COPY=(
  ".gitignore"
  ".krew_plugins"
  ".packages"
  "cspell.json"
  "dev.sh"
  "package.json"
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
      done
    fi
  done

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
  
  # Include extensions based on selected tools
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      case "$tool" in
        "go"|"goreleaser")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Go ####" "// #### End Go ####" >> "$temp_file"
          ;;
        "dotnet")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin .NET ####" "// #### End .NET ####" >> "$temp_file"
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin JavaScript/Node.js ####" "// #### End JavaScript/Node.js ####" >> "$temp_file"
          ;;
        "kubectl"|"helm"|"k9s"|"kubectx"|"kubens"|"krew"|"dive"|"kubebench"|"popeye"|"trivy"|"cmctl"|"k3d")
          # Kubernetes extensions (avoid duplicates)
          if ! grep -q "// #### Begin Kubernetes/Helm ####" "$temp_file"; then
            echo "" >> "$temp_file"
            extract_devcontainer_section "// #### Begin Kubernetes/Helm ####" "// #### End Kubernetes/Helm ####" >> "$temp_file"
          fi
          ;;
        "opentofu")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Terraform/OpenTofu ####" "// #### End Terraform/OpenTofu ####" >> "$temp_file"
          ;;
        "packer")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin Packer ####" "// #### End Packer ####" >> "$temp_file"
          ;;
        "powershell")
          echo "" >> "$temp_file"
          extract_devcontainer_section "// #### Begin PowerShell ####" "// #### End PowerShell ####" >> "$temp_file"
          ;;
      esac
    fi
  done
  
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
  
  # Include JavaScript/TypeScript extensions if Node.js was installed
  if [[ "${TOOL_SELECTED[node]}" == "true" ]]; then
    INCLUDE_JS_EXTENSIONS=true
    echo "" >> "$temp_file"
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript ####" "// #### End JavaScript/TypeScript ####" >> "$temp_file"
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
  
  # Include settings based on selected tools
  for tool in "${!TOOL_SELECTED[@]}"; do
    if [[ "${TOOL_SELECTED[$tool]}" == "true" ]]; then
      case "$tool" in
        "go"|"goreleaser")
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin Go Settings ####" "// #### End Go Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          ;;
        "dotnet")
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin .NET Settings ####" "// #### End .NET Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          ;;
        "node"|"pnpm"|"yarn"|"deno"|"bun")
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin JavaScript/Node.js Settings ####" "// #### End JavaScript/Node.js Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          ;;
        "kubectl"|"helm"|"k9s"|"kubectx"|"kubens"|"krew"|"dive"|"kubebench"|"popeye"|"trivy"|"cmctl"|"k3d")
          # Kubernetes settings (avoid duplicates)
          if ! grep -q "Begin Kubernetes/Helm Settings" "$temp_file"; then
            # shellcheck disable=SC2129
            extract_devcontainer_section "// #### Begin Kubernetes/Helm Settings ####" "// #### End Kubernetes/Helm Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          fi
          ;;
        "powershell")
          # shellcheck disable=SC2129
          extract_devcontainer_section "// #### Begin PowerShell Settings ####" "// #### End PowerShell Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
          ;;
      esac
    fi
  done
  
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
  
  # Include JavaScript/TypeScript settings if JS extensions were selected
  if [ "$INCLUDE_JS_EXTENSIONS" = true ]; then
    # shellcheck disable=SC2129
    extract_devcontainer_section "// #### Begin JavaScript/TypeScript Settings ####" "// #### End JavaScript/TypeScript Settings ####" | grep -v "^\s*//.*Begin\|^\s*//.*End" >> "$temp_file"
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
