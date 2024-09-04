#!/bin/bash

set -e

# Load environment variables from .env file
if [ -f ../.env ]; then
    export $(cat ../.env | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if required variables are set
if [ -z "$PRIMARY_IP" ] || [ -z "$REPLICATOR_PASSWORD" ]; then
    echo "Error: PRIMARY_IP and/or REPLICATOR_PASSWORD are not set in the .env file"
    exit 1
fi

# Update recovery.conf with the primary server IP and password
sed -i "s/PRIMARY_IP/$PRIMARY_IP/" ../secondary_server/conf/recovery.conf
sed -i "s/replicator_password/$REPLICATOR_PASSWORD/" ../secondary_server/conf/recovery.conf

echo "Stopping any running containers..."
docker-compose -f ../secondary_server/docker-compose.yml down

echo "Ensuring Docker volume exists..."
docker volume create secondary_server_replica_data

echo "Setting correct permissions for Docker volume..."
sudo mkdir -p /var/lib/docker/volumes/secondary_server_replica_data/_data
sudo chmod 777 /var/lib/docker/volumes/secondary_server_replica_data/_data

echo "Clearing the replica's data directory..."
sudo rm -rf /var/lib/docker/volumes/secondary_server_replica_data/_data/*

echo "Using pg_basebackup to copy the database from the primary..."
if docker run --rm \
    -v secondary_server_replica_data:/var/lib/postgresql/data \
    --network host \
    -e PGPASSWORD=$REPLICATOR_PASSWORD \
    postgres:13 \
    pg_basebackup -h $PRIMARY_IP -D /var/lib/postgresql/data -P -U replicator; then
    echo "pg_basebackup completed successfully"
else
    echo "Error: pg_basebackup failed"
    exit 1
fi

echo "Copying the recovery.conf file to the data directory..."
if sudo cp ../secondary_server/conf/recovery.conf /var/lib/docker/volumes/secondary_server_replica_data/_data/; then
    echo "recovery.conf copied successfully"
else
    echo "Error: Failed to copy recovery.conf"
    exit 1
fi

echo "Starting all services..."
if docker-compose -f ../secondary_server/docker-compose.yml up -d; then
    echo "Services started successfully"
else
    echo "Error: Failed to start services"
    exit 1
fi

echo "Secondary server initialized and connected to primary at $PRIMARY_IP"
echo "You can check the logs of the replica container for any issues:"
echo "docker logs postgres_replica"