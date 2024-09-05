#!/bin/bash
set -e

# Function to log messages
log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1"
}

log "Starting primary database setup..."

# Switch to postgres user and run the rest of the script
exec su postgres << EOF
# Redefine log function in this subshell
log() {
    echo "\$(date "+%Y-%m-%d %H:%M:%S") - \$1"
}

# Check if PGDATA is set, if not set it to the default
PGDATA=\${PGDATA:-/var/lib/postgresql/data/pgdata}

# Initialize the database if it's empty or not a valid cluster
if [ -z "\$(ls -A \$PGDATA)" ] || [ ! -f "\$PGDATA/PG_VERSION" ]; then
    log "Initializing PostgreSQL database..."
    initdb \$PGDATA
    log "PostgreSQL database initialized."
fi

# Generate pg_hba.conf
log "Generating pg_hba.conf..."
cat > \$PGDATA/pg_hba.conf <<EOC
# Allow replication connections from the secondary server
host replication ${REPLICATION_USER} ${SECONDARY_IP}/32 md5

# Allow normal connections
host all all all md5
EOC

chmod 600 \$PGDATA/pg_hba.conf
log "pg_hba.conf generated and permissions set."

# Start PostgreSQL
log "Starting PostgreSQL..."
pg_ctl -D \$PGDATA -l \$PGDATA/logfile start

# Wait for PostgreSQL to be ready
log "Waiting for PostgreSQL to be ready..."
until pg_isready -h localhost -p 5432; do
    log "PostgreSQL is unavailable - sleeping"
    sleep 1
done
log "PostgreSQL is ready!"

# Create replication user if it doesn't exist
log "Checking for replication user..."
if ! psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${REPLICATION_USER}'" | grep -q 1; then
    log "Creating replication user..."
    psql -c "CREATE USER ${REPLICATION_USER} REPLICATION LOGIN ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';"
    log "Replication user created."
else
    log "Replication user already exists."
fi

# Keep the container running
log "Setup complete. Keeping container running..."
tail -f \$PGDATA/logfile
EOF