#!/bin/bash
#
# Script to add Mise tools to the dynamic dev container.
#
# This script handles the installation of development tools via Mise (https://mise.jdx.dev/)
# during the container build process. It temporarily removes JavaScript/Node.js tools
# to prevent build failures, then restores them after installation.
#
# cSpell:ignore krew mise mvdan gofumpt gopls

IFS=$'\n\t'

set -euo pipefail

# Source the logging utility
# shellcheck disable=SC1091
source "$(dirname "$0")/log.sh"

# Constants
readonly MISE_CONFIG_FILE=".mise.toml"
readonly BACKUP_FILE="${MISE_CONFIG_FILE}.backup"
readonly TEMP_FILE="${MISE_CONFIG_FILE}.temp"
readonly JS_BEGIN_MARKER="#### Begin Node Development"
readonly JS_END_MARKER="#### End Node Development"
readonly MAX_INSTALL_ATTEMPTS=10
readonly RETRY_DELAY=6
readonly ZSHRC_FILE="/home/vscode/.zshrc"

# Global variables
js_section_removed=false

#######################################
# Check for backup and restore if needed
# Arguments:
#   None
# Returns:
#   0 on success
# Globals:
#   BACKUP_FILE - Path to backup file
#   MISE_CONFIG_FILE - Path to mise configuration file
#######################################
check_and_restore_backup() {
  if [[ -f "$BACKUP_FILE" ]]; then
    log_warning "Found backup .mise.toml file, restoring from previous failed installation"
    if ! sudo mv "$BACKUP_FILE" "$MISE_CONFIG_FILE"; then
      log_error "Failed to restore backup file"
      return 1
    fi
    log_success "Restored .mise.toml from backup"
  fi
  return 0
}

#######################################
# Check for JavaScript/Node.js section and remove it if found
# This has to be done because when node20 or above is installed it breaks the .devcontainer install 
# process and the post_start_command.sh file never runs.
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   js_section_removed - Set to true if section was found and removed
#   BACKUP_FILE, TEMP_FILE, JS_BEGIN_MARKER, JS_END_MARKER, MISE_CONFIG_FILE - File paths and markers
#######################################
check_and_remove_javascript_section() {
  local in_js_section=false
  local js_section_found=false
  
  # Check if JavaScript section exists
  if ! grep -q "$JS_BEGIN_MARKER" "$MISE_CONFIG_FILE"; then
    log_info "No JavaScript/Node.js section found, proceeding with normal mise install"
    js_section_removed=false
    return 0
  fi
  
  log_info "JavaScript/Node.js section detected, creating backup and removing section"
  
  # Create backup with error handling
  if ! sudo cp "$MISE_CONFIG_FILE" "$BACKUP_FILE"; then
    log_error "Failed to create backup of $MISE_CONFIG_FILE"
    return 1
  fi
  log_success "Backup of .mise.toml created at $BACKUP_FILE"
  
  # Create temp file with proper permissions
  if ! sudo touch "$TEMP_FILE"; then
    log_error "Failed to create temporary file $TEMP_FILE"
    return 1
  fi
  
  # Remove JavaScript section with improved error handling
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "$JS_BEGIN_MARKER" ]]; then
      in_js_section=true
      js_section_found=true
      continue
    elif [[ "$line" == "$JS_END_MARKER" ]]; then
      in_js_section=false
      continue
    fi
    
    # Only write lines that are not in the JavaScript section
    if [[ "$in_js_section" == false ]]; then
      if ! printf '%s\n' "$line" | sudo tee -a "$TEMP_FILE" >/dev/null; then
        log_error "Failed to write to temporary file"
        sudo rm -f "$TEMP_FILE" 2>/dev/null || true
        return 1
      fi
    fi
  done < "$MISE_CONFIG_FILE"
  
  # Replace original with modified version
  if ! sudo mv "$TEMP_FILE" "$MISE_CONFIG_FILE"; then
    log_error "Failed to replace original mise configuration"
    sudo rm -f "$TEMP_FILE" 2>/dev/null || true
    return 1
  fi
  
  if [[ "$js_section_found" == true ]]; then
    log_success "Removed JavaScript/Node.js section from .mise.toml"
    js_section_removed=true
  else
    log_warning "JavaScript section markers found but no content removed"
    js_section_removed=false
  fi
  
  return 0
}

