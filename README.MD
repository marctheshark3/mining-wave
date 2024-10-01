
## API Endpoints

### 1. Root Endpoint
- **Path:** `/`
- **Method:** GET
- **Description:** Returns a welcome message to the Mining Core API.

### 2. List Tables
- **Path:** `/tables`
- **Method:** GET
- **Description:** Returns a list of all table names in the connected database.

### 3. Test Database Connection
- **Path:** `/test_db_connection`
- **Method:** GET
- **Description:** Confirms successful database connection.

### 4. Get Table Data
- **Path:** `/miningcore/{table_name}`
- **Method:** GET
- **Description:** Returns all rows from the specified table.

### 5. Get Filtered Table Data
- **Path:** `/miningcore/{table_name}/{address}`
- **Method:** GET
- **Parameters:** 
  - `limit` (query parameter, optional): Number of rows to return (default: 100, max: 1000)
- **Description:** Returns filtered rows from the specified table for the given address.

### 6. Get Pool History
- **Path:** `/sigscore/miners/history`
- **Method:** GET
- **Description:** Returns hourly total hashrate for the pool over the last 5 days.

### 7. Get All Miners
- **Path:** `/sigscore/miners`
- **Method:** GET
- **Parameters:**
  - `limit` (query parameter, optional): Number of miners to return (default: 100, max: 1000)
  - `offset` (query parameter, optional): Number of miners to skip (default: 0)
- **Description:** Returns a list of miners with their address, hashrate, and last block found timestamp.

### 8. Get Top Miners
- **Path:** `/sigscore/miners/top`
- **Method:** GET
- **Description:** Returns the top 20 miners by hashrate.

### 9. Get Miner Details
- **Path:** `/sigscore/miners/{address}`
- **Method:** GET
- **Description:** Returns detailed information about a specific miner, including current hashrate, shares per second, worker count, total hashrate, last block found, balance, and last payment.

### 10. Get Miner Workers
- **Path:** `/sigscore/miners/{address}/workers`
- **Method:** GET
- **Description:** Returns 24-hour hourly data for all workers of a specific miner, including hashrate and shares per second.

## Error Handling

The API uses standard HTTP status codes for error responses:
- 404: Resource not found
- 500: Internal server error

Detailed error messages are provided in the response body.

## Logging

The application uses Python's built-in logging module. Logs are output to the console with the logging level set to INFO.

## Database

The application uses PostgreSQL as its database. Ensure you have a PostgreSQL instance running and accessible with the credentials provided in your environment variables.

## Security

- The API uses parameterized queries to prevent SQL injection attacks.
- Sensitive information like database credentials are stored in environment variables.

## Performance Considerations

- Some queries use Common Table Expressions (CTEs) and window functions, which may be computationally expensive for very large datasets.
- Consider implementing proper indexing on frequently queried columns (e.g., miner, created) to improve query performance.
- For high-traffic scenarios, consider implementing caching mechanisms for frequently accessed data.

## Contributing

Contributions to this project are welcome. Please ensure you follow the existing code style and include appropriate tests for new features.

## License

[Include your license information here]