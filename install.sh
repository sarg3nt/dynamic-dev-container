#!/bin/bash
#
# This script will start the dev container and open an interactive prompt into it.
#

set -euo pipefail
IFS=$'\n\t'

# Check if user is using Docker Deskop for Windows or the native Docker Engine.
main() {
  # shellcheck source=/dev/null
  if [[ ! -f "usr/bin/lib/sh/colors.sh" ]]; then
    echo "You do not appear to be in the go-dev-container project directory."
    echo "This script must be ran from the root of the go-dev-container project directory."
    exit 1
  fi
  source "usr/bin/lib/sh/colors.sh"

  local project_path=""
  project_path="${1-}"
  if [[ -z "${project_path}" ]]; then
    echo -e "${RED}The path to your project was not passed in and is required.${NC}"
    echo -e "${CYAN}Usage:${NC} $0 <path-to-your-project>"
    exit 1
  fi

  # Remove trailing slash from project_path if it exists
  project_path="${project_path%/}"

  if [[ ! -d "${project_path}" ]]; then
    echo -e "${RED}The path to your project does not exist.${NC}"
    exit 1
  fi

  echo -e "${BLUE}This script will copy the following directories and files into${NC} ${project_path}"
  echo -e "  .devcontainer"
  echo -e "  .mise.toml"
  echo -e "  cspell.json"
  echo -e "  dev.sh"
  read -r -p "$(echo -e "${CYAN}Do you wish to continue? (y/n): ${NC}")" response
  if [[ "$response" != "y" ]]; then
    echo -e "${RED}Aborting.${NC}"
    exit 1
  fi
  echo ""

  echo -e "${BLUE}Copying files to ${project_path}${NC}"

  echo -e "  ${GREEN}Copying${NC} .devcontainer ${GREEN}directory${NC}"
  cp -r ".devcontainer" "${project_path}/"
  echo -e "  ${GREEN}Copying${NC} .mise.toml"
  cp ".mise.toml" "${project_path}/"
  echo -e "  ${GREEN}Copying${NC} cspell.json"
  cp "cspell.json" "${project_path}/"
  echo -e "  ${GREEN}Copying${NC} dev.sh"
  cp "dev.sh" "${project_path}/"

  echo ""
  echo -e "${CYAN}You must now update the values in the${NC} ${project_path}/.devcontainer/devcontainer.json ${CYAN}and${NC} ${project_path}/dev.sh ${CYAN}files.${NC}"
  echo -e "${CYAN}See${NC} README.md ${CYAN}for instructions.${NC}"

}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