#######################################
# Clean up temporary files and restore backups on failure
# Arguments:
#   None
# Globals:
#   TEMP_FILE, BACKUP_FILE, MISE_CONFIG_FILE, js_section_removed
#######################################
cleanup_on_failure() {
  log_info "Cleaning up temporary files and restoring backups..."
  
  # Remove temporary file if it exists
  if [[ -f "$TEMP_FILE" ]]; then
    sudo rm -f "$TEMP_FILE" 2>/dev/null || true
    log_info "Removed temporary file $TEMP_FILE"
  fi
  
  # Restore backup if JavaScript section was removed and backup exists
  if [[ "$js_section_removed" == true && -f "$BACKUP_FILE" ]]; then
    if sudo mv "$BACKUP_FILE" "$MISE_CONFIG_FILE" 2>/dev/null; then
      log_success "Restored original .mise.toml with JavaScript section"
    else
      log_warning "Failed to restore backup, manual restoration may be needed"
    fi
  fi
}

#######################################
# Validate that mise is available and properly configured
# Arguments:
#   None
# Returns:
#   0 if mise is available, 1 otherwise
#######################################
validate_mise_availability() {
  if ! command -v mise >/dev/null 2>&1; then
    log_error "Mise command not found. Please ensure Mise is installed."
    return 1
  fi
  
  log_info "Mise version: $(mise --version 2>/dev/null || echo 'unknown')"
  return 0
}

#######################################
# Install tools with mise using native mise install command
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   js_section_removed, MAX_INSTALL_ATTEMPTS, RETRY_DELAY, BACKUP_FILE, MISE_CONFIG_FILE
#######################################
install_mise_tools() {
  log_info "Starting mise tools installation..."
  
  # Validate mise availability
  if ! validate_mise_availability; then
    return 1
  fi
  
  # Check if .mise.toml exists
  if [[ ! -f "$MISE_CONFIG_FILE" ]]; then
    log_warning "No $MISE_CONFIG_FILE file found, skipping mise tools installation"
    return 0
  fi
  
  # Check for and restore any existing backup
  if ! check_and_restore_backup; then
    return 1
  fi
  
  # Check if JavaScript section exists and handle it
  # This has to be done because when node20 or above is installed it breaks the .devcontainer install 
  # process and the post_start_command.sh file never runs.
  js_section_removed=false
  if ! check_and_remove_javascript_section; then
    cleanup_on_failure
    return 1
  fi
  
  # Trust the mise configuration in the current directory
  log_info "Trusting mise configuration..."
  if ! mise trust "$MISE_CONFIG_FILE"; then
    log_error "Failed to trust mise configuration"
    cleanup_on_failure
    return 1
  fi
  log_success "Mise configuration trusted successfully."

  # Install tools using native mise install with retry logic
  local attempt=1
  local install_success=false
  
  # Make several attempts to install mise tools as temporary network issues could cause it to fail.
  while [[ $attempt -le $MAX_INSTALL_ATTEMPTS && $install_success == false ]]; do
    log_info "Installing mise tools (attempt $attempt/$MAX_INSTALL_ATTEMPTS)..."
    
    if mise install -y 2>&1; then
      log_success "Mise tools installation completed successfully!"
      install_success=true
    else
      if [[ $attempt -lt $MAX_INSTALL_ATTEMPTS ]]; then
        log_warning "Mise install failed on attempt $attempt, retrying in $RETRY_DELAY seconds..."
        sleep "$RETRY_DELAY"
      else
        log_error "Mise install failed after $MAX_INSTALL_ATTEMPTS attempts"
        cleanup_on_failure
        return 1
      fi
    fi
    
    ((attempt++))
  done
  
  # Restore backup if JavaScript section was removed
  if [[ "$js_section_removed" == true && -f "$BACKUP_FILE" ]]; then
    log_info "Restoring original .mise.toml with JavaScript section"
    if ! sudo mv "$BACKUP_FILE" "$MISE_CONFIG_FILE"; then
      log_error "Failed to restore original mise configuration"
      return 1
    fi
    log_success "Restored original .mise.toml with JavaScript section"
  fi
  
  # Activate mise environment with error handling
  log_info "Activating mise environment..."
  if ! eval "$(/usr/local/bin/mise activate bash)" 2>/dev/null; then
    log_warning "Failed to activate mise environment, continuing anyway"
  else
    log_success "Mise environment activated successfully."
  fi
  
  return 0
}

