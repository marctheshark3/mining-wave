import asyncio
import asyncpg
import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def verify_bonus_calculations():
    end_time = datetime.datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    try:
        # Get database connection parameters from environment variables
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = int(os.getenv('DB_PORT', '5432'))
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        db_name = os.getenv('DB_NAME', 'miningcore')
        
        print(f"Connecting to database...")
        
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        print("\n1. Basic Data Verification:")
        print("==========================")
        
        # Check data distribution for a single active miner
        sample_miner = await conn.fetchval('''
            SELECT miner 
            FROM minerstats 
            WHERE created >= $1 
            GROUP BY miner 
            ORDER BY COUNT(*) DESC 
            LIMIT 1
        ''', start_time)
        
        if sample_miner:
            print(f"\nAnalyzing sample miner: {sample_miner}")
            
            # Get raw data points for this miner
            raw_data = await conn.fetch('''
                SELECT 
                    created,
                    hashrate,
                    worker,
                    sharespersecond
                FROM minerstats 
                WHERE miner = $1 
                AND created >= $2
                ORDER BY created
            ''', sample_miner, start_time)
            
            print(f"Total data points: {len(raw_data)}")
            if raw_data:
                print(f"First record: {raw_data[0]['created']}")
                print(f"Last record: {raw_data[-1]['created']}")
                
                # Analyze data points per day
                daily_points = await conn.fetch('''
                    SELECT 
                        DATE(created) as day,
                        COUNT(*) as points,
                        COUNT(DISTINCT date_trunc('hour', created)) as distinct_hours,
                        AVG(hashrate) as avg_hashrate
                    FROM minerstats 
                    WHERE miner = $1 
                    AND created >= $2
                    GROUP BY DATE(created)
                    ORDER BY day
                ''', sample_miner, start_time)
                
                print("\nDaily breakdown:")
                for day in daily_points:
                    print(f"Date: {day['day']}")
                    print(f"  - Data points: {day['points']}")
                    print(f"  - Distinct hours: {day['distinct_hours']}")
                    print(f"  - Avg hashrate: {day['avg_hashrate']:.2f}")
        
        print("\n2. Hourly Activity Analysis:")
        print("===========================")
        
        # Analyze how we're counting active hours
        hourly_analysis = await conn.fetch('''
            WITH hourly_stats AS (
                SELECT 
                    miner,
                    date_trunc('hour', created) AS hour,
                    DATE(created) AS day,
                    COUNT(*) as points_in_hour,
                    AVG(hashrate) as avg_hashrate
                FROM minerstats
                WHERE created >= $1 
                AND miner = $2
                GROUP BY miner, date_trunc('hour', created), DATE(created)
                HAVING AVG(hashrate) > 0
            )
            SELECT 
                day,
                COUNT(DISTINCT hour) as active_hours,
                COUNT(*) as total_hours_with_data,
                AVG(avg_hashrate) as daily_avg_hashrate,
                MIN(points_in_hour) as min_points_per_hour,
                MAX(points_in_hour) as max_points_per_hour,
                AVG(points_in_hour) as avg_points_per_hour
            FROM hourly_stats
            GROUP BY day
            ORDER BY day
        ''', start_time, sample_miner)
        
        print("\nHourly activity breakdown for sample miner:")
        for day in hourly_analysis:
            print(f"\nDate: {day['day']}")
            print(f"  - Active hours: {day['active_hours']}")
            print(f"  - Hours with data: {day['total_hours_with_data']}")
            print(f"  - Daily avg hashrate: {day['daily_avg_hashrate']:.2f}")
            print(f"  - Points per hour: min={day['min_points_per_hour']}, max={day['max_points_per_hour']}, avg={day['avg_points_per_hour']:.2f}")
        
        print("\n3. Qualifying Days Analysis:")
        print("===========================")
        
        # Check how many miners have any qualifying days
        qualifying_days = await conn.fetch('''
            WITH hourly_activity AS (
                SELECT 
                    miner,
                    date_trunc('hour', created) AS hour,
                    DATE(created) AS day,
                    AVG(hashrate) AS avg_hashrate
                FROM minerstats
                WHERE created >= $1
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
                active_hours,
                COUNT(*) as day_count
            FROM daily_activity
            GROUP BY active_hours
            ORDER BY active_hours DESC
        ''', start_time)
        
        print("\nDistribution of active hours per day:")
        for row in qualifying_days:
            print(f"  {row['active_hours']} hours: {row['day_count']} instances")
        
        print("\n4. Final Qualification Check:")
        print("===========================")
        
        # Get miners close to qualifying
        almost_qualified = await conn.fetch('''
            WITH hourly_activity AS (
                SELECT 
                    miner,
                    date_trunc('hour', created) AS hour,
                    DATE(created) AS day,
                    AVG(hashrate) AS avg_hashrate
                FROM minerstats
                WHERE created >= $1
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
            ),
            miner_stats AS (
                SELECT 
                    miner,
                    COUNT(DISTINCT day) as total_days,
                    COUNT(DISTINCT CASE WHEN active_hours >= 12 THEN day END) as qualifying_days,
                    AVG(active_hours) as avg_hours_per_day,
                    MAX(active_hours) as max_hours_in_day
                FROM daily_activity
                GROUP BY miner
                HAVING COUNT(DISTINCT day) >= 3  -- Looking for miners active at least 3 days
            )
            SELECT *
            FROM miner_stats
            ORDER BY qualifying_days DESC, avg_hours_per_day DESC
            LIMIT 10
        ''', start_time)
        
        print("\nMiners closest to qualifying:")
        for row in almost_qualified:
            print(f"\nMiner: {row['miner']}")
            print(f"  - Total active days: {row['total_days']}")
            print(f"  - Days with 12+ hours: {row['qualifying_days']}")
            print(f"  - Average hours per day: {row['avg_hours_per_day']:.2f}")
            print(f"  - Max hours in a day: {row['max_hours_in_day']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error during verification: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_bonus_calculations()) 