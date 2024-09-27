# Create a new file named init-mirror.sh with the following content:
#!/bin/bash

# Wait for the mirror database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h mirror -U $POSTGRES_USER -d $POSTGRES_DB -c '\q'; do
  >&2 echo "Mirror is unavailable - sleeping"
  sleep 1
done

# Dump the primary database
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $PRIMARY_HOST -p $PRIMARY_PORT -U $POSTGRES_USER -d $POSTGRES_DB > /tmp/dump.sql

# Restore the dump to the mirror database
PGPASSWORD=$POSTGRES_PASSWORD psql -h mirror -U $POSTGRES_USER -d $POSTGRES_DB < /tmp/dump.sql

echo "Database mirroring completed"