# PostgreSQL Replication and Mining Core API

This project sets up a PostgreSQL replication system with a primary and secondary server, along with a FastAPI application to serve data from the secondary database.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Directory Structure](#directory-structure)
3. [Setup Instructions](#setup-instructions)
   - [Primary Server Setup](#primary-server-setup)
   - [Secondary Server Setup](#secondary-server-setup)
4. [Usage](#usage)
5. [Troubleshooting](#troubleshooting)
6. [Contributing](#contributing)
7. [Support the Developer](#support-the-developer)

## Prerequisites

- Docker and Docker Compose installed on both primary and secondary servers
- PostgreSQL client tools installed on the secondary server
- Basic understanding of PostgreSQL and Docker

## Directory Structure

```
/
├── primary_server/
│   ├── docker-compose.yml
│   ├── data/
│   └── conf/
│       ├── postgresql.conf
│       └── pg_hba.conf
├── secondary_server/
│   ├── docker-compose.yml
│   ├── data/
│   ├── conf/
│   │   ├── postgresql.conf
│   │   ├── pg_hba.conf
│   │   └── pg_ident.conf
│   └── api/
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
├── .env
└── init-replication.sh
```

## Setup Instructions

### Primary Server Setup

1. Create the necessary directories:
   ```
   mkdir -p primary_server/{data,conf}
   ```

2. Create and edit the Docker Compose file:
   ```
   nano primary_server/docker-compose.yml
   ```
   Add the following content:
   ```yaml
   version: '3'
   
   services:
     postgres_primary:
       image: postgres:12
       container_name: postgres_primary
       environment:
         POSTGRES_DB: ${POSTGRES_DB}
         POSTGRES_USER: ${POSTGRES_USER}
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
       volumes:
         - ./data:/var/lib/postgresql/data
         - ./conf:/etc/postgresql
       ports:
         - "5432:5432"
       command: 
         - "postgres"
         - "-c"
         - "config_file=/etc/postgresql/postgresql.conf"
   ```

3. Create and edit the configuration files:
   ```
   nano primary_server/conf/postgresql.conf
   ```
   Add the following content:
   ```
   listen_addresses = '*'
   wal_level = replica
   max_wal_senders = 10
   max_replication_slots = 10
   hot_standby = on
   ```

   ```
   nano primary_server/conf/pg_hba.conf
   ```
   Add the following content:
   ```
   # TYPE  DATABASE        USER            ADDRESS                 METHOD
   local   all             all                                     trust
   host    all             all             127.0.0.1/32            trust
   host    all             all             ::1/128                 trust
   host    replication     all             127.0.0.1/32            trust
   host    replication     all             ::1/128                 trust
   host    replication     replicator      0.0.0.0/0               md5
   ```

4. Create a `.env` file in the root directory:
   ```
   nano .env
   ```
   Add the following content (replace with your actual values):
   ```
   POSTGRES_DB=miningcore
   POSTGRES_USER=miningcore
   POSTGRES_PASSWORD=your_password
   REPLICATION_USER=replicator
   REPLICATION_PASSWORD=your_replication_password
   ```

5. Start the primary PostgreSQL container:
   ```
   cd primary_server
   docker-compose up -d
   ```

6. Create the replication user:
   ```
   docker exec -it postgres_primary psql -U ${POSTGRES_USER} -c "CREATE USER ${REPLICATION_USER} WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';"
   ```

### Secondary Server Setup

1. Copy the entire project directory to the secondary server.

2. Update the `.env` file on the secondary server with the correct PRIMARY_IP:
   ```
   PRIMARY_IP=<primary_server_ip>
   ```

3. Create the initialization script:
   ```
   nano init-replication.sh
   ```
   Add the content for the initialization script (refer to the previous responses for the full script).

4. Make the script executable:
   ```
   chmod +x init-replication.sh
   ```

5. Run the initialization script:
   ```
   ./init-replication.sh
   ```

## Usage

After setup, you can access the API endpoints:

- List all tables: `http://secondary_server_ip:8000/tables`
- Get data from a specific table: `http://secondary_server_ip:8000/table/{table_name}`

## Troubleshooting

If you encounter issues:

1. Check the logs:
   ```
   docker-compose -f secondary_server/docker-compose.yml logs
   ```

2. Ensure all environment variables are correctly set.

3. Verify that the primary server is accessible from the secondary server.

4. Check the PostgreSQL configuration files for any misconfigurations.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support the Developer

If you find this project helpful, consider supporting the developer:

- $erg Address: 9gUDVVx75KyZ783YLECKngb1wy8KVwEfk3byjdfjUyDVAELAPUN

Your support is greatly appreciated and helps maintain and improve this project!