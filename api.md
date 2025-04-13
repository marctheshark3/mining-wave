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

### Pool Blocks
- **Endpoint**: `/miningcore/blocks`
- **Method**: GET
- **Description**: Get all blocks found by the pool
- **Parameters**:
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of blocks found by the pool, including demurrage information
- **Cache**: 30 seconds

### Miner Blocks
- **Endpoint**: `/miningcore/blocks/{address}`
- **Method**: GET
- **Description**: Get blocks found by a specific miner
- **Parameters**:
  - `address`: Miner's address
  - `limit`: Maximum number of results (default: 100, max: 1000)
- **Response**: List of blocks found by the miner, including demurrage information:
  - `hasDemurrage`: Whether demurrage was received for this block
  - `demurrageAmount`: The amount of demurrage received (if any)
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

## Demurrage Routes

### Demurrage Wallet
- **Endpoint**: `/demurrage/wallet`
- **Method**: GET
- **Description**: Get detailed statistics and transactions for the demurrage wallet. Uses a comprehensive calculation method by default to provide accurate period-based statistics.
- **Parameters**:
  - `limit`: Maximum number of recent transactions to return in `recentIncoming` and `recentOutgoing` lists (default: 10, max: 50).
  - `use_comprehensive`: Boolean flag to enable/disable the comprehensive calculation method (default: true). If false, uses a faster but less accurate method based only on recent transactions.
- **Response**: Comprehensive demurrage wallet statistics including:
  ```json
  {
    "balance": 123.4567, // Current wallet balance in ERG
    "recentIncoming": [ // List of recent incoming transactions (verified demurrage)
      {
        "txId": "...",
        "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "amount": 0.625,
        "blockHeight": 1234567,
        "isVerifiedDemurrage": true 
      } 
      // ... (up to limit)
    ],
    "recentOutgoing": [ // List of recent outgoing transactions (distributions)
      {
        "txId": "...",
        "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "totalAmount": 50.1234,
        "recipientCount": 15
      }
      // ... (up to limit)
    ],
    "totalCollected": 518.8235, // Total verified demurrage collected (all time)
    "totalDistributed": 495.1111, // Total ERG distributed (all time)
    "distributed7d": 60.0,       // Total ERG distributed in the last 7 days
    "distributed30d": 250.0,     // Total ERG distributed in the last 30 days
    "collected24h": 6.3688,      // Total verified demurrage collected in the last 24 hours
    "collected7d": 63.2554,     // Total verified demurrage collected in the last 7 days
    "collected30d": 276.0499,    // Total verified demurrage collected in the last 30 days
    "lastDistribution": {        // Details of the last distribution transaction
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
      "amount": 50.1234,
      "recipientCount": 15
    },
    "nextEstimatedDistribution": { // Estimated details for the next distribution
      "estimatedTimestamp": "YYYY-MM-DDTHH:MM:SSZ",
      "estimatedAmount": 6.5 // Estimated based on recent collection rate
    }
  }
  ```
- **Cache**: 1800 seconds (30 minutes)

### Demurrage Statistics
- **Endpoint**: `/demurrage/stats`
- **Method**: GET
- **Description**: Get comprehensive statistics about demurrage across different time periods, including estimated earnings based on hashrate. Relies on `/demurrage/wallet` for collection data.
- **Response**: Detailed demurrage statistics including:
  ```json
  {
    "periods": {
      "24h": {
        "totalDemurrage": 6.3688,
        "avgPerBlock": 0.045, // Average demurrage per block found by pool in period
        "blocksWithDemurrage": 5, // Count of pool blocks confirmed to have demurrage
        "totalBlocks": 10, // Total blocks found by pool in period
        "demurragePercentage": 50.0 // Percentage of pool blocks with demurrage
      },
      "7d": { ... }, // Similar structure for 7 days
      "30d": { ... }, // Similar structure for 30 days
      "allTime": { ... } // Similar structure for all time
    },
    "estimatedEarnings": { // Estimated earnings based on miner hashrate proportion
      "1GHs": {"24h": 0.06, "7d": 0.63, "30d": 2.76},
      "5GHs": { ... },
      "10GHs": { ... },
      "50GHs": { ... }
    },
    "currentPoolHashrate": 110.5, // Current pool hashrate in GH/s
    "lastUpdated": "YYYY-MM-DDTHH:MM:SS.ffffffZ", // Timestamp of when the data was generated
    "apiStatus": { // Status of the data processing
      "processedBlocks": 5000,
      "errorCount": 0,
      "completionPercentage": 100.0
    }
  }
  ```
- **Cache**: 1800 seconds (30 minutes)

### Miner Demurrage Earnings
- **Endpoint**: `/demurrage/miner/{address}`
- **Method**: GET
- **Description**: Get demurrage earnings specific to a miner address, calculated based on their historical pool share.
- **Parameters**:
  - `address`: The miner's Ergo address (Path parameter)
