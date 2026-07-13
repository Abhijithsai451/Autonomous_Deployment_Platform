docker exec -i postgres_db psql -U user -d postgres < ../apps/identity/scripts/seed_data.sql
# To check the file structure inside the docker
#docker exec -it cortexops_identity find /app