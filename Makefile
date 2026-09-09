IMAGE := docker.io/mapalmeira/moedeiro
TAG ?=
PLATFORMS := linux/amd64,linux/arm64
PODMAN ?= podman
FRONTEND_BUILD_IMAGE ?= node:24-alpine
HOST_ARCH := $(shell uname -m)

ifeq ($(HOST_ARCH),x86_64)
HOST_PLATFORM := linux/amd64
else ifeq ($(HOST_ARCH),aarch64)
HOST_PLATFORM := linux/arm64
else
HOST_PLATFORM := linux/$(HOST_ARCH)
endif

FRONTEND_BUILD_PLATFORM ?= $(HOST_PLATFORM)

.DEFAULT_GOAL := help

.PHONY: help check-tag frontend-build clean-manifest build push release

help:
	@printf '%s\n' \
		'Usage:' \
		'  make frontend-build        Build the production frontend once in a native Node container.' \
		'  make build TAG=<version>   Build a multi-architecture image manifest.' \
		'  make push TAG=<version>    Push the version tag and update latest.' \
		'  make release TAG=<version> Build and push the image.'

check-tag:
	@test -n "$(TAG)" || { \
		echo 'TAG is required (for example: make release TAG=1.2.3)'; \
		exit 1; \
	}

frontend-build:
	$(PODMAN) run --rm \
		--platform $(FRONTEND_BUILD_PLATFORM) \
		--userns=keep-id \
		--volume "$(CURDIR)/frontend:/app/frontend:Z" \
		--workdir /app/frontend \
		$(FRONTEND_BUILD_IMAGE) \
		sh -c 'npm ci && npm run build:production'

clean-manifest: check-tag
	$(PODMAN) manifest rm --ignore $(IMAGE):$(TAG)

build: check-tag frontend-build clean-manifest
	$(PODMAN) build \
		--file Containerfile \
		--platform $(PLATFORMS) \
		--manifest $(IMAGE):$(TAG) \
		.

push: check-tag
	$(PODMAN) manifest push --all \
		$(IMAGE):$(TAG) \
		docker://$(IMAGE):$(TAG)

	$(PODMAN) manifest push --all \
		$(IMAGE):$(TAG) \
		docker://$(IMAGE):latest

release: build push