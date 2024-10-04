# MiningWave API

This project provides a FastAPI-based API for retrieving mining-related data from a PostgreSQL database.

## Setup and Deployment

### Prerequisites

- Docker and Docker Compose installed on your system
- PostgreSQL database with mining data

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
```

### Running the API

1. Build and start the Docker container:

```bash
docker-compose up -d
```

2. The API will be available at `http://localhost:8000`

### Stopping the API

To stop the Docker container:

```bash
docker-compose down
```

## API Endpoints

### Root

- **GET /** 
  - Returns a welcome message
  - Response: `{"message": "Welcome to the Mining Core API"}`

### Database Information

- **GET /tables**
  - Lists all tables in the connected database
  - Response: `{"tables": ["table1", "table2", ...]}`

- **GET /test_db_connection**
  - Tests the database connection
  - Response: `{"status": "Database connection successful", "result": 1}`

### Mining Data

- **GET /miningcore/{table_name}**
  - Retrieves all data from the specified table
  - Response: Array of objects representing table rows

- **GET /miningcore/{table_name}/{address}**
  - Retrieves filtered data from the specified table for a given address
  - Query Parameters:
    - `limit`: Number of rows to return (default: 100, max: 1000)
  - Response: Array of objects representing filtered table rows

### Pool Statistics

- **GET /sigscore/history**
  - Retrieves pool hashrate history for the last 5 days
  - Response: Array of objects with timestamps and total hashrates

- **GET /sigscore/miners**
  - Retrieves information about all miners
  - Query Parameters:
    - `limit`: Number of miners to return (default: 100, max: 1000)
    - `offset`: Number of miners to skip (default: 0)
  - Response: Array of objects with miner details

- **GET /sigscore/miners/top**
  - Retrieves the top 20 miners by hashrate
  - Response: Array of objects with miner addresses and hashrates

- **GET /sigscore/miners/{address}**
  - Retrieves detailed information about a specific miner
  - Response: Object with miner statistics, including current hashrate, balance, and worker details

- **GET /sigscore/miners/{address}/workers**
  - Retrieves 24-hour hourly data for a miner's workers
  - Response: Object with worker names as keys and arrays of hourly data as values

### Miner Settings

- **GET /sigscore/miner_setting**
  - Retrieves settings for all miners
  - Query Parameters:
    - `limit`: Number of settings to return (default: 100, max: 1000)
    - `offset`: Number of settings to skip (default: 0)
  - Response: Array of objects with miner settings

- **GET /sigscore/miner_setting/{miner_address}**
  - Retrieves settings for a specific miner
  - Response: Object with miner address, minimum payout threshold, swapping status, and creation date

## Error Handling

The API returns appropriate HTTP status codes and error messages for invalid requests or server errors.

## Logging

The API logs important events and errors for monitoring and debugging purposes.

## Security Note

Ensure that your `.env` file and database credentials are kept secure and not exposed publicly.
