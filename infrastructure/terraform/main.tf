terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

provider "docker" {}

# Create a dedicated network so your Python apps can easily find them later
resource "docker_network" "cortexops_network" {
  name = "cortexops_network"
}

# ----------------------------------------------------
# REDIS CACHE CONFIGURATION
# ----------------------------------------------------
resource "docker_image" "redis" {
  name         = "redis:7.2-alpine"
  keep_locally = true
}

resource "docker_container" "redis_cache" {
  image   = docker_image.redis.image_id
  name    = "cortexops_cache"
  network_mode = docker_network.cortexops_network.name

  ports {
    internal = 6379
    external = 6379
  }

  command = ["redis-server", "--appendonly", "yes"]
}

# ----------------------------------------------------
# POSTGRESQL DATABASE CONFIGURATION
# ----------------------------------------------------
resource "docker_image" "postgres" {
  name         = "postgres:16-alpine"
  keep_locally = true
}

resource "docker_container" "postgres_db" {
  image   = docker_image.postgres.image_id
  name    = "cortexops_db"
  network_mode = docker_network.cortexops_network.name

  ports {
    internal = 5432
    external = 5432
  }

  env = [
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=postgres_password",
    "POSTGRES_DB=cortexops_main" # Main connection endpoint
  ]

  # Provision isolated DBs on startup using a simple init script
  # (Postgres docker container automatically executes scripts in this folder)
  upload {
    target = "/docker-entrypoint-initdb.d/init-schemas.sh"
    content = <<-EOT
      #!/bin/bash
      set -e
      psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
          CREATE DATABASE identity;
          CREATE DATABASE organization;
          CREATE DATABASE workflows;
      EOSQL
    EOT
  }
}