# routes/sigscore/queries.py

LOYAL_MINERS_QUERY = """
    WITH hourly_activity AS (
        SELECT 
            miner,
            date_trunc('hour', created) AS hour,
            DATE(created) AS day,
            AVG(hashrate) AS avg_hashrate
        FROM minerstats
        WHERE created >= $1 AND created <= $2
        GROUP BY miner, date_trunc('hour', created), DATE(created)
        HAVING AVG(hashrate) > 0
    ),
    daily_activity AS (
        SELECT 
            miner,
            day,
            COUNT(DISTINCT hour) AS active_hours,
            AVG(avg_hashrate) AS daily_avg_hashrate
        FROM hourly_activity
        GROUP BY miner, day
    ),
    qualified_miners AS (
        SELECT 
            miner,
            COUNT(DISTINCT day) AS days_active,
            AVG(daily_avg_hashrate) AS weekly_avg_hashrate
        FROM daily_activity
        WHERE active_hours >= 12
        GROUP BY miner
        HAVING COUNT(DISTINCT day) >= 4
    )
    SELECT 
        qm.miner,
        qm.days_active,
        qm.weekly_avg_hashrate,
        COALESCE(b.amount, 0) as current_balance,
        MAX(p.created) as last_payment_date
    FROM qualified_miners qm
    LEFT JOIN balances b ON qm.miner = b.address
    LEFT JOIN payments p ON qm.miner = p.address
    GROUP BY qm.miner, qm.days_active, qm.weekly_avg_hashrate, b.amount
    ORDER BY qm.weekly_avg_hashrate DESC
    LIMIT $3
"""

MINER_DETAILS_QUERIES = {
    "pool_stats": """
        SELECT networkdifficulty, networkhashrate 
        FROM poolstats 
        ORDER BY created DESC 
        LIMIT 1
    """,
    "last_block": """
        SELECT created, blockheight 
        FROM blocks 
        WHERE miner = $1 
        ORDER BY created DESC 
        LIMIT 1
    """,
    "balance": """
        SELECT COALESCE(amount, 0) as balance
        FROM balances
        WHERE address = $1
        ORDER BY created DESC
        LIMIT 1
    """,
    "payment": """
        SELECT amount, created as last_payment_date, transactionconfirmationdata 
        FROM payments 
        WHERE address = $1 
        ORDER BY created DESC 
        LIMIT 1
    """,
    "total_paid": """
        SELECT COALESCE(SUM(amount), 0) as total_paid 
        FROM payments 
        WHERE address = $1
    """,
    "paid_today": """
        SELECT COALESCE(SUM(amount), 0) as paid_today 
        FROM payments 
        WHERE address = $1 
        AND DATE(created) = $2
    """,
    "workers": """
        WITH latest_worker_stats AS (
            SELECT 
                worker,
                hashrate,
                sharespersecond,
                ROW_NUMBER() OVER (PARTITION BY worker ORDER BY created DESC) as rn
            FROM minerstats
            WHERE miner = $1
        )
        SELECT 
            worker, 
            hashrate, 
            sharespersecond,
            SUM(hashrate) OVER () as total_hashrate,
            SUM(sharespersecond) OVER () as total_sharespersecond
        FROM latest_worker_stats
        WHERE rn = 1
        ORDER BY hashrate DESC
    """
}

ALL_MINERS_QUERY = """
    WITH latest_timestamp AS (
        SELECT MAX(created) as max_created
        FROM minerstats
    ),
    latest_stats AS (
        SELECT 
            miner,
            SUM(hashrate) as total_hashrate,
            SUM(sharespersecond) as total_sharespersecond
        FROM minerstats
        WHERE created = (SELECT max_created FROM latest_timestamp)
        GROUP BY miner
        HAVING SUM(hashrate) > 0
    ),
    latest_blocks AS (
        SELECT DISTINCT ON (miner) miner, created as last_block_found
        FROM blocks
        ORDER BY miner, created DESC
    )
    SELECT 
        ls.miner, 
        ls.total_hashrate, 
        ls.total_sharespersecond,
        (SELECT max_created FROM latest_timestamp) as last_stat_time,
        lb.last_block_found
    FROM latest_stats ls
    LEFT JOIN latest_blocks lb ON ls.miner = lb.miner
    ORDER BY ls.total_hashrate DESC NULLS LAST
    LIMIT $1 OFFSET $2
"""

TOP_MINERS_QUERY = """
    SELECT miner, hashrate
    FROM (
        SELECT DISTINCT ON (miner) miner, hashrate
        FROM minerstats
        ORDER BY miner, created DESC
    ) as latest_stats
    ORDER BY hashrate DESC
    LIMIT 20
"""

WORKER_HISTORY_QUERY = """
    WITH worker_stats AS (
        SELECT 
            worker,
            date_trunc('hour', created) as hour,
            AVG(hashrate) as hashrate,
            AVG(sharespersecond) as shares
        FROM minerstats
        WHERE miner = $1
        AND created >= NOW() - make_interval(days => $2)
        GROUP BY worker, date_trunc('hour', created)
    )
    SELECT
        worker,
        hour as timestamp,
        hashrate,
        shares,
        LAG(hashrate) OVER (PARTITION BY worker ORDER BY hour) as prev_hashrate
    FROM worker_stats
    ORDER BY hour, worker
"""