#!/bin/bash
#
# Shared library for parsing .mise.toml files
# Contains common functions used by multiple scripts
#
# cSpell:ignore mise

#######################################
# Parse tools from .mise.toml file with optional section filtering
# Arguments:
#   $1 - tools_array_name (name of the array variable to populate)
#   $2 - section_filter (optional: "include_js" or "exclude_js")
# Returns:
#   Populates the specified array with tool@version entries
#######################################
parse_mise_tools() {
  local tools_array_name="$1"
  local section_filter="${2:-all}"
  local tools_file=".mise.toml"
  local in_tools_section=false
  local in_js_section=false
  
  if [[ ! -f "$tools_file" ]]; then
    log_error "No .mise.toml file found"
    return 1
  fi

  log_info "Parsing tools from $tools_file (filter: $section_filter)"

  while IFS= read -r line; do
    # Remove leading/trailing whitespace
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # Skip empty lines and regular comments (but not section markers)
    [[ -z "$line" || ( "$line" =~ ^# && ! "$line" =~ ^####.*####$ ) ]] && continue
    
    # Check for section headers
    if [[ "$line" == "[tools]" ]]; then
      in_tools_section=true
      in_js_section=false
      continue
    elif [[ "$line" =~ ^\[.*\]$ ]]; then
      in_tools_section=false
      in_js_section=false
      continue
    fi
    
    # Check for JavaScript/Node.js section markers
    if [[ "$line" == "#### Begin JavaScript/Node.js Development ####" ]]; then
      in_js_section=true
      continue
    elif [[ "$line" == "#### End JavaScript/Node.js Development ####" ]]; then
      in_js_section=false
      continue
    fi
    
    # Parse tool entries in [tools] section based on filter
    if [[ "$in_tools_section" == true ]]; then
      local should_include=false
      
      case "$section_filter" in
        "include_js")
          # Only include tools in JS section
          [[ "$in_js_section" == true ]] && should_include=true
          ;;
        "exclude_js")
          # Exclude tools in JS section
          [[ "$in_js_section" == false ]] && should_include=true
          ;;
        "all"|*)
          # Include all tools
          should_include=true
          ;;
      esac
      
      if [[ "$should_include" == true ]]; then
        # Handle both quoted and unquoted tool names
        if [[ "$line" =~ ^[\"\']?([^\"\'=]+)[\"\']?[[:space:]]*=[[:space:]]*[\"\']([^\"\']+)[\"\'].*$ ]]; then
          local tool_name="${BASH_REMATCH[1]}"
          local tool_version="${BASH_REMATCH[2]}"
          
          # Trim whitespace from both name and version
          tool_name=$(echo "$tool_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
          tool_version=$(echo "$tool_version" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
          
          # Use eval to add to the named array
          eval "${tools_array_name}+=(\"${tool_name}@${tool_version}\")"
        fi
      fi
    fi
  done < "$tools_file"
}

#######################################
# Parse aliases from .mise.toml file
# Arguments:
#   $1 - aliases_array_name (name of the associative array variable to populate)
# Returns:
#   Populates the specified associative array with alias entries
#######################################
parse_mise_aliases() {
  local aliases_array_name="$1"
  local tools_file=".mise.toml"
  local in_alias_section=false
  
  if [[ ! -f "$tools_file" ]]; then
    return 0
  fi

  log_info "Parsing aliases from $tools_file"

  while IFS= read -r line; do
    # Remove leading/trailing whitespace
    line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # Skip empty lines and regular comments (but not section markers)
    [[ -z "$line" || ( "$line" =~ ^# && ! "$line" =~ ^####.*####$ ) ]] && continue
    
    # Check for section headers
    if [[ "$line" == "[alias]" ]]; then
      in_alias_section=true
      continue
    elif [[ "$line" =~ ^\[.*\]$ ]]; then
      in_alias_section=false
      continue
    fi
    
    # Parse alias entries in [alias] section
    if [[ "$in_alias_section" == true ]]; then
      if [[ "$line" =~ ^([a-zA-Z0-9_-]+)[[:space:]]*=[[:space:]]*[\"\']([^\"\']+)[\"\'].*$ ]]; then
        local alias_name="${BASH_REMATCH[1]}"
        local alias_value="${BASH_REMATCH[2]}"
        
        # Use eval to add to the named associative array
        eval "${aliases_array_name}[\"${alias_name}\"]=\"${alias_value}\""
      fi
    fi
  done < "$tools_file"
}

#######################################
# Install tools with mise one at a time using aliases if available
# Arguments:
#   $1 - tools_array_name (name of the array with tools to install)
#   $2 - aliases_array_name (name of the associative array with aliases)
#   $3 - global_flag (optional: "-g" for global installation, empty for local)
# Returns:
#   0 on success, 1 on failure
#######################################
install_tools_with_mise() {
  local tools_array_name="$1"
  local aliases_array_name="$2"
  local global_flag="${3:-}"
  
  # Get array length using nameref
  local -n tools_ref="$tools_array_name"
  local -n aliases_ref="$aliases_array_name"
  
  log_info "Found ${#tools_ref[@]} tools to install"
  
  if [[ ${#tools_ref[@]} -eq 0 ]]; then
    log_info "No tools to install"
    return 0
  fi
  
  # Install each tool individually
  for tool_spec in "${tools_ref[@]}"; do
    # Extract tool name and version
    local tool_name="${tool_spec%@*}"
    local tool_version="${tool_spec#*@}"
    
    # Check if tool has an alias
    if [[ -n "${aliases_ref[$tool_name]:-}" ]]; then
      local alias_value="${aliases_ref[$tool_name]}"
      log_info "Installing aliased tool: $tool_name using alias $alias_value@$tool_version"
      # Install using the alias with the provided global flag
      if mise use $global_flag -y "$alias_value@$tool_version"; then
        log_success "Successfully installed $tool_name ($alias_value@$tool_version)"
      else
        log_error "Failed to install $tool_name ($alias_value@$tool_version)"
      fi
    else
      log_info "Installing tool: $tool_name@$tool_version"
      if mise use $global_flag -y "$tool_name@$tool_version"; then
        log_success "Successfully installed $tool_name@$tool_version"
      else
        log_error "Failed to install $tool_name@$tool_version"
      fi
    fi
  done
  
  return 0
}
