# Mining Wave

Mining Wave is a PostgreSQL replication setup designed for mining pool operations, with an existing primary database server and a new secondary (replica) server with an integrated API service for interacting with the Ergo blockchain.

## Prerequisites

- Existing PostgreSQL instance running on the primary server
- Docker and Docker Compose installed on both primary and secondary servers
- Git installed on both servers
- Network connectivity between the primary and secondary servers
- Sudo access on the primary server

## Setup Instructions

### On the Primary Server

1. Clone the repository:
   ```
   git clone https://github.com/your-username/mining-wave.git
   cd mining-wave
   ```

2. Initialize the primary server:
   ```
   cd scripts
   chmod +x init_primary.sh
   ./init_primary.sh
   ```

3. Ensure that port 5432 is open in your firewall for the secondary server's IP.

### On the Secondary Server

(Instructions remain the same as in the previous README)

## Usage

### Starting the Services

- On the primary server:
  The existing PostgreSQL service should already be running. No additional action is needed.

- On the secondary server:
  ```
  cd mining-wave/secondary_server
  docker-compose up -d
  ```

### Stopping the Services

- On the primary server:
  The existing PostgreSQL service should keep running.

- On the secondary server:
  ```
  cd mining-wave/secondary_server
  docker-compose down
  ```

### Querying the Database

Use the provided script to query the database:

```
cd mining-wave/scripts
./query_db.sh "YOUR SQL QUERY HERE"
```

For example:
```
./query_db.sh "SELECT * FROM blocks LIMIT 5;"
```

## Components

### Primary Server

The primary server runs an existing PostgreSQL instance that has been configured for replication.

### Secondary Server

(Remains the same as in the previous README)

### API Service

(Remains the same as in the previous README)

## Configuration

- Primary server PostgreSQL configurations are applied to the existing instance.
- Secondary server configurations remain in the `conf` directories.
- The API service configuration is in `secondary_server/api_service/main.py`.

## Troubleshooting

If you encounter issues:

1. On the primary server, check PostgreSQL logs:
   ```
   sudo tail -f /var/log/postgresql/postgresql-13-main.log
   ```

2. On the secondary server, check Docker logs:
   ```
   docker-compose logs
   ```

3. Ensure the PRIMARY_IP is correctly set on the secondary server.

4. Verify network connectivity between the primary and secondary servers.

5. Check that port 5432 is open in the primary server's firewall for the secondary server's IP.

(The rest of the README remains the same)