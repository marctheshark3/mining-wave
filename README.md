# Mining Wave: PostgreSQL Replication and Mining Core API

Mining Wave is a sophisticated data replication and API system for mining operations. It sets up a PostgreSQL replication system with primary and secondary servers, along with a FastAPI application to serve mining data from the secondary database. The name "Mining Wave" reflects the flow of data from server A to server B, like a wave of information.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
   - [Primary Server Setup](#primary-server-setup)
   - [Secondary Server Setup](#secondary-server-setup)
3. [Usage](#usage)
4. [Troubleshooting](#troubleshooting)
5. [Support the Developer](#support-the-developer)

## Prerequisites

- Docker and Docker Compose installed on both primary and secondary servers
- PostgreSQL client tools installed on the secondary server
- Basic understanding of PostgreSQL and Docker

## Setup Instructions

### Primary Server Setup

1. Navigate to the project directory on your primary server.

2. Create a `.env` file in the root directory:
   ```
   nano .env
   ```
   Add the following content (replace with your actual values):
   ```
   POSTGRES_DB=miningcore
   POSTGRES_USER=miningcore
   POSTGRES_PASSWORD=your_secure_password
   REPLICATION_USER=replicator
   REPLICATION_PASSWORD=your_secure_replication_password
   ```

3. Start the primary PostgreSQL container:
   ```
   cd primary_server
   docker-compose up -d
   ```

4. Create the replication user:
   ```
   docker exec -it postgres_primary psql -U ${POSTGRES_USER} -c "CREATE USER ${REPLICATION_USER} WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';"
   ```

### Secondary Server Setup

1. Copy the entire project directory to the secondary server.

2. Update the `.env` file on the secondary server:
   ```
   nano .env
   ```
   Add the following line, replacing `<primary_server_ip>` with the actual IP of your primary server:
   ```
   PRIMARY_IP=<primary_server_ip>
   ```

3. Run the initialization script:
   ```
   ./init-replication.sh
   ```

## Usage

Mining Wave allows you to replicate your mining database and access it through a user-friendly API. After setup, you can access the API endpoints:

- List all tables: `http://secondary_server_ip:8000/tables`
- Get data from a specific table: `http://secondary_server_ip:8000/table/{table_name}`

Example use cases:
- Retrieve real-time mining statistics
- Access historical mining data
- Monitor mining pool performance
- Analyze block rewards and mining efficiency

## Troubleshooting

If you encounter issues:

1. Check the logs:
   ```
   docker-compose -f secondary_server/docker-compose.yml logs
   ```

2. Ensure all environment variables in the `.env` file are correctly set.

3. Verify that the primary server is accessible from the secondary server.

4. Check the PostgreSQL configuration files for any misconfigurations.

5. Ensure that the replication user has the correct permissions on the primary server.

## Support the Developer

If you find Mining Wave helpful for your mining operations, consider supporting the developer:

- $erg Address: 9gUDVVx75KyZ783YLECKngb1wy8KVwEfk3byjdfjUyDVAELAPUN

Your support is greatly appreciated and helps maintain and improve Mining Wave, ensuring it continues to meet the evolving needs of the mining community!
