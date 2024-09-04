#!/bin/bash

source .env

# Create replication user
docker-compose exec db psql -U $DB_USER -d $DB_NAME -c "
CREATE USER $REPLICATION_USER WITH REPLICATION ENCRYPTED PASSWORD '$REPLICATION_PASSWORD';
"

# Update postgresql.conf
docker-compose exec db bash -c "echo 'wal_level = replica' >> /var/lib/postgresql/data/postgresql.conf"
docker-compose exec db bash -c "echo 'max_wal_senders = 10' >> /var/lib/postgresql/data/postgresql.conf"
docker-compose exec db bash -c "echo 'max_replication_slots = 10' >> /var/lib/postgresql/data/postgresql.conf"

# Update pg_hba.conf
docker-compose exec db bash -c "echo 'host replication $REPLICATION_USER 0.0.0.0/0 md5' >> /var/lib/postgresql/data/pg_hba.conf"

# Restart PostgreSQL
docker-compose restart db

echo "Replication setup complete. Now set up the secondary server."