IMAGE := docker.io/mapalmeira/moedeiro
TAG ?=
PLATFORMS := linux/amd64,linux/arm64

.DEFAULT_GOAL := help

.PHONY: help check-tag build push release

help:
	@printf '%s\n' \
		'Usage:' \
		'  make build TAG=<version>    Build a multi-architecture image manifest.' \
		'  make push TAG=<version>     Push the version tag and update latest.' \
		'  make release TAG=<version>  Build and push the image.'

check-tag:
	@test -n "$(TAG)" || { echo 'TAG is required (for example: make release TAG=1.2.3)'; exit 1; }

build: check-tag
	podman build \
		--file Containerfile \
		--platform $(PLATFORMS) \
		--manifest $(IMAGE):$(TAG) \
		.

push: check-tag
	podman manifest push --all $(IMAGE):$(TAG) docker://$(IMAGE):$(TAG)
	podman manifest push --all $(IMAGE):$(TAG) docker://$(IMAGE):latest

release: build push
