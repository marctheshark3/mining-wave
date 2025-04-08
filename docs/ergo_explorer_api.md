# Ergo Explorer API Reference

This document provides a reference for the key Ergo Explorer API endpoints used in our application. The official API documentation is available at [https://api.ergoplatform.com/api/v1/docs/](https://api.ergoplatform.com/api/v1/docs/).

## Base URL

All API requests should be made to:

```
https://api.ergoplatform.com/api/v1
```

## Block Endpoints

### Get Block by Height

Retrieves a block at the specified height.

```
GET /blocks?height={height}
```

**Parameters:**
- `height`: The block height to retrieve

**Response:**
Returns a JSON object with an `items` array containing matching blocks.

**Example:**
```
GET /blocks?height=1000000
```

### Get Block Transactions

Retrieves all transactions in a block.

```
GET /blocks/{blockId}/transactions
```

**Parameters:**
- `blockId`: The block ID (hash)

**Response:**
Returns an array of transaction objects.

**Example:**
```
GET /blocks/b6a7d5d54f5995f7b028e3bfece7793f5e1dbffd6b88b2268cbdc04d07d9d35a/transactions
```

## Transaction Endpoints

### Get Transaction Details

Retrieves detailed information about a transaction.

```
GET /transactions/{transactionId}
```

**Parameters:**
- `transactionId`: The transaction ID (hash)

**Response:**
Returns detailed transaction information including inputs and outputs.

**Example:**
```
GET /transactions/9148408c04c2e38a6402a7950d6157730fa7d49e9ab3b9cadec481d7769918e9
```

## Address Endpoints

### Get Address Transactions

Retrieves transactions related to a specific address.

```
GET /addresses/{address}/transactions
```

**Parameters:**
- `address`: The Ergo blockchain address
- `limit` (optional): Maximum number of transactions to return (default: 20)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
Returns a JSON object with an `items` array containing transactions and metadata.

**Example:**
```
GET /addresses/9fE5o7913CKKe6wvNgM11vULjTuKiopPcvCaj7t2zcJWXM2gcLu/transactions?limit=10
```

### Get Address Balance

Retrieves the confirmed balance for an address.

```
GET /addresses/{address}/balance/confirmed
```

**Parameters:**
- `address`: The Ergo blockchain address

**Response:**
Returns a JSON object with the balance in nanoERGs.

**Example:**
```
GET /addresses/9fE5o7913CKKe6wvNgM11vULjTuKiopPcvCaj7t2zcJWXM2gcLu/balance/confirmed
```

## General Information

### Get Blockchain Info

Retrieves general information about the blockchain.

```
GET /info
```

**Response:**
Returns a JSON object with current blockchain information including height, difficulty, etc.

**Example:**
```
GET /info
```

## Error Handling

The API uses standard HTTP status codes to indicate success or failure:

- `200 OK`: The request was successful
- `400 Bad Request`: The request was invalid
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: An error occurred on the server

## Implementation Notes

1. Some API endpoints return data directly as an array, while others return a JSON object with an `items` array.

2. Block height endpoints (`/blocks?height={height}`) return an array of blocks matching that height. In most cases, there will be only one, but be prepared to handle multiple blocks.

3. Transaction values are provided in nanoERGs (1 ERG = 1,000,000,000 nanoERGs).

4. The API may have rate limiting in place. Implement retry logic with backoff for reliable operation. 