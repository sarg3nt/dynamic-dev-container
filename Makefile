IMAGE_NAME := ghcr.io/sarg3nt/dynamic-dev-container
IMAGE_TAG := 1.0.4
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | sed 's/[\/_]/-/g')
# Get absolute path - works on both Linux and macOS
CURRENT_DIR := $(shell cd "$(shell pwd)" && pwd)
# Detect host platform so `make build` produces a usable local image on both
# linux/amd64 hosts and Apple Silicon (linux/arm64) hosts.
HOST_ARCH := $(shell uname -m)
ifeq ($(HOST_ARCH),arm64)
  HOST_PLATFORM := linux/arm64
else ifeq ($(HOST_ARCH),aarch64)
  HOST_PLATFORM := linux/arm64
else
  HOST_PLATFORM := linux/amd64
endif
PLATFORMS := linux/amd64,linux/arm64
TAG := $(IMAGE_NAME):$(IMAGE_TAG)-$(GIT_BRANCH)

# `build`: native single-arch build via buildx, loaded into the local docker
# image store. Works the same on Intel and Apple Silicon hosts.
.PHONY: build
build:
	docker buildx build --platform $(HOST_PLATFORM) --build-arg GITHUB_API_TOKEN=${GITHUB_TOKEN} -t "$(TAG)" --load .

.PHONY: build-no-cache
build-no-cache:
	docker buildx build --platform $(HOST_PLATFORM) --build-arg GITHUB_API_TOKEN=${GITHUB_TOKEN} --progress=plain --no-cache -t "$(TAG)" --load .

# `build-multi`: cross-compile both archs to verify the build works everywhere.
# Cannot use --load (buildx --load is single-platform only); writes to the
# buildx cache instead so the layers are exercised but no local image is loaded.
.PHONY: build-multi
build-multi:
	docker buildx build --platform $(PLATFORMS) --build-arg GITHUB_API_TOKEN=${GITHUB_TOKEN} -t "$(TAG)" .

# `build-push-multi`: build both archs and push as a multi-arch manifest.
.PHONY: build-push-multi
build-push-multi:
	docker buildx build --platform $(PLATFORMS) --build-arg GITHUB_API_TOKEN=${GITHUB_TOKEN} -t "$(TAG)" --push .

.PHONY: run
run:
	docker run --mount type=bind,source="${CURRENT_DIR}",target=/workspaces/working \
		-w /workspaces/working -it --rm -u "vscode" \
		"$(TAG)" zsh

.PHONY: push
push:
	docker push "$(TAG)"
