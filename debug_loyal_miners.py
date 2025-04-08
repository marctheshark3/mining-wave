import asyncio
import asyncpg
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
            AVG(hashrate) as avg_hashrate,
            COUNT(*) as datapoints
        FROM minerstats
        WHERE created >= $1 AND created <= $2
        GROUP BY miner, date_trunc('hour', created), DATE(created)
        HAVING AVG(hashrate) > 0
    ),
    daily_activity AS (
        SELECT 
            miner,
            day,
            COUNT(DISTINCT hour) as active_hours,
            AVG(avg_hashrate) as daily_avg_hashrate,
            SUM(datapoints) as total_datapoints
        FROM hourly_activity
        GROUP BY miner, day
        HAVING COUNT(DISTINCT hour) >= 4  -- At least 4 hours with any activity
    ),
    qualified_miners AS (
        SELECT 
            miner,
            COUNT(DISTINCT day) AS days_active,
            AVG(active_hours) as avg_hours_per_day,
            AVG(daily_avg_hashrate) AS weekly_avg_hashrate,
            SUM(total_datapoints) as week_datapoints
        FROM daily_activity
        GROUP BY miner
        HAVING COUNT(DISTINCT day) >= 4  -- Active on at least 4 days
        AND AVG(active_hours) >= 4  -- Average at least 4 hours per day
    )
    SELECT 
        qm.miner,
        qm.days_active,
        qm.avg_hours_per_day,
        qm.weekly_avg_hashrate,
        qm.week_datapoints,
        COALESCE(b.amount, 0) as current_balance,
        MAX(p.created) as last_payment_date
    FROM qualified_miners qm
    LEFT JOIN balances b ON qm.miner = b.address
    LEFT JOIN payments p ON qm.miner = p.address
    GROUP BY qm.miner, qm.days_active, qm.avg_hours_per_day, qm.weekly_avg_hashrate, qm.week_datapoints, b.amount
    ORDER BY qm.weekly_avg_hashrate DESC
    LIMIT $3
    '''
    
    try:
        # Get database connection parameters from environment variables
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', '5432'))
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        db_name = os.getenv('DB_NAME', 'miningcore')
        
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
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
                    COUNT(DISTINCT date_trunc('hour', created)) as hour_count,
                    AVG(hashrate) as avg_hashrate
                FROM minerstats
                WHERE created >= $1 AND created <= $2
                AND hashrate > 0
                GROUP BY miner
                ORDER BY hour_count DESC
                LIMIT 10
            ''', start_time, end_time)
            
            print(f"\nhourly_activity - Found {len(hourly_rows)} miners with hourly data")
            for row in hourly_rows[:5]:
                print(f"  Miner: {row['miner']}, Hours: {row['hour_count']}, Avg hashrate: {row['avg_hashrate']:.2f}")
            
            # Check daily_activity CTE
            daily_rows = await conn.fetch('''
                WITH hourly_activity AS (
                    SELECT 
                        miner,
                        date_trunc('hour', created) AS hour,
                        DATE(created) AS day,
                        AVG(hashrate) as avg_hashrate
                    FROM minerstats
                    WHERE created >= $1 AND created <= $2
                    GROUP BY miner, date_trunc('hour', created), DATE(created)
                    HAVING AVG(hashrate) > 0
                )
                SELECT 
                    miner,
                    COUNT(DISTINCT day) as active_days,
                    AVG(COUNT(DISTINCT hour)) OVER (PARTITION BY miner) as avg_hours_per_day
                FROM hourly_activity
                GROUP BY miner
                ORDER BY active_days DESC, avg_hours_per_day DESC
                LIMIT 10
            ''', start_time, end_time)
            
            print(f"\ndaily_activity - Found {len(daily_rows)} miners with daily activity")
            for row in daily_rows[:5]:
                print(f"  Miner: {row['miner']}, Active days: {row['active_days']}, Avg hours per day: {row['avg_hours_per_day']:.2f}")
            
            # Check how many hours per day miners are active
            hours_per_day = await conn.fetch('''
                WITH hourly_activity AS (
                    SELECT 
                        miner,
                        date_trunc('hour', created) AS hour,
                        DATE(created) AS day,
                        AVG(hashrate) as avg_hashrate
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
                HAVING COUNT(DISTINCT hour) >= 4
                ORDER BY miner, day
                LIMIT 20
            ''', start_time, end_time)
            
            print(f"\nMiners with at least 4 hours per day - Found {len(hours_per_day)} qualifying miner-days")
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
            
            # Check if any miners have 4+ days with 4+ hours
            qualified = await conn.fetch('''
                WITH hourly_activity AS (
                    SELECT 
                        miner,
                        date_trunc('hour', created) AS hour,
                        DATE(created) AS day,
                        AVG(hashrate) as avg_hashrate
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
                    HAVING COUNT(DISTINCT hour) >= 4
                )
                SELECT 
                    miner,
                    COUNT(DISTINCT day) as qualifying_days,
                    AVG(active_hours) as avg_hours_per_day
                FROM daily_activity
                GROUP BY miner
                HAVING COUNT(DISTINCT day) >= 4
                ORDER BY qualifying_days DESC
            ''', start_time, end_time)
            
            print(f"\nMiners with 4+ days of 4+ hours - Found {len(qualified)} qualifying miners")
            for row in qualified[:5]:
                print(f"  Miner: {row['miner']}, Qualifying days: {row['qualifying_days']}, Avg hours per day: {row['avg_hours_per_day']:.2f}")
            
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