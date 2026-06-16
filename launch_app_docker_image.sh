#!/bin/bash
# Builds and launches a single service container (no infrastructure).
# Usage: ./launch_app_docker_image.sh [service]   (default: app)
set -e

SERVICE="${1:-app}"
IMAGE_NAME="flask-boilerplate-${SERVICE}"
PORT=5000

echo "Building Docker image for service: $SERVICE..."
docker build -f "services/${SERVICE}/Dockerfile" -t "$IMAGE_NAME" .

echo "Starting container..."
docker run --rm -d -p $PORT:$PORT --name "$IMAGE_NAME" "$IMAGE_NAME"

echo "Waiting for server to start..."
sleep 2

echo "Testing REST health endpoint..."
curl -s http://localhost:$PORT/api/v1/health | python3 -m json.tool

echo "Done. Container is running at http://localhost:$PORT"
echo "GraphQL playground: http://localhost:$PORT/graphql"
echo ""
echo "To stop: docker stop $IMAGE_NAME"
