import asyncio
import asyncpg
import os
import datetime
from dotenv import load_dotenv

async def check_thresholds():
    load_dotenv()
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=7)
    
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        database=os.getenv('DB_NAME', 'miningcore')
    )
    
    print("Connected to database. Checking miner thresholds...")
    
    # Count qualifying miners with various criteria
    print('\nMiners qualifying with different hour requirements:')
    for hours in [2, 4, 6, 8, 10, 12]:
        count = await conn.fetchval('''
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
                    COUNT(DISTINCT hour) as active_hours
                FROM hourly_activity
                GROUP BY miner, day
                HAVING COUNT(DISTINCT hour) >= $3
            ),
            qualified_miners AS (
                SELECT 
                    miner,
                    COUNT(DISTINCT day) AS days_active
                FROM daily_activity
                GROUP BY miner
                HAVING COUNT(DISTINCT day) >= 4
            )
            SELECT COUNT(*)
            FROM qualified_miners
        ''', start_time, end_time, hours)
        print(f'  {hours}+ hours per day for 4+ days: {count} miners')
    
    # Check different days requirements
    print('\nMiners qualifying with different day requirements (4+ hours/day):')
    for days in [1, 2, 3, 4, 5, 6, 7]:
        count = await conn.fetchval('''
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
                    COUNT(DISTINCT hour) as active_hours
                FROM hourly_activity
                GROUP BY miner, day
                HAVING COUNT(DISTINCT hour) >= 4
            ),
            qualified_miners AS (
                SELECT 
                    miner,
                    COUNT(DISTINCT day) AS days_active
                FROM daily_activity
                GROUP BY miner
                HAVING COUNT(DISTINCT day) >= $3
            )
            SELECT COUNT(*)
            FROM qualified_miners
        ''', start_time, end_time, days)
        print(f'  {days}+ days with 4+ hours: {count} miners')
    
    # Get top miner statistics
    print('\nTop miners by activity hours:')
    top_miners = await conn.fetch('''
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
                COUNT(DISTINCT hour) as active_hours,
                AVG(avg_hashrate) as daily_avg_hashrate
            FROM hourly_activity
            GROUP BY miner, day
        ),
        miner_stats AS (
            SELECT 
                miner,
                COUNT(DISTINCT day) AS days_active,
                AVG(active_hours) as avg_hours_per_day,
                SUM(active_hours) as total_hours,
                AVG(daily_avg_hashrate) as avg_hashrate
            FROM daily_activity
            GROUP BY miner
            ORDER BY total_hours DESC
            LIMIT 10
        )
        SELECT *
        FROM miner_stats
    ''', start_time, end_time)
    
    for i, row in enumerate(top_miners, 1):
        print(f"\n#{i}: Miner {row['miner']}")
        print(f"  Days active: {row['days_active']} days")
        print(f"  Avg hours per day: {row['avg_hours_per_day']:.2f} hours")
        print(f"  Total active hours: {row['total_hours']} hours")
        print(f"  Avg hashrate: {row['avg_hashrate'] / 1e9:.2f} GH/s")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_thresholds()) 