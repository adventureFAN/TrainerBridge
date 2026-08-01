#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="trainerbridge-builder:ubuntu-22.04"
DOCKERFILE="$PROJECT_ROOT/packaging/container/Dockerfile"

if command -v podman >/dev/null 2>&1; then
    CONTAINER_ENGINE="podman"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_ENGINE="docker"
else
    echo "Neither Podman nor Docker was found." >&2
    echo "On Bazzite, Podman is normally already installed." >&2
    exit 1
fi

printf 'Using container engine: %s\n' "$CONTAINER_ENGINE"
printf 'Building Ubuntu 22.04 release environment...\n'

"$CONTAINER_ENGINE" build \
    --file "$DOCKERFILE" \
    --tag "$IMAGE_NAME" \
    "$PROJECT_ROOT"

printf 'Building TrainerBridge release artifacts...\n'

if [[ "$CONTAINER_ENGINE" == "podman" ]]; then
    "$CONTAINER_ENGINE" run \
        --rm \
        --userns=keep-id \
        --security-opt label=disable \
        --env HOME=/tmp/trainerbridge-build-home \
        --volume "$PROJECT_ROOT:/workspace" \
        --workdir /workspace \
        "$IMAGE_NAME"
else
    "$CONTAINER_ENGINE" run \
        --rm \
        --user "$(id -u):$(id -g)" \
        --env HOME=/tmp/trainerbridge-build-home \
        --volume "$PROJECT_ROOT:/workspace" \
        --workdir /workspace \
        "$IMAGE_NAME"
fi