#######################################
# Set up .NET environment variables
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
# Globals:
#   ZSHRC_FILE - Path to zsh configuration file
#######################################
setup_dotnet_environment() {
  # Check if .NET is available
  if [[ -z "${DOTNET_ROOT:-}" ]] || [[ ! -d "${DOTNET_ROOT}" ]]; then
    log_info "DOTNET_ROOT not set or directory doesn't exist, skipping .NET environment setup"
    return 0
  fi
  
  log_info "Setting up .NET environment variables..."
  
  # Find and set MSBuildSDKsPath
  local sdks_path
  sdks_path=$(find "${DOTNET_ROOT}" -name "Sdks" -type d 2>/dev/null | head -1)
  
  if [[ -n "${sdks_path}" && -d "${sdks_path}" ]]; then
    log_info "Setting MSBuildSDKsPath to: ${sdks_path}"
    if ! sudo sh -c "echo \"export MSBuildSDKsPath=\\\"${sdks_path}\\\"\" >> \"$ZSHRC_FILE\""; then
      log_error "Failed to set MSBuildSDKsPath in $ZSHRC_FILE"
      return 1
    fi
  else
    log_warning "Could not find .NET SDK directory, skipping MSBuildSDKsPath setup"
  fi

  # Set telemetry opt-out
  log_info "Disabling .NET telemetry..."
  if ! sudo sh -c "echo \"export DOTNET_CLI_TELEMETRY_OPTOUT=1\" >> \"$ZSHRC_FILE\""; then
    log_error "Failed to set DOTNET_CLI_TELEMETRY_OPTOUT in $ZSHRC_FILE"
    return 1
  fi
  
  log_success ".NET environment variables set successfully."
  return 0
}

#######################################
# Set up Go development tools
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
setup_go_tools() {
  if ! command -v go >/dev/null 2>&1; then
    log_info "Go not found, skipping Go tools installation"
    return 0
  fi
  
  log_info "Go version: $(go version 2>/dev/null || echo 'unknown')"
  log_info "Installing Go development tools..."
  
  # Array of Go tools to install
  local -a go_tools=(
    "github.com/go-delve/delve/cmd/dlv@latest"
    "golang.org/x/tools/gopls@latest"
    "mvdan.cc/gofumpt@latest"
  )
  
  local failed_tools=()
  
  # Install each tool with error handling
  for tool in "${go_tools[@]}"; do
    local tool_name
    tool_name=$(basename "${tool%@*}")
    log_info "Installing Go tool: $tool_name"
    
    if ! go install "$tool" 2>/dev/null; then
      log_warning "Failed to install Go tool: $tool_name"
      failed_tools+=("$tool_name")
    else
      log_info "Successfully installed: $tool_name"
    fi
  done
  
  # Report results
  if [[ ${#failed_tools[@]} -eq 0 ]]; then
    log_success "All Go tools installed successfully."
    return 0
  else
    log_warning "Some Go tools failed to install: ${failed_tools[*]}"
    return 1
  fi
}

#######################################
# Update tldr cache if tldr is available
# Arguments:
#   None
# Returns:
#   0 on success or if tldr not available, 1 on failure
#######################################
setup_tldr_cache() {
  if ! command -v tldr >/dev/null 2>&1; then
    log_info "tldr not found, skipping cache update"
    return 0
  fi
  
  log_info "Populating tldr cache..."
  if ! tldr --update; then
    log_warning "Failed to update tldr cache."
    return 1
  else
    log_success "tldr cache updated successfully."
    return 0
  fi
}

#######################################
# Main function to orchestrate the mise tools installation process
# Arguments:
#   None
# Returns:
#   0 on success, 1 on failure
#######################################
main() {
  local exit_code=0
  
  log_info "Starting dynamic dev container mise tools setup..."
  
  log_info "GITHUB_TOKEN: ${GITHUB_TOKEN:-not set}"

  # Install mise tools
  if ! install_mise_tools; then
    log_error "Failed to install mise tools"
    exit_code=1
  fi
  
  # Set up .NET environment
  if ! setup_dotnet_environment; then
    log_warning ".NET environment setup failed, continuing..."
    exit_code=1
  fi
  
  # Set up Go tools
  if ! setup_go_tools; then
    log_warning "Go tools setup failed, continuing..."
    exit_code=1
  fi
  
  # Set up tldr cache (continue even if this fails)
  if ! setup_tldr_cache; then
    log_warning "tldr cache setup failed, continuing..."
  fi

  if [[ $exit_code -eq 0 ]]; then
    log_success "All mise tools and development environments set up successfully!"
  else
    log_warning "Setup completed with some failures. Check logs above for details."
  fi
  
  return $exit_code
}

if ! (return 0 2>/dev/null); then
  main "$@"
fi
