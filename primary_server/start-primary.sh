#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until pg_isready; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 1
done

# Generate pg_hba.conf
cat > /var/lib/postgresql/data/pg_hba.conf <<EOF
# Allow replication connections from the secondary server
host replication ${REPLICATION_USER} ${SECONDARY_IP}/32 md5

# Allow normal connections
host all all all md5
EOF

# Make sure the file has the correct permissions
chown postgres:postgres /var/lib/postgresql/data/pg_hba.conf
chmod 600 /var/lib/postgresql/data/pg_hba.conf

# Restart PostgreSQL to apply the new configuration
pg_ctl -D /var/lib/postgresql/data restart

# Keep the container running
tail -f /dev/null