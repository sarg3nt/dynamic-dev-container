#!/bin/bash
# Calls the github API to get a list of tags for releases for the given project and repo
# major_minor_version should look like "v1.0" and is optional, if none is given then the latest non beta is returned.
# Docs: https://docs.github.com/en/rest/releases/releases
# Note: This could fail if the repo has a lot of releases and we are behind on major_minor_version by quite a bit.
# 100 per page is the largest amount allowed

set -euo pipefail
IFS=$'\n\t'

# shellcheck source=/dev/null
source "/usr/bin/lib/sh/log.sh"

# Check if user is using Docker Deskop for Windows or the native Docker Engine.
main() {
  local project="${1:-}"
  local repo="${2:-}"
  local major_minor_version="${3:-}"

  if [[ -z "${GITHUB_API_TOKEN:+1}" ]]; then
    log "ERROR: GITHUB_API_TOKEN is not set and is required." "red"
    log "Usage: GITHUB_API_TOKEN=your_token_here get_latest_version.sh project repo [major_minor_version]" "red"
    exit 1
  fi

  if [[ -z "${project}" ]]; then
    log "ERROR: Project is not specified and is required." "red"
    log "Usage: get_latest_version.sh project repo [major_minor_version]" "red"
    exit 1
  fi

  if [[ -z "${repo}" ]]; then
    log "ERROR: Repo is not specified and is required." "red"
    log "Usage: get_latest_version.sh project repo [major_minor_version]" "red"
    exit 1
  fi

  # If a major_minor_version is passed then we attempt to get the latest patch release for it
  if [[ -n "${major_minor_version}" ]]; then
    curl -s --request GET \
      --url "https://api.github.com/repos/${project}/${repo}/releases?per_page=100" \
      --header "Authorization: Bearer ${GITHUB_API_TOKEN}" \
      --header "X-GitHub-Api-Version: 2022-11-28" |
      jq -r '.[]|select(.tag_name| startswith("'"$major_minor_version"'"))' |
      jq -r '.tag_name' |
      grep -v 'beta\|rc' |
      sed -E 's,^[^0-9]*([0-9]+.*).*$,\1,' |
      sort -Vr |
      head -1
  else
    # If no major_minor_version is passed just get the latest release
    curl -s --request GET \
      --url "https://api.github.com/repos/${project}/${repo}/releases/latest" \
      --header "Authorization: Bearer ${GITHUB_API_TOKEN}" \
      --header "X-GitHub-Api-Version: 2022-11-28" |
      jq -r '.tag_name' |
      sed -E 's,^[^0-9]*([0-9]+.*).*$,\1,'
  fi
}

if ! (return 0 2>/dev/null); then
  (main "$@")
fi
