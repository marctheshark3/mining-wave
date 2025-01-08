# MiningWave API
FastAPI-based microservice for crypto mining pool metrics and management. Features real-time monitoring, worker statistics, and rewards distribution.

## API Documentation
The API provides comprehensive, interactive documentation:
- **Swagger UI**: `http://localhost:8000/docs`
  - Interactive API testing interface
  - Try out API calls directly in your browser
  - View request/response schemas
  - Explore available parameters
- **ReDoc**: `http://localhost:8000/redoc`
  - Alternative documentation format
  - Clean, organized interface
  - Printer-friendly documentation

All API endpoints are automatically documented with:
- Detailed request/response schemas
- Query parameters and validation rules
- Example requests and responses
- Authentication requirements
- Rate limiting information

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

## Core Features
- Real-time performance monitoring
- Worker-level statistics tracking
- Payment and balance management
- Redis-based caching with custom encoding
- Rate limiting protection
- Comprehensive error handling
- Structured logging

## Key Endpoints Overview
For detailed endpoint documentation, parameters, and response schemas, please refer to the Swagger UI (`/docs`) or ReDoc (`/redoc`) interface.

### Core Operations
- Health and connectivity checks
- Database table management
- System status monitoring

### Pool Statistics
- Current pool metrics
- Network statistics
- Block information
- Effort calculations

### Sigscore System
- Pool hashrate history
- Miner rankings
- Loyalty rewards tracking
- Performance analytics

### Miner Management
- Individual miner statistics
- Worker performance metrics
- Payment settings
- Balance tracking

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
- Effort calculation debugging

## Production Notes
- Secure your `.env` file
- Adjust rate limits for production load
- Configure appropriate CORS settings
- Monitor Redis memory usage
- Set up proper database backups

## License
This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.
