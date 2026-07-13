docker exec -it -e PYTHONPATH=/app cortexops_identity python /app/apps/identity/scripts/seed_data.py

# To check the file structure inside the docker
#docker exec -it cortexops_identity find /app