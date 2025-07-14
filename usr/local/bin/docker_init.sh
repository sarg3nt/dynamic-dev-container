#!/bin/sh
#
# Use socat to create a new listening unix socket inside the dev container and forward all traffic to the host's docker socket.
# This allows us to set custom permissions on new socket without affecting the permissions on the host's docker socket.
#

# cspell:ignore dind socat vscr

# The following two statements are here to get our external docker socket into the dev container in a way that
# we do not need to sudo to use Docker.
# Delete the existing docker socket.
sudo rm /var/run/docker.sock >/dev/null 2>&1

# Shellcheck rule SC2188 is disabled in `.devcontainer/devcontainer.json` because it doesn't seem to be disablable inline.
# shellcheck disable=SC2069,SC1105,SC2188
# Use socat to mount our passed in docker socket to the correct docker.sock version.
( (sudo socat UNIX-LISTEN:/var/run/docker.sock,fork,mode=660,user=vscode UNIX-CONNECT:/var/run/docker-host.sock) 2>&1 >>/tmp/vscr-dind-socat.log) &
>/dev/null

"$@"
