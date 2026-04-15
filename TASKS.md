# TASKS

This task file is for Claude Code and I to work on tasks in this repository.
This repository is a generic and dynamic dev container for Visual Studio Code.

## Make work with a M series Macintosh

The dev container was originally built to work on Linux and WSL in Windows.
This task is to fix issues preventing the dev container from working my new M5 MacBook Pro.

1. You will do a deep dive into the architecture of this project and once you have a deep understanding of how it works you will start by create a claude.md file for yourself so you have a full grasp of how the project works in the future.
2. You will discover all the issues with the dev container running on a M series macintosh and then make a plan in this document to fix them.  You will make sure you look at every piece of software being installed, such as all of the mise tools, overall config and scripts used to build the container.
3. You will also update the Makefile to fully support multi-arch builds.
4. You will update the Git workflows to build multi-arch builds.