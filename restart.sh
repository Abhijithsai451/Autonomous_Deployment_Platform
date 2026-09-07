#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration Paths
INFRA_COMPOSE="infrastructure/docker/docker-compose.infra.yml"
APPS_COMPOSE="infrastructure/docker/docker-compose.apps.yml"
MONITOR_COMPOSE="infrastructure/docker/docker-compose.monitoring.yml"

SEED_DATABASE="scripts/seed_databases.sh"
if [ "$1" = "--clean" ]; then
    echo "=========================================="
    echo "🧹 RUNNING DEEP CLEAN..."
    echo "=========================================="

    # 1. Stop everything running
    echo "Stopping all containers..."
    docker compose -f "$INFRA_COMPOSE" down -v
    docker compose -f "$APPS_COMPOSE" down -v
    docker compose -f "$MONITOR_COMPOSE" down -v

    # 2. Prune the build cache (Forces docker to read local files fresh)
    echo "Pruning Docker builder cache..."
    docker builder prune -a -f

    # 3. Delete all images associated with this project completely
    echo "Pruning unused images..."
    docker image prune -a -f

    echo "✅ Deep clean complete!"
    ./run.sh

elif [ "$1" = "--later" ]; then
    echo "Pruning unused images..."
else
    echo "=========================================="
    echo "🔄 RESETTING CONTAINERS & STARTING UP..."
    echo "=========================================="

    # 1. Take down all app and infra containers completely (including volumes)
    echo "Removing containers and volumes (-v)..."
    docker compose -f "$INFRA_COMPOSE" down -v
    docker compose -f "$APPS_COMPOSE" down -v
    docker compose -f "$MONITOR_COMPOSE" down -v

    # 2. Fire up the startup runner script clean
    if [ -f "./run.sh" ]; then
        echo "Starting fresh stack via ./run.sh..."
        ./run.sh

    else
        echo " Error: ./run.sh not found in the current directory!"
        exit 1
    fi
fi