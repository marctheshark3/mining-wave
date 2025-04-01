import asyncio
import asyncpg
from datetime import datetime, timedelta

CRITERIA_ORIGINAL = {"min_hours": 12, "min_days": 3, "title": "Original criteria (3 days with 12+ hours)"}
CRITERIA_NEW = {"min_hours": 8, "min_days": 4, "title": "New criteria (4 days with 8+ hours)"}

async def count_eligible_miners(conn, criteria):
    """Count miners eligible under specific criteria"""
    QUERY = f'''
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
        WHERE active_hours >= {criteria["min_hours"]}
        GROUP BY miner
        HAVING COUNT(DISTINCT day) >= {criteria["min_days"]}
    )
    SELECT COUNT(DISTINCT miner) as total_miners
    FROM qualified_miners
    '''
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    count = await conn.fetchval(QUERY, start_time, end_time)
    print(f'{criteria["title"]}: {count} miners')
    return count

async def get_miners_lists(conn, criteria):
    """Get lists of miners eligible under specific criteria"""
    QUERY = f'''
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
        WHERE active_hours >= {criteria["min_hours"]}
        GROUP BY miner
        HAVING COUNT(DISTINCT day) >= {criteria["min_days"]}
    )
    SELECT miner
    FROM qualified_miners
    ORDER BY weekly_avg_hashrate DESC
    '''
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    rows = await conn.fetch(QUERY, start_time, end_time)
    return [row['miner'] for row in rows]

async def main():
    """Run the analysis"""
    print("Connecting to database...")
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost/miningwave')
    
    try:
        # Count miners under each criteria
        original_count = await count_eligible_miners(conn, CRITERIA_ORIGINAL)
        new_count = await count_eligible_miners(conn, CRITERIA_NEW)
        
        # Get lists of miners under each criteria
        print("\nRetrieving miner lists for comparison...")
        original_miners = set(await get_miners_lists(conn, CRITERIA_ORIGINAL))
        new_miners = set(await get_miners_lists(conn, CRITERIA_NEW))
        
        # Analyze differences
        only_in_original = original_miners - new_miners
        only_in_new = new_miners - original_miners
        in_both = original_miners.intersection(new_miners)
        
        print(f"\nComparison Results:")
        print(f"- Miners in both criteria: {len(in_both)}")
        print(f"- Miners only in original criteria: {len(only_in_original)}")
        print(f"- Miners only in new criteria: {len(only_in_new)}")
        
        # Rate of change
        if original_count > 0:
            percent_change = ((new_count - original_count) / original_count) * 100
            print(f"\nThe new criteria results in a {percent_change:.1f}% change in eligible miners")
        
        # Show a few example miners from the new criteria
        if only_in_new:
            print(f"\nSample miners that qualify ONLY under new criteria:")
            for miner in list(only_in_new)[:3]:
                print(f"- {miner}")
    
    finally:
        await conn.close()
        print("\nAnalysis complete.")

if __name__ == "__main__":
    asyncio.run(main()) 