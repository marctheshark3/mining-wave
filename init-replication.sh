#!/bin/bash

# This script should be run from the root directory containing both primary_server and secondary_server folders

# Load environment variables
source .env

# Stop the secondary containers
docker-compose -f secondary_server/docker-compose.yml down

# Clear the secondary data directory
sudo rm -rf secondary_server/data

# Create a base backup of the primary
docker-compose -f primary_server/docker-compose.yml exec postgres_primary pg_basebackup -h localhost -D /tmp/secondary_data -U ${REPLICATION_USER} -v -P -R

# Move the backup to the secondary data directory
sudo mv /tmp/secondary_data secondary_server/data

# Create recovery.signal file to initiate recovery mode
sudo touch secondary_server/data/recovery.signal

# Start the secondary containers (PostgreSQL and API)
docker-compose -f secondary_server/docker-compose.yml up -d --build

echo "Replication initialized and API service started. Check the secondary logs for confirmation."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose -f secondary_server/docker-compose.yml exec -T postgres_secondary pg_isready; do
  sleep 1
done

# Check replication status
echo "Checking replication status..."
docker-compose -f secondary_server/docker-compose.yml exec -T postgres_secondary psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT * FROM pg_stat_wal_receiver;"

# Test API
echo "Testing API..."
curl -s http://localhost:8000
echo ""
curl -s http://localhost:8000/tables
echo ""

echo "Initialization complete. API is accessible at http://localhost:8000"