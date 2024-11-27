# MiningWave API

FastAPI-based microservice for crypto mining pool metrics and management. Features real-time monitoring, worker statistics, and rewards distribution.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- PostgreSQL database instance
- Redis (automatically handled by Docker Compose)

### Configuration
Create a `.env` file:
```env
DB_NAME=miningcore
DB_USER=miningcore
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=5432
REDIS_URL=redis://redis:6379
```

### Deployment
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Core Endpoints
- `GET /` - API health check
- `GET /tables` - List available database tables
- `GET /test_db_connection` - Test database connectivity

### Pool Statistics
- `GET /sigscore/history` - Pool hashrate history (5-day window)
- `GET /sigscore/miners` - Active miners list with stats
- `GET /sigscore/miners/top` - Top 20 miners by hashrate
- `GET /sigscore/miners/bonus` - Loyalty rewards tracking
  - Monitors miners active 4+ days/week
  - Minimum 12 hours daily activity
  - Tracks hashrate contributions

### Miner Management
- `GET /sigscore/miners/{address}` - Single miner detailed stats
  - Current hashrate
  - Balance and payments
  - Worker performance
- `GET /sigscore/miners/{address}/workers` - Worker-level metrics
- `GET /sigscore/miner_setting` - Pool-wide miner settings
- `GET /sigscore/miner_setting/{address}` - Individual miner settings

### Data Access
- `GET /miningcore/{table_name}` - Raw table data access
- `GET /miningcore/{table_name}/{address}` - Filtered table data
  - `limit`: Records per page (max: 1000)
  - `offset`: Pagination offset

## Features

- Real-time performance monitoring
- Worker-level statistics tracking
- Payment and balance management
- Redis-based caching
- Rate limiting protection
- Comprehensive error handling
- Structured logging

## Technical Stack

- **FastAPI**: Modern async web framework
- **PostgreSQL**: Primary data store
- **Redis**: Caching and rate limiting
- **Docker**: Containerization and orchestration
- **Pydantic**: Data validation
- **AsyncPG**: Async database operations

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn api:app --reload

# Access API documentation
http://localhost:8000/docs
```

## Security

- Environment variables for sensitive data
- Rate limiting on all endpoints
- CORS protection configured
- Connection pooling for database
- Cached responses for high-traffic endpoints

## Monitoring

The API includes comprehensive logging:
- Performance metrics
- Error tracking
- Access patterns
- System health status

## Production Notes

- Secure your `.env` file
- Adjust rate limits for production load
- Configure appropriate CORS settings
- Monitor Redis memory usage
- Set up proper database backups

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.