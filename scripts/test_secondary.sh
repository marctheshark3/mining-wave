#!/bin/bash

echo "Testing Secondary Server Configuration..."

# Load environment variables
set -a
source ../.env
set +a

# Function to run psql commands inside the Docker container
docker_psql() {
    docker exec postgres_replica psql -U miningcore -c "$1"
}

# 1. Check if the replica container is running
echo "1. Checking if replica container is running..."
if docker ps | grep -q postgres_replica; then
    echo "   Replica container is running."
else
    echo "   Error: Replica container is not running!"
    exit 1
fi

# 2. Check PostgreSQL version and replication status
echo "2. Checking PostgreSQL version and replication status..."
docker_psql "SELECT version();"
docker_psql "SELECT pg_is_in_recovery();"

# 3. Check replication connection
echo "3. Checking replication connection..."
docker_psql "SELECT * FROM pg_stat_wal_receiver;"

# 4. Check lag between primary and secondary
echo "4. Checking replication lag..."
docker_psql "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"

# 5. Check if any tables exist (assuming 'blocks' table should exist)
echo "5. Checking if 'blocks' table exists..."
docker_psql "\dt blocks"

# 6. Count rows in the 'blocks' table
echo "6. Counting rows in 'blocks' table..."
docker_psql "SELECT COUNT(*) FROM blocks;"

# 7. Check PostgreSQL logs for any errors
echo "7. Checking PostgreSQL logs for errors..."
docker logs postgres_replica | tail -n 50

# 8. Test connection to the primary
echo "8. Testing connection to primary server..."
docker exec postgres_replica pg_isready -h $PRIMARY_IP -p 5432 -U replicator

echo "Secondary server tests completed."