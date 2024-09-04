#!/bin/bash

# Copy configuration files
docker-compose -f ../primary_server/docker-compose.yml up

# Restart PostgreSQL to apply new configuration
sudo systemctl restart postgresql

# Create replication user
sudo -u postgres psql -c "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator_password';"

echo "Primary server initialized. Please update the PRIMARY_IP in the secondary_server/conf/recovery.conf file."
echo "You may need to open port 5432 in your firewall for replication."