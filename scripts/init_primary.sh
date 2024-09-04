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
if [ -z "$REPLICATOR_PASSWORD" ]; then
    echo "Error: REPLICATOR_PASSWORD is not set in the .env file"
    exit 1
fi

# Change to the correct directory
cd "$(dirname "$0")/.."

echo "Copying configuration files..."
docker-compose -f primary_server/docker-compose.yml up --abort-on-container-exit

echo "Restarting PostgreSQL to apply new configuration..."
if ! sudo systemctl restart postgresql@12-main; then
    echo "Error: Failed to restart PostgreSQL"
    exit 1
fi

echo "Creating replication user..."
if sudo -u postgres psql -c "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'replicator') THEN
            CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATOR_PASSWORD}';
            RAISE NOTICE 'User replicator created successfully';
        ELSE
            RAISE NOTICE 'User replicator already exists';
        END IF;
    END
    \$\$;
"; then
    echo "Replication user setup completed successfully"
else
    echo "Error: Failed to setup replication user"
    exit 1
fi

echo "Primary server initialized successfully."
echo "Please ensure that port 5432 is open in your firewall for replication."