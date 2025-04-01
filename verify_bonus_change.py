import asyncio
import asyncpg
import datetime

async def verify_bonus_change():
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=7)
    limit = 100
    
    # Original query with 4-day requirement
    original_query = '''
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
    '''
    
    # Modified query with 3-day requirement
    modified_query = '''
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
        HAVING COUNT(DISTINCT day) >= 3
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
    '''
    
    try:
        conn = await asyncpg.connect(
            host='***REMOVED***',
            port=5432,
            user='miningcore',
            password='this_IS_thesigmining',
            database='miningcore'
        )
        
        print("Connected to database. Running comparison queries...")
        
        # Execute the original query (4-day requirement)
        original_rows = await conn.fetch(original_query, start_time, end_time, limit)
        print(f'Original criteria (4+ days): Found {len(original_rows)} loyal miners')
        
        # Execute the modified query (3-day requirement)
        modified_rows = await conn.fetch(modified_query, start_time, end_time, limit)
        print(f'Modified criteria (3+ days): Found {len(modified_rows)} loyal miners')
        
        if len(modified_rows) > 0:
            print("\nMiners qualifying with the new criteria:")
            for i, row in enumerate(modified_rows):
                print(f"{i+1}. Miner: {row['miner']}, Days active: {row['days_active']}, Avg hashrate: {row['weekly_avg_hashrate']}")
                
            # Get the distribution of days active
            days_active_counts = {}
            for row in modified_rows:
                days = row['days_active']
                if days not in days_active_counts:
                    days_active_counts[days] = 0
                days_active_counts[days] += 1
                
            print("\nDistribution of days active:")
            for days, count in sorted(days_active_counts.items()):
                print(f"  {days} days: {count} miners")
        else:
            print("\nNo miners qualify even with the new criteria. Further investigation needed.")
            
            # Check miners with 2 qualifying days
            two_day_query = '''
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
                HAVING COUNT(DISTINCT day) >= 2
            )
            SELECT 
                qm.miner,
                qm.days_active,
                qm.weekly_avg_hashrate
            FROM qualified_miners qm
            ORDER BY qm.days_active DESC, qm.weekly_avg_hashrate DESC
            LIMIT 10
            '''
            
            two_day_rows = await conn.fetch(two_day_query, start_time, end_time, 10)
            print(f'\nFound {len(two_day_rows)} miners with at least 2 qualifying days:')
            for row in two_day_rows:
                print(f"  Miner: {row['miner']}, Days active: {row['days_active']}, Avg hashrate: {row['weekly_avg_hashrate']}")
        
        await conn.close()
        
    except Exception as e:
        print(f'Error executing comparison queries: {str(e)}')

if __name__ == "__main__":
    asyncio.run(verify_bonus_change()) 