#!/bin/bash
set -e

# Generate pg_hba.conf
cat > /etc/postgresql/pg_hba.conf <<EOF
# Allow replication connections from the secondary server
host replication ${REPLICATION_USER} ${SECONDARY_IP}/32 md5

# Allow normal connections
host all all all md5
EOF

# Make sure the file has the correct permissions
chown postgres:postgres /etc/postgresql/pg_hba.conf
chmod 600 /etc/postgresql/pg_hba.conf

# Start PostgreSQL
exec docker-entrypoint.sh "$@"