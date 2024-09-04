#!/bin/bash

# Ensure PRIMARY_IP is set
if [ -z "$PRIMARY_IP" ]; then
    echo "Please set the PRIMARY_IP environment variable before running this script."
    exit 1
fi

# Ensure REPLICATOR_PASSWORD is set
if [ -z "$REPLICATOR_PASSWORD" ]; then
    echo "Please set the REPLICATOR_PASSWORD environment variable before running this script."
    exit 1
fi

# Update recovery.conf with the primary server IP
sed -i "s/PRIMARY_IP/$PRIMARY_IP/" ../secondary_server/conf/recovery.conf
sed -i "s/replicator_password/$REPLICATOR_PASSWORD/" ../secondary_server/conf/recovery.conf

# Start the replica server
docker-compose -f ../secondary_server/docker-compose.yml up -d replica

# Wait for the replica to start
sleep 10

# Stop the replica
docker-compose -f ../secondary_server/docker-compose.yml stop replica

# Clear the replica's data directory
sudo rm -rf /var/lib/docker/volumes/secondary_server_replica_data/_data/*

# Use pg_basebackup to copy the database from the primary
docker run --rm \
    -v secondary_server_replica_data:/var/lib/postgresql/data \
    --network host \
    -e PGPASSWORD=$REPLICATOR_PASSWORD \
    postgres:13 \
    pg_basebackup -h $PRIMARY_IP -D /var/lib/postgresql/data -P -U replicator

# Start all services
docker-compose -f ../secondary_server/docker-compose.yml up -d

echo "Secondary server initialized and connected to primary at $PRIMARY_IP"