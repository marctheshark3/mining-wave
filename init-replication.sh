#!/bin/bash

# This script should be run from the root directory containing both primary_server and secondary_server folders

# Load environment variables
source .env

# Stop the secondary container
docker-compose -f secondary_server/docker-compose.yml down

# Clear the secondary data directory
sudo rm -rf secondary_server/data

# Create a base backup of the primary
docker-compose -f primary_server/docker-compose.yml exec postgres_primary pg_basebackup -h localhost -D /tmp/secondary_data -U ${REPLICATION_USER} -v -P -R

# Move the backup to the secondary data directory
sudo mv /tmp/secondary_data secondary_server/data

# Create recovery.signal file to initiate recovery mode
sudo touch secondary_server/data/recovery.signal

# Start the secondary container
docker-compose -f secondary_server/docker-compose.yml up -d

echo "Replication initialized. Check the secondary logs for confirmation."