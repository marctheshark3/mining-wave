#!/bin/bash

# This script should be run from the root directory containing both primary_server and secondary_server folders

# Load environment variables
set -a
source .env
set +a

# Stop the secondary containers
docker-compose -f secondary_server/docker-compose.yml down

# Clear the secondary data directory
sudo rm -rf secondary_server/data
mkdir -p secondary_server/data

# Create a base backup of the primary
echo $PRIMARY_IP $REPLICATION_USER $POSTGRES_USER $POSTGRES_DB
echo "Creating base backup from primary server..."
PGPASSWORD=$REPLICATION_PASSWORD pg_basebackup -h $PRIMARY_IP -D secondary_server/data -U $REPLICATION_USER -v -P -R

# Create recovery.signal file to initiate recovery mode
touch secondary_server/data/recovery.signal
ls secondary_server/conf
# Set correct permissions
sudo chown -R 999:999 secondary_server/data
sudo chown 999:999 secondary_server/conf/postgresql.conf
sudo chown 999:999 secondary_server/conf/pg_hba.conf
sudo chown 999:999 secondary_server/conf/pg_ident.conf

# Start the secondary containers (PostgreSQL and API)
docker-compose -f secondary_server/docker-compose.yml up -d --build --force-recreate

echo "Replication initialized and API service started. Check the secondary logs for confirmation."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose -f secondary_server/docker-compose.yml exec -T mirror pg_isready; do
  sleep 1
done

# Check replication status
echo "Checking replication status..."
docker-compose -f secondary_server/docker-compose.yml exec -T mirror psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM pg_stat_wal_receiver;"

# Test API
echo "Testing API..."
curl -s http://localhost:8000
echo ""
curl -s http://localhost:8000/tables
echo ""

echo "Initialization complete. API is accessible at http://localhost:8000"