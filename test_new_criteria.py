import asyncio
import asyncpg
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def test_alternative_criteria():
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=7)
    limit = 100
    
    # Current criteria (3 days with 12+ hours)
    current_query = '''
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
    
    # Alternative criteria (4 days with 8+ hours)
    alternative_query = '''
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
        WHERE active_hours >= 8
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
    
    # Detailed breakdown query to check how many miners have different hour/day combinations
    breakdown_query = '''
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
    miner_active_days AS (
        SELECT 
            miner,
            COUNT(*) as total_active_days,
            COUNT(*) FILTER (WHERE active_hours >= 8) as days_with_8plus_hours,
            COUNT(*) FILTER (WHERE active_hours >= 12) as days_with_12plus_hours
        FROM daily_activity
        GROUP BY miner
        HAVING COUNT(*) >= 3
    )
    SELECT
        miner,
        total_active_days,
        days_with_8plus_hours,
        days_with_12plus_hours
    FROM miner_active_days
    WHERE days_with_8plus_hours >= 4 OR days_with_12plus_hours >= 3
    ORDER BY days_with_8plus_hours DESC, days_with_12plus_hours DESC
    LIMIT 50
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
        
        print("Connected to database. Running comparison queries...")
        
        # Execute the current query (3 days with 12+ hours)
        current_rows = await conn.fetch(current_query, start_time, end_time, limit)
        print(f'Current criteria (3+ days with 12+ hours): Found {len(current_rows)} miners')
        
        # Execute the alternative query (4 days with 8+ hours)
        alternative_rows = await conn.fetch(alternative_query, start_time, end_time, limit)
        print(f'Alternative criteria (4+ days with 8+ hours): Found {len(alternative_rows)} miners')
        
        # Calculate the differences between the two sets
        current_miners = set(row['miner'] for row in current_rows)
        alternative_miners = set(row['miner'] for row in alternative_rows)
        
        only_in_current = current_miners - alternative_miners
        only_in_alternative = alternative_miners - current_miners
        in_both = current_miners.intersection(alternative_miners)
        
        print(f"\nComparison:")
        print(f"- Miners qualifying under both criteria: {len(in_both)}")
        print(f"- Miners qualifying only under current criteria (3/12): {len(only_in_current)}")
        print(f"- Miners qualifying only under alternative criteria (4/8): {len(only_in_alternative)}")
        
        # Get detailed breakdown of days and hours
        breakdown_rows = await conn.fetch(breakdown_query, start_time, end_time)
        
        # Create distribution table
        distribution = {}
        for row in breakdown_rows:
            days_8plus = row['days_with_8plus_hours']
            days_12plus = row['days_with_12plus_hours']
            key = (days_8plus, days_12plus)
            
            if key not in distribution:
                distribution[key] = 0
            distribution[key] += 1
        
        print("\nDistribution of miners by active days:")
        print("| Days with 8+ hours | Days with 12+ hours | Count |")
        print("|-------------------|-------------------|-------|")
        for (days_8plus, days_12plus), count in sorted(distribution.items(), 
                                                     key=lambda x: (x[0][0], x[0][1]), 
                                                     reverse=True):
            print(f"| {days_8plus:17d} | {days_12plus:19d} | {count:5d} |")
        
        # Detailed analysis of miners in each group
        if only_in_current:
            print("\nSample of miners qualifying ONLY under current criteria (3/12):")
            for i, miner in enumerate(list(only_in_current)[:5]):
                for row in breakdown_rows:
                    if row['miner'] == miner:
                        print(f"{i+1}. Miner {miner}: {row['days_with_8plus_hours']} days with 8+ hours, {row['days_with_12plus_hours']} days with 12+ hours")
                        break
        
        if only_in_alternative:
            print("\nSample of miners qualifying ONLY under alternative criteria (4/8):")
            for i, miner in enumerate(list(only_in_alternative)[:5]):
                for row in breakdown_rows:
                    if row['miner'] == miner:
                        print(f"{i+1}. Miner {miner}: {row['days_with_8plus_hours']} days with 8+ hours, {row['days_with_12plus_hours']} days with 12+ hours")
                        break
                        
        # If we have a significant number in the alternatives, list top alternative miners
        if len(alternative_rows) > 0:
            print("\nTop 10 miners under alternative criteria (4/8):")
            for i, row in enumerate(alternative_rows[:10]):
                print(f"{i+1}. Miner: {row['miner']}, Avg hashrate: {row['weekly_avg_hashrate']}")
        
        await conn.close()
        
    except Exception as e:
        print(f'Error executing comparison queries: {str(e)}')

if __name__ == "__main__":
    asyncio.run(test_alternative_criteria()) 