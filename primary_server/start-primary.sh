#!/bin/bash
set -e

# Function to log messages
log() {
    echo "$(date "+%Y-%m-%d %H:%M:%S") - $1"
}

log "Starting primary database setup..."

# Generate pg_hba.conf
log "Generating pg_hba.conf..."
cat > /var/lib/postgresql/data/pg_hba.conf <<EOF
# Allow replication connections from the secondary server
host replication ${REPLICATION_USER} ${SECONDARY_IP}/32 md5

# Allow normal connections
host all all all md5
EOF

# Make sure the file has the correct permissions
chown postgres:postgres /var/lib/postgresql/data/pg_hba.conf
chmod 600 /var/lib/postgresql/data/pg_hba.conf
log "pg_hba.conf generated and permissions set."

# Switch to postgres user and run the rest of the script
exec su postgres -c "
    # Initialize the database if it's empty
    if [ -z \"\$(ls -A /var/lib/postgresql/data)\" ]; then
        log \"Initializing PostgreSQL database...\"
        initdb /var/lib/postgresql/data
        log \"PostgreSQL database initialized.\"
    fi

    # Start PostgreSQL
    log \"Starting PostgreSQL...\"
    pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/data/logfile start

    # Wait for PostgreSQL to be ready
    log \"Waiting for PostgreSQL to be ready...\"
    until pg_isready -h localhost -p 5432; do
        log \"PostgreSQL is unavailable - sleeping\"
        sleep 1
    done
    log \"PostgreSQL is ready!\"

    # Keep the container running
    log \"Setup complete. Keeping container running...\"
    tail -f /var/lib/postgresql/data/logfile
"