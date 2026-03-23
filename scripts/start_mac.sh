#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="finally"
CONTAINER_NAME="finally"

cd "$PROJECT_DIR"

# Stop existing container if running
if docker ps -aq -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" && docker rm "$CONTAINER_NAME"
fi

# Build image if --build flag passed or image doesn't exist
if [[ "$1" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

# Run container
docker run -d \
    --name "$CONTAINER_NAME" \
    -v finally-data:/app/db \
    -p 8000:8000 \
    --env-file .env \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:8000"
echo "To stop: ./scripts/stop_mac.sh"

# Open browser if on Mac
if command -v open &>/dev/null; then
    sleep 2 && open http://localhost:8000 &
fi