- **Response**: Detailed information about the miner's demurrage earnings including:
  ```json
  {
    "minerAddress": "...",
    "currentHashrate": 5.5e9, // Miner's current reported hashrate
    "currentPoolShare": 5.0, // Miner's current share of the pool hashrate (%)
    "earnings": { // Estimated earnings based on average share during period
      "24h": {"amount": 0.3184, "shareOfTotal": 5.0}, 
      "7d": {"amount": 3.1627, "shareOfTotal": 4.8},
      "30d": {"amount": 13.8025, "shareOfTotal": 4.9},
      "allTime": {"amount": 25.9411, "shareOfTotal": 4.7}
    },
    "recentPayments": [ // Payments received directly from the demurrage wallet
      {
        "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
        "amount": 2.5,
        "txId": "..."
      }
      // ... (up to 10)
    ],
    "projectedNextPayment": { // Estimated next payment based on pool distribution schedule
      "estimatedTimestamp": "YYYY-MM-DDTHH:MM:SSZ",
      "estimatedAmount": 0.325 
    },
    "apiStatus": { // Status of the block processing for demurrage calculation
      "processedBlocks": 4998,
      "errorCount": 2,
      "completionPercentage": 99.9
    }
  }
  ```
- **Cache**: 1800 seconds (30 minutes)

### Demurrage Health
- **Endpoint**: `/demurrage/health`
- **Method**: GET
- **Description**: Test blockchain API connectivity (Explorer and Local Node) and health for demurrage monitoring.
- **Response**: Health status information including:
  ```json
  {
    "explorerApi": {
      "status": "ok", // "ok" or "error"
      "height": 1234567 
    },
    "nodeApi": {
      "status": "ok",
      "height": 1234567,
      "headersHeight": 1234568,
      "isConnected": true
    },
    "blockRetrieval": {
      "status": "ok",
      "blockId": "...",
      "height": 1000000
    },
    "overall": "ok" // "ok" or "degraded"
  }
  ```
- **Cache**: 60 seconds

### Demurrage Debug
- **Endpoint**: `/demurrage/debug`
- **Method**: GET
- **Description**: Debug endpoint for demurrage calculation. Retrieves raw block data from `/miningcore/blocks` and shows detailed counts and percentages of blocks with demurrage for different periods.
- **Response**: Debugging information about demurrage occurrence in pool blocks:
  ```json
  {
    "periods": {
      "24h": {
        "totalBlocks": 10,
        "blocksWithDemurrage": 5,
        "blocksWithoutDemurrage": 5,
        "demurragePercentage": 50.0,
        "sampleBlocksWithDemurrage": [ { ... block data ... } ], // Max 3 samples
        "sampleBlocksWithoutDemurrage": [ { ... block data ... } ] // Max 3 samples
      },
      "7d": { ... }, // Similar structure for 7 days
      "30d": { ... }, // Similar structure for 30 days
      "allTime": { ... } // Similar structure for all time
    },
    "totalBlocksInApi": 500 // Total blocks returned by /miningcore/blocks
  }
  ```
- **Cache**: No cache

### Demurrage Epoch Stats
- **Endpoint**: `/demurrage/epochs`
- **Method**: GET
- **Description**: Get epoch-based demurrage statistics, showing verified demurrage rewards collected in each recent epoch (up to the last 10).
- **Response**: Demurrage statistics grouped by Ergo epoch:
  ```json
  {
    "currentEpoch": 1480,
    "currentHeight": 1516544,
    "blocksInCurrentEpoch": 512,
    "blocksLeftInEpoch": 512,
    "currentEpochStartBlock": 1516032,
    "totalEpochs": 10, // Number of epochs included in the 'epochs' list
    "totalDemurrage": 150.5678, // Total verified demurrage across listed epochs
    "averageDemurragePerEpoch": 15.0567, // Average across listed epochs
    "projectedDemurrageForCurrentEpoch": 16.5, // Projection based on current rate
    "epochs": [
      {
        "epoch": 1471,
        "startBlock": 1507328,
        "endBlock": 1508351,
        "demurrageAmount": 14.2, // Verified demurrage collected
        "blockCountWithDemurrage": 60, // Pool blocks in epoch with demurrage
        "totalBlocksInEpochRange": 1024, // Total blocks in this epoch
        "isCurrentEpoch": false
      }
      // ... (for up to 10 recent epochs)
    ]
  }
  ```
- **Cache**: 1800 seconds (30 minutes)

### Demurrage Blocks
- **Endpoint**: `/demurrage/blocks`
- **Method**: GET
- **Description**: Retrieves demurrage collections (ERG and tokens) grouped by block height. Fetches incoming transactions to the demurrage wallet. Excludes distributions (outgoing transactions).
- **Parameters**:
  - `limit`: Maximum number of recent blocks with demurrage to return (default: 100, max: 1000).
- **Response**: List of blocks containing demurrage, sorted by height descending:
  ```json
  [
    {
      "blockHeight": 1516540,
      "totalErg": 0.625, // Total ERG collected in this block
      "tokens": { // Dictionary of token IDs and amounts collected
        "tokenId1...": 1000,
        "tokenId2...": 50
      }
    },
    {
      "blockHeight": 1516535,
      "totalErg": 0.675,
      "tokens": {}
    }
    // ... (up to limit)
  ]
  ```
- **Cache**: 1800 seconds (30 minutes)

## Demurrage Monitoring

(Section removed as monitoring is now internal and reflected in the API responses) 