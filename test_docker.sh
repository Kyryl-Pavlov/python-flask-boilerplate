#!/bin/bash
set -e

IMAGE_NAME="flask-boilerplate"
PORT=8000

echo "Building Docker image..."
docker build -t $IMAGE_NAME .

echo "Starting container..."
docker run --rm -d -p $PORT:$PORT --name $IMAGE_NAME $IMAGE_NAME

echo "Waiting for server to start..."
sleep 2

echo "Testing REST health endpoint..."
curl -s http://localhost:$PORT/api/v1/health | python3 -m json.tool

echo "Done. Container is running at http://localhost:$PORT"
echo "GraphQL playground: http://localhost:$PORT/graphql"
echo ""
echo "To stop: docker stop $IMAGE_NAME"
