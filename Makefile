IMAGE_NAME := ghcr.io/sarg3nt/dynamic-dev-container
IMAGE_TAG := 1.0.4
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | sed 's/[\/_]/-/g')
# Get absolute path - works on both Linux and macOS
CURRENT_DIR := $(shell cd "$(shell pwd)" && pwd)

# ---------------------------------------------------------------------------
# Supply-chain pinning.
#
# Rocky base image: the Dockerfile defaults to the OCI index (multi-arch
# manifest list) digest so cross-platform buildx works. Single-arch `make
# build` targets override with the per-arch manifest digest so the registry
# cannot re-point the index without us noticing. Re-pin on every image bump:
#   docker buildx imagetools inspect rockylinux/rockylinux:10-ubi
#
# mise: fetched directly from GitHub releases inside the Dockerfile with a
# pinned SHA256 per arch (see MISE_SHA256_* ARGs in the Dockerfile). Re-pin
# from https://github.com/jdx/mise/releases/download/v<ver>/SHASUMS256.txt
# when bumping MISE_VERSION.
# ---------------------------------------------------------------------------
ROCKY_TAG := 10-ubi
ROCKY_INDEX_DIGEST  := sha256:02564b26a5d147fcdbd1058abd9b358008f5608b382dcb288cfc718d627256cb
ROCKY_AMD64_DIGEST  := sha256:839c8620a6bd5e3afc884243eeb59c0741e9ffc0a6f75c6ccee020afd1308cce
ROCKY_ARM64_DIGEST  := sha256:f8c623fb78b476a1ac29040420a3593d8a867f763a76417d57933de97334ed3e

# Detect host platform so `make build` produces a usable local image on both
# linux/amd64 hosts and Apple Silicon (linux/arm64) hosts.
HOST_ARCH := $(shell uname -m)
ifeq ($(HOST_ARCH),arm64)
  HOST_PLATFORM := linux/arm64
  HOST_ROCKY_DIGEST := $(ROCKY_ARM64_DIGEST)
else ifeq ($(HOST_ARCH),aarch64)
  HOST_PLATFORM := linux/arm64
  HOST_ROCKY_DIGEST := $(ROCKY_ARM64_DIGEST)
else
  HOST_PLATFORM := linux/amd64
  HOST_ROCKY_DIGEST := $(ROCKY_AMD64_DIGEST)
endif

PLATFORMS := linux/amd64,linux/arm64
TAG := $(IMAGE_NAME):$(IMAGE_TAG)-$(GIT_BRANCH)

# Build-arg bundles. Native builds pin the per-arch base-image manifest.
# Multi-platform builds pin the index (buildx applies the same ARG to both
# platforms so we cannot use per-arch digests in a single invocation).
NATIVE_BUILD_ARGS := \
  --build-arg GITHUB_TOKEN=${GITHUB_TOKEN} \
  --build-arg BASE_IMAGE=rockylinux/rockylinux:$(ROCKY_TAG)@$(HOST_ROCKY_DIGEST)

MULTI_BUILD_ARGS := \
  --build-arg GITHUB_TOKEN=${GITHUB_TOKEN} \
  --build-arg BASE_IMAGE=rockylinux/rockylinux:$(ROCKY_TAG)@$(ROCKY_INDEX_DIGEST)

# `build`: native single-arch build via buildx, loaded into the local docker
# image store. Works the same on Intel and Apple Silicon hosts.
.PHONY: build
build:
	docker buildx build --platform $(HOST_PLATFORM) $(NATIVE_BUILD_ARGS) -t "$(TAG)" --load .

.PHONY: build-no-cache
build-no-cache:
	docker buildx build --platform $(HOST_PLATFORM) $(NATIVE_BUILD_ARGS) --progress=plain --no-cache -t "$(TAG)" --load .

# `build-multi`: cross-compile both archs to verify the build works everywhere.
# Cannot use --load (buildx --load is single-platform only); writes to the
# buildx cache instead so the layers are exercised but no local image is loaded.
.PHONY: build-multi
build-multi:
	docker buildx build --platform $(PLATFORMS) $(MULTI_BUILD_ARGS) -t "$(TAG)" .

# `build-push-multi`: build both archs and push as a multi-arch manifest.
.PHONY: build-push-multi
build-push-multi:
	docker buildx build --platform $(PLATFORMS) $(MULTI_BUILD_ARGS) -t "$(TAG)" --push .

.PHONY: run
run:
	docker run --mount type=bind,source="${CURRENT_DIR}",target=/workspaces/working \
		-w /workspaces/working -it --rm -u "vscode" \
		"$(TAG)" zsh

.PHONY: push
push:
	docker push "$(TAG)"
