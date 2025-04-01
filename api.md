# MiningWave API Documentation

This document provides information about all available API endpoints in the MiningWave API.

## Base Endpoints

### Health Check
- **Endpoint**: `/health`
- **Method**: GET
- **Description**: Health check endpoint for the API
- **Response**: Health status and database pool statistics

### Root Endpoint
- **Endpoint**: `/`
- **Method**: GET
- **Description**: Root endpoint returning API information
- **Response**: Basic API information including version and status

### Routes
- **Endpoint**: `/routes`
- **Method**: GET
- **Description**: List all available routes in the API
- **Response**: List of all routes with their paths and methods

## General Routes

### General Root
- **Endpoint**: `/`
- **Method**: GET
- **Description**: Welcome message for the Mining Core API
- **Rate Limit**: 10 requests per 60 seconds

### Tables List
- **Endpoint**: `/tables`
- **Method**: GET
- **Description**: List all available database tables
- **Response**: Array of table names

### Database Connection Test
- **Endpoint**: `/test_db_connection`
- **Method**: GET
- **Description**: Test database connectivity
- **Response**: Connection status

## MiningCore Routes

### Pool Statistics
- **Endpoint**: `/miningcore/poolstats`
- **Method**: GET
- **Description**: Get current pool statistics
- **Response**: Pool stats including hashrate, connected miners, and network data
- **Cache**: 60 seconds

### Miner Blocks
- **Endpoint**: `/miningcore/blocks/{address}`
- **Method**: GET
- **Description**: Get blocks found by a specific miner
- **Parameters**:
  - `address`: Miner's address
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of blocks found by the miner
- **Cache**: 30 seconds

### Miner Payments
- **Endpoint**: `/miningcore/payments/{address}`
- **Method**: GET
- **Description**: Get payment history for a specific miner
- **Parameters**:
  - `address`: Miner's address
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of payments to the miner
- **Cache**: 60 seconds

### Current Shares
- **Endpoint**: `/miningcore/shares`
- **Method**: GET
- **Description**: Get current share counts for all miners
- **Response**: List of shares by miner
- **Cache**: 30 seconds

### Table Data
- **Endpoint**: `/miningcore/{table_name}`
- **Method**: GET
- **Description**: Get all data from a specific table
- **Parameters**:
  - `table_name`: Name of the table
- **Response**: All rows from the specified table
- **Cache**: 60 seconds

### Filtered Table Data
- **Endpoint**: `/miningcore/{table_name}/{address}`
- **Method**: GET
- **Description**: Get filtered data from a specific table for a given address
- **Parameters**:
  - `table_name`: Name of the table
  - `address`: Miner's address
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: Filtered rows from the specified table
- **Cache**: 60 seconds

## SigScore Routes

### Average Block Participation
- **Endpoint**: `/sigscore/miners/average-participation`
- **Method**: GET/POST
- **Description**: Calculate average participation across multiple blocks
- **Parameters**:
  - **GET**: `blocks`: Comma-separated list of block heights
  - **POST**: JSON body with `block_heights` array
- **Response**: Average participation statistics across blocks
- **Cache**: 300 seconds

### Block Participation
- **Endpoint**: `/sigscore/miners/participation/{block_height}`
- **Method**: GET
- **Description**: Get miner participation percentages for a specific block
- **Parameters**:
  - `block_height`: Block height or 'latest'/'recent'
  - `days`: Number of days to look back (default: 7, max: 30)
- **Response**: Block participation data by miner
- **Cache**: 300 seconds

### Weekly Loyal Miners
- **Endpoint**: `/sigscore/miners/bonus`
- **Method**: GET
- **Description**: Get miners who have been active for at least 4 out of the last 7 days
- **Parameters**:
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of loyal miners with activity statistics
- **Cache**: 300 seconds

### Miner Bonus Eligibility
- **Endpoint**: `/sigscore/miners/{address}/bonus-eligibility`
- **Method**: GET
- **Description**: Check why a miner might or might not be eligible for the bonus
- **Parameters**:
  - `address`: Miner's address
- **Response**: Eligibility details and daily breakdown

### Weekly Miner Activity
- **Endpoint**: `/sigscore/miners/activity`
- **Method**: GET
- **Description**: Get activity statistics for all miners over the last 7 days
- **Parameters**:
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of miners with activity statistics
- **Cache**: 300 seconds

### Pool History
- **Endpoint**: `/sigscore/history`
- **Method**: GET
- **Description**: Get pool hashrate history for the last 5 days
- **Response**: Hourly hashrate data
- **Cache**: 300 seconds

### All Miners
- **Endpoint**: `/sigscore/miners`
- **Method**: GET
- **Description**: Get list of all active miners with their current stats
- **Parameters**:
  - `limit`: Maximum number of results (default: 100, max: 1000)
  - `offset`: Offset for pagination (default: 0)
- **Response**: List of miners with current statistics
- **Cache**: 60 seconds

### Top Miners
- **Endpoint**: `/sigscore/miners/top`
- **Method**: GET
- **Description**: Get top 20 miners by hashrate
- **Response**: List of top miners with their hashrates
- **Cache**: 60 seconds

### Miner Details
- **Endpoint**: `/sigscore/miners/{address}`
- **Method**: GET
- **Description**: Get detailed statistics for a specific miner
- **Parameters**:
  - `address`: Miner's address
- **Response**: Comprehensive miner details including balance, hashrate, and payment history
- **Cache**: 30 seconds

### Miner Worker History
- **Endpoint**: `/sigscore/miners/{address}/workers`
- **Method**: GET
- **Description**: Get worker history for a specific miner
- **Parameters**:
  - `address`: Miner's address
  - `days`: Number of days of history (default: 5, max: 30)
- **Response**: Worker history data
- **Cache**: 60 seconds

### All Miner Settings
- **Endpoint**: `/sigscore/miner_setting`
- **Method**: GET
- **Description**: Get settings for all miners
- **Parameters**:
  - `limit`: Maximum number of results (default: 100, max: 1000)
  - `offset`: Offset for pagination (default: 0)
- **Response**: List of miner settings
- **Cache**: 300 seconds

### Specific Miner Setting
- **Endpoint**: `/sigscore/miner_setting/{miner_address}`
- **Method**: GET
- **Description**: Get settings for a specific miner
- **Parameters**:
  - `miner_address`: Miner's address
- **Response**: Miner's settings
- **Cache**: 300 seconds 