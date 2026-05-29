#!/bin/sh
#
# Use socat to create a new listening unix socket inside the dev container and forward all traffic to the host's docker socket.
# This allows us to set custom permissions on new socket without affecting the permissions on the host's docker socket.

# cspell:ignore dind socat vscr

# The following two statements are here to get our external docker socket into the dev container in a way that
# we do not need to sudo to use Docker.
# Delete the existing docker socket.
sudo rm /var/run/docker.sock > /dev/null 2>&1

# Use socat to mount our passed in docker socket to the correct docker.sock version.
# The disable directive must sit immediately above the command; an intervening
# comment stops shellcheck applying it, which is why SC2188 leaked before. The
# stray `> /dev/null` after `&` (a command-less redirect) was the SC2188 cause
# and is removed — socat output already goes to the log file.
# shellcheck disable=SC2069,SC1105
((sudo socat UNIX-LISTEN:/var/run/docker.sock,fork,mode=660,user=vscode UNIX-CONNECT:/var/run/docker-host.sock) 2>&1 >> /tmp/vscr-dind-socat.log) &

"$@"
