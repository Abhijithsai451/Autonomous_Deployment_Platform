#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Core configurations
NETWORK_NAME="cortexops_shared_network"
INFRA_COMPOSE="infrastructure/docker/docker-compose.infra.yml"
APPS_COMPOSE="infrastructure/docker/docker-compose.apps.yml"

echo "========================================="
echo "   Starting CortexOps Platform From Root "
echo "========================================="

# 1. Ensure the shared network exists before starting services
if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "🌐 Creating shared external network: $NETWORK_NAME..."
    docker network create "$NETWORK_NAME"
else
    echo "🌐 Shared network '$NETWORK_NAME' already exists."
fi

# 2. Spin up Core Infrastructure Frameworks (Postgres, NATS, Keycloak, Redis)
# Running from root means --env-file is simply '.env'
echo "🏗️  Launching Core Infrastructure (Databases & Brokers)..."
docker compose --env-file .env -f "$INFRA_COMPOSE" up -d

echo "⏳ Waiting a few seconds for core services to stabilize..."
sleep 5

# 3. Spin up Application Services (Identity API, etc.)
# Docker build context natively remains at the repo root now!
echo "⚡ Launching Application Services..."
docker compose --env-file .env -f "$APPS_COMPOSE" up --build -d

echo "========================================="
echo "✅ All systems are online!"
echo "📍 Identity API: http://localhost:8000"
echo "📍 Keycloak:     http://localhost:8080"
echo "📍 NATS Broker:  localhost:4222"
echo "========================================="
echo "💡 To view logs, run: docker compose -f $APPS_COMPOSE logs -f"