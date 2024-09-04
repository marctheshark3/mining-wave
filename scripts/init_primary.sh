#!/bin/bash

# Start the primary server
docker-compose -f ../primary_server/docker-compose.yml up -d

# Wait for the primary server to be ready
sleep 10

# Create replication user
docker exec postgres_primary psql -U miningcore -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator_password';"

echo "Primary server initialized. Please update the PRIMARY_IP in the secondary_server/conf/recovery.conf file."