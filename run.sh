#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Core configurations
DOCKER_DIR="infrastructure/docker"
NETWORK_NAME="cortexops_shared_network"

echo "========================================="
echo " Starting CortexOps Ecosystem Stack"
echo "========================================="

# 1. Ensure the shared network exists before starting services
if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo " Creating shared external network: $NETWORK_NAME..."
    docker network create "$NETWORK_NAME"
else
    echo " Shared network '$NETWORK_NAME' already exists."
fi

# 2. Change directory into the docker configuration folder
echo " Navigating to $DOCKER_DIR..."
cd "$DOCKER_DIR"

# 3. Spin up Core Infrastructure Frameworks (Postgres, NATS, Keycloak, Redis)
# Note: We pass --env-file '../../.env' so Compose can parse variables from the root folder
echo "  Launching Core Infrastructure (Databases & Brokers)..."
docker compose --env-file ../../.env -f docker-compose.infra.yml up -d

echo " Waiting a few seconds for core services to stabilize..."
sleep 5

# 4. Spin up Application Services (Identity API, etc.)
echo " Launching Application Services..."
docker compose --env-file ../../.env -f docker-compose.apps.yml up --build -d

echo "========================================="
echo " All systems are online!"
echo " Identity API: http://localhost:8000"
echo " Keycloak:     http://localhost:8080"
echo " NATS Broker:  localhost:4222"
echo "========================================="
echo "💡 To view logs, run: cd $DOCKER_DIR && docker compose -f docker-compose.apps.yml logs -f"