set -e

# Core configurations
NETWORK_NAME="cortexops_shared_network"
INFRA_COMPOSE="infrastructure/docker/docker-compose.infra.yml"
APPS_COMPOSE="infrastructure/docker/docker-compose.apps.yml"
MONITOR_COMPOSE="infrastructure/docker/docker-compose.monitoring.yml"

# ==============================================================================
#  MICROSERVICES
# ==============================================================================
SERVICES=(
    "Identity Service      : 8000 : cortexops_identity      : apps/identity/identity_test.py"
    "Organization Service  : 8001 : cortexops_organization  : apps/organization//org_test.py"
    "Workflow Service      : 8002 : cortexops_workflow      : apps/workflow/workflow_test.py"
    "Agent Runtime Service : 8003 : cortexops_agent_runtime : apps/agent_runtime/agent_runtime_test.py "
    #"Audit Service         : 8002 : cortexops_audit         : tests/test_audit.py"
    #"Workflow Service      : 8003 : cortexops_workflow      : tests/test_workflow.py"
)

test_health() {
    local service_name=$1
    local url=$2
    echo -n " Waiting for $service_name to accept connections ($url)..."

    local attempts=0
    local max_attempts=5
    until [ "$(curl --write-out '%{http_code}' --silent --output /dev/null "$url")" -eq 200 ]; do
        echo -n "."
        sleep 2
        attempts=$((attempts + 1))
        if [ $attempts -eq $max_attempts ]; then
            echo -e "\n Timeout: $service_name failed to respond at $url!"
            exit 1
        fi
    done
    echo " [READY] "
}

echo "========================================="
echo "   Starting Autonomous DEVOPS Platform "
echo "========================================="

if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "Creating shared external network: $NETWORK_NAME..."
    docker network create "$NETWORK_NAME"
else
    echo "Shared network '$NETWORK_NAME' already exists."
fi

echo "Launching Core Infrastructure (Databases & Brokers)..."
docker compose --env-file .env -f "$INFRA_COMPOSE" up -d

echo "Waiting a few seconds for core services to stabilize..."
sleep 2
echo "Launching Core Monitoring Systems (Messaging, Telemetry, Traces)..."
docker compose --env-file .env -f "$MONITOR_COMPOSE" up -d

echo "Waiting a few seconds for Monitoring services to stabilize..."
sleep 2

echo " Launching Application Services..."
docker compose --env-file .env -f "$APPS_COMPOSE" up --build -d

echo "========================================="
echo " Performing Health & Verification Checks"
echo "========================================="
for service in "${SERVICES[@]}"; do
    IFS=":" read -r name port container test_path <<< "$service"
    name=$(echo "$name" | xargs)
    port=$(echo "$port" | xargs)

    test_health "$name" "http://localhost:$port/health"
done

# 5. Loop: Dynamically run unit tests for ALL services
echo "========================================="
echo " Running Service Unit Tests"
echo "========================================="
for service in "${SERVICES[@]}"; do
    IFS=":" read -r name port container test_path <<< "$service"
    name=$(echo "$name" | xargs)
    container=$(echo "$container" | xargs)
    test_path=$(echo "$test_path" | xargs)

    echo ""
    echo "Running tests for: $name ($container)..."
    echo "-----------------------------------------"
    docker exec -t "$container" pytest "$test_path" -v
    echo "-----------------------------------------"
done

echo "========================================="
echo " All systems are online and verified!"
echo "========================================="
echo " To view logs, run: docker compose -f $APPS_COMPOSE logs -f"


