# 1. Stop everything running
docker compose -f infrastructure/docker/docker-compose.infra.yml -f infrastructure/docker/docker-compose.apps.yml down

# 2. Prune the build cache (Forces docker to read your local files fresh)
docker builder prune -a -f

# 3. Delete all images associated with this project completely
docker image prune -a -f