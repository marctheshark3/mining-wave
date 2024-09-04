#!/bin/bash

# Load environment variables from .env file
set -a
source ../.env
set +a

# Check if required variables are set
if [ -z "$PRIMARY_IP" ] || [ -z "$REPLICATOR_PASSWORD" ]; then
    echo "Please ensure PRIMARY_IP and REPLICATOR_PASSWORD are set in the .env file."
    exit 1
fi

# Update recovery.conf with the primary server IP and password
sed -i "s/PRIMARY_IP/$PRIMARY_IP/" ../secondary_server/conf/recovery.conf
sed -i "s/replicator_password/$REPLICATOR_PASSWORD/" ../secondary_server/conf/recovery.conf

# Stop any running containers
docker-compose -f ../secondary_server/docker-compose.yml down

# Clear the replica's data directory
sudo rm -rf /var/lib/docker/volumes/secondary_server_replica_data/_data

# Use pg_basebackup to copy the database from the primary
docker run --rm \
    -v secondary_server_replica_data:/var/lib/postgresql/data \
    --network host \
    -e PGPASSWORD=$REPLICATOR_PASSWORD \
    postgres:13 \
    pg_basebackup -h $PRIMARY_IP -D /var/lib/postgresql/data -P -U replicator

# Copy the recovery.conf file to the data directory
sudo cp ../secondary_server/conf/recovery.conf /var/lib/docker/volumes/secondary_server_replica_data/_data/

# Start all services
docker-compose -f ../secondary_server/docker-compose.yml up -d

echo "Secondary server initialized and connected to primary at $PRIMARY_IP"