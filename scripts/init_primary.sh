#!/bin/bash

# Load environment variables from .env file
set -a
source ../.env
set +a

# Copy configuration files
docker-compose -f ../primary_server/docker-compose.yml up --abort-on-container-exit

# Restart PostgreSQL to apply new configuration
sudo systemctl restart postgresql

# Create replication user if it doesn't exist
sudo -u postgres psql -c "DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'replicator') THEN
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATOR_PASSWORD}';
  END IF;
END
\$\$;"

echo "Primary server initialized. Please update the PRIMARY_IP in the secondary_server/conf/recovery.conf file."
echo "You may need to open port 5432 in your firewall for replication."