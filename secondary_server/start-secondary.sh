#!/bin/bash
set -e

log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1"
}

log "Starting secondary database setup..."

# Switch to postgres user and run the rest of the script
exec su postgres << EOF
# Redefine log function in this subshell
log() {
    echo "\$(date "+%Y-%m-%d %H:%M:%S") - \$1"
}

PGDATA=\${PGDATA:-/var/lib/postgresql/data/pgdata}

if [ -z "\$(ls -A \$PGDATA)" ]; then
    log "Initializing secondary database..."
    
    # Create a pgpass file for passwordless connection
    echo "\${PRIMARY_HOST}:\${PRIMARY_PORT}:*:\${REPLICATION_USER}:\${REPLICATION_PASSWORD}" > ~/.pgpass
    chmod 600 ~/.pgpass

    # Use pg_basebackup to clone the primary
    pg_basebackup -h \${PRIMARY_HOST} -p \${PRIMARY_PORT} -D \$PGDATA -U \${REPLICATION_USER} -P -v

    # Create recovery.conf (for PostgreSQL 12, we use standby.signal and postgresql.auto.conf)
    touch \$PGDATA/standby.signal
    echo "primary_conninfo = 'host=\${PRIMARY_HOST} port=\${PRIMARY_PORT} user=\${REPLICATION_USER} password=\${REPLICATION_PASSWORD}'" >> \$PGDATA/postgresql.auto.conf
    echo "hot_standby = on" >> \$PGDATA/postgresql.auto.conf

    log "Secondary database initialized and configured for replication."
fi

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

# Keep the container running
log "Setup complete. Keeping container running..."
tail -f \$PGDATA/logfile
EOF