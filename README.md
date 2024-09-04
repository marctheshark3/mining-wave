# Mining Wave

Mining Wave is a containerized PostgreSQL replication setup designed for mining pool operations. It consists of a primary server and a secondary (replica) server with an integrated API service for interacting with the Ergo blockchain.

## Project Structure

```
mining-wave/
├── primary_server/
│   ├── docker-compose.yml
│   └── conf/
│       ├── postgresql.conf
│       └── pg_hba.conf
├── secondary_server/
│   ├── docker-compose.yml
│   ├── conf/
│   │   ├── postgresql.conf
│   │   └── recovery.conf
│   └── api_service/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── main.py
└── scripts/
    ├── init_primary.sh
    ├── init_secondary.sh
    └── query_db.sh
```

## Prerequisites

- Docker and Docker Compose installed on both primary and secondary servers
- Git installed on both servers
- Network connectivity between the primary and secondary servers

## Setup Instructions

### On the Primary Server

1. Clone the repository:
   ```
   git clone https://github.com/marctheshark3/mining-wave.git
   cd mining-wave
   ```

2. Initialize the primary server:
   ```
   cd scripts
   chmod +x init_primary.sh
   ./init_primary.sh
   ```

### On the Secondary Server

1. Clone the repository:
   ```
   git clone https://github.com/marctheshark3/mining-wave.git
   cd mining-wave
   ```

2. Initialize the secondary server:
   ```
   cd scripts
   chmod +x init_secondary.sh
   export PRIMARY_IP=<ip_of_primary_server>
   ./init_secondary.sh
   ```

   Replace `<ip_of_primary_server>` with the actual IP address of your primary server.

## Usage

### Starting the Services

- On the primary server:
  ```
  cd mining-wave/primary_server
  docker-compose up -d
  ```

- On the secondary server:
  ```
  cd mining-wave/secondary_server
  docker-compose up -d
  ```

### Stopping the Services

- On either server:
  ```
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

The primary server runs a PostgreSQL instance configured for replication.

### Secondary Server

The secondary server runs:
1. A PostgreSQL instance configured as a replica of the primary server.
2. An API service that interacts with the Ergo blockchain and updates the database.

### API Service

The API service runs on the secondary server and performs the following tasks:
- Fetches new block data from the Ergo blockchain every 10 minutes.
- Updates the `blocks` table in the PostgreSQL database with the fetched data.

## Configuration

- Database credentials and other configurations are set in the `docker-compose.yml` files.
- PostgreSQL configurations are in the `conf` directories.
- The API service configuration is in `secondary_server/api_service/main.py`.

## Troubleshooting

If you encounter issues:

1. Check Docker logs:
   ```
   docker-compose logs
   ```

2. Ensure the PRIMARY_IP is correctly set on the secondary server.

3. Verify network connectivity between the primary and secondary servers.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
