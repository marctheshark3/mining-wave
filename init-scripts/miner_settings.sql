CREATE TABLE IF NOT EXISTS miner_payouts (
    id SERIAL PRIMARY KEY,
    miner_address VARCHAR(255) NOT NULL UNIQUE,
    minimum_payout_threshold DECIMAL(10, 2) NOT NULL,
    swapping BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
