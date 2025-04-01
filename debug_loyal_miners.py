import asyncio
import asyncpg
import datetime

async def test_loyal_miners_query():
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=7)
    limit = 100
    
    query = '''
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
    
    try:
        conn = await asyncpg.connect(
            host='***REMOVED***',
            port=5432,
            user='miningcore',
            password='***REMOVED***',
            database='miningcore'
        )
        
        print("Connected to database. Running queries...")
        
        # Execute the query
        rows = await conn.fetch(query, start_time, end_time, limit)
        
        # Print the results
        print(f'Found {len(rows)} loyal miners')
        for row in rows[:5]:  # Print first 5 rows for brevity
            print(f'Miner: {row["miner"]}, Days active: {row["days_active"]}, Avg hashrate: {row["weekly_avg_hashrate"]}')
        
        if not rows:
            print("No loyal miners found. Diagnosing the issue...")
            
            # Check if we have data in the tables at all
            miner_count = await conn.fetchval('SELECT COUNT(*) FROM minerstats')
            balance_count = await conn.fetchval('SELECT COUNT(*) FROM balances')
            payment_count = await conn.fetchval('SELECT COUNT(*) FROM payments')
            
            print(f'Table counts: minerstats={miner_count}, balances={balance_count}, payments={payment_count}')
            
            # Check for recent data
            recent_miners = await conn.fetch(
                'SELECT COUNT(DISTINCT miner) FROM minerstats WHERE created >= $1',
                end_time - datetime.timedelta(days=7)
            )
            print(f'Recent distinct miners: {recent_miners[0][0]}')
            
            # Debug each CTE separately
            print("\nDebugging each CTE separately:")
            
            # Check hourly_activity CTE
            hourly_rows = await conn.fetch('''
                SELECT 
                    miner,
                    COUNT(DISTINCT date_trunc('hour', created)) as hour_count
                FROM minerstats
                WHERE created >= $1 AND created <= $2
                AND hashrate > 0
                GROUP BY miner
                ORDER BY hour_count DESC
                LIMIT 10
            ''', start_time, end_time)
            
            print(f"\nhourly_activity - Found {len(hourly_rows)} miners with hourly data")
            for row in hourly_rows[:5]:
                print(f"  Miner: {row['miner']}, Hours: {row['hour_count']}")
            
            # Check daily_activity CTE - Fixed the query
            daily_rows = await conn.fetch('''
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
                )
                SELECT 
                    miner,
                    COUNT(DISTINCT day) as active_days,
                    COUNT(DISTINCT hour) as total_hours
                FROM hourly_activity
                GROUP BY miner
                ORDER BY active_days DESC, total_hours DESC
                LIMIT 10
            ''', start_time, end_time)
            
            print(f"\ndaily_activity - Found {len(daily_rows)} miners with daily activity")
            for row in daily_rows[:5]:
                print(f"  Miner: {row['miner']}, Active days: {row['active_days']}, Total hours: {row['total_hours']}")
            
            # Check how many hours per day miners are active
            hours_per_day = await conn.fetch('''
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
                )
                SELECT 
                    miner,
                    day,
                    COUNT(DISTINCT hour) AS hours_active
                FROM hourly_activity
                GROUP BY miner, day
                HAVING COUNT(DISTINCT hour) >= 12
                ORDER BY miner, day
                LIMIT 20
            ''', start_time, end_time)
            
            print(f"\nMiners with at least 12 hours per day - Found {len(hours_per_day)} qualifying miner-days")
            if len(hours_per_day) > 0:
                last_miner = None
                miner_days = 0
                for row in hours_per_day:
                    if last_miner != row['miner']:
                        if last_miner:
                            print(f"  Miner {last_miner} has {miner_days} qualifying days")
                        last_miner = row['miner']
                        miner_days = 1
                    else:
                        miner_days += 1
                if last_miner:
                    print(f"  Miner {last_miner} has {miner_days} qualifying days")
            
            # Check if any miners have 4+ days with 12+ hours
            qualified = await conn.fetch('''
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
                        COUNT(DISTINCT hour) AS active_hours
                    FROM hourly_activity
                    GROUP BY miner, day
                )
                SELECT 
                    miner,
                    COUNT(*) as qualifying_days
                FROM daily_activity
                WHERE active_hours >= 12
                GROUP BY miner
                HAVING COUNT(*) >= 4
                ORDER BY qualifying_days DESC
                LIMIT 10
            ''', start_time, end_time)
            
            print(f"\nMiners with 4+ days of 12+ hours - Found {len(qualified)} qualifying miners")
            for row in qualified[:5]:
                print(f"  Miner: {row['miner']}, Qualifying days: {row['qualifying_days']}")
            
            # Check daily miner counts
            daily_counts = await conn.fetch('''
                SELECT 
                    DATE(created) as day,
                    COUNT(DISTINCT miner) as miners
                FROM minerstats
                WHERE created >= $1
                GROUP BY DATE(created)
                ORDER BY day
            ''', start_time)
            
            print('\nDaily miner counts:')
            for row in daily_counts:
                print(f'  {row["day"]}: {row["miners"]} miners')
        
        await conn.close()
        
    except Exception as e:
        print(f'Error executing loyal miners query: {str(e)}')

if __name__ == "__main__":
    asyncio.run(test_loyal_miners_query()) 