import asyncio
import asyncpg
import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def verify_granular_activity():
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
        
        # Get our sample miner from previous analysis
        sample_miner = "9f6PPoCYrvHQbS6U8s7y6wE1S6pFET712ajBCzH5Ep7mYTGBudy"
        
        print("\n1. Detailed Time Gap Analysis:")
        print("============================")
        
        # Analyze time gaps between consecutive records
        gaps = await conn.fetch('''
            WITH numbered_records AS (
                SELECT 
                    created,
                    hashrate,
                    LAG(created) OVER (ORDER BY created) as prev_created,
                    ROW_NUMBER() OVER (ORDER BY created) as rn
                FROM minerstats 
                WHERE miner = $1 
                AND created >= $2
                ORDER BY created
            )
            SELECT 
                created,
                prev_created,
                EXTRACT(EPOCH FROM (created - prev_created)) as gap_seconds,
                hashrate
            FROM numbered_records
            WHERE prev_created IS NOT NULL
            ORDER BY gap_seconds DESC
            LIMIT 10
        ''', sample_miner, start_time)
        
        print("\nLargest time gaps between records:")
        for gap in gaps:
            print(f"Gap of {gap['gap_seconds']:.1f} seconds between:")
            print(f"  {gap['prev_created']} and {gap['created']}")
        
        print("\n2. Activity Continuity Analysis:")
        print("==============================")
        
        # Analyze continuous activity periods
        activity_periods = await conn.fetch('''
            WITH time_groups AS (
                SELECT 
                    created,
                    hashrate,
                    DATE(created) as day,
                    created - (LAG(created) OVER (ORDER BY created)) as time_gap,
                    CASE 
                        WHEN created - (LAG(created) OVER (ORDER BY created)) > INTERVAL '30 minutes'
                        THEN 1 
                        ELSE 0 
                    END as new_period
                FROM minerstats 
                WHERE miner = $1 
                AND created >= $2
            ),
            periods AS (
                SELECT 
                    created,
                    hashrate,
                    day,
                    SUM(new_period) OVER (ORDER BY created) as period_id
                FROM time_groups
            ),
            period_stats AS (
                SELECT 
                    day,
                    period_id,
                    MIN(created) as period_start,
                    MAX(created) as period_end,
                    COUNT(*) as data_points,
                    AVG(hashrate) as avg_hashrate
                FROM periods 
                GROUP BY day, period_id
            )
            SELECT 
                day,
                period_start,
                period_end,
                EXTRACT(EPOCH FROM (period_end - period_start))/3600 as duration_hours,
                data_points,
                avg_hashrate
            FROM period_stats
            ORDER BY period_start
        ''')
        
        print("\nContinuous activity periods (gaps > 30 min considered breaks):")
        current_day = None
        total_hours = 0
        for period in activity_periods:
            if current_day != period['day']:
                if current_day:
                    print(f"Total hours of continuous activity: {total_hours:.2f}")
                print(f"\nDate: {period['day']}")
                current_day = period['day']
                total_hours = 0
            
            duration = period['duration_hours']
            total_hours += duration
            print(f"  Period: {period['period_start']} to {period['period_end']}")
            print(f"  Duration: {duration:.2f} hours ({period['data_points']} data points)")
            print(f"  Avg hashrate: {period['avg_hashrate']:.2f}")
        
        if current_day:
            print(f"Total hours of continuous activity: {total_hours:.2f}")
        
        print("\n3. Hourly Coverage Analysis:")
        print("==========================")
        
        # Analyze partial hour coverage
        hourly_coverage = await conn.fetch('''
            WITH minute_activity AS (
                SELECT 
                    DATE(created) as day,
                    date_trunc('hour', created) as hour_start,
                    date_trunc('minute', created) as minute,
                    AVG(hashrate) as minute_hashrate
                FROM minerstats 
                WHERE miner = $1 
                AND created >= $2
                GROUP BY DATE(created), date_trunc('hour', created), date_trunc('minute', created)
            )
            SELECT 
                day,
                hour_start,
                COUNT(DISTINCT minute) as active_minutes,
                COUNT(DISTINCT minute) >= 30 as would_count_as_active,
                AVG(minute_hashrate) as avg_hashrate
            FROM minute_activity
            GROUP BY day, hour_start
            ORDER BY hour_start
        ''', sample_miner, start_time)
        
        print("\nHourly activity coverage (minutes per hour):")
        current_day = None
        active_hours_strict = 0
        active_hours_30min = 0
        for hour in hourly_coverage:
            if current_day != hour['day']:
                if current_day:
                    print(f"Summary for {current_day}:")
                    print(f"  Hours with full activity: {active_hours_strict}")
                    print(f"  Hours with 30+ min activity: {active_hours_30min}")
                print(f"\nDate: {hour['day']}")
                current_day = hour['day']
                active_hours_strict = 0
                active_hours_30min = 0
            
            print(f"  Hour starting {hour['hour_start']}")
            print(f"    Active minutes: {hour['active_minutes']}")
            print(f"    Would count as active (30+ min): {'Yes' if hour['would_count_as_active'] else 'No'}")
            print(f"    Avg hashrate: {hour['avg_hashrate']:.2f}")
            
            if hour['active_minutes'] >= 55:  # Nearly full hour
                active_hours_strict += 1
            if hour['would_count_as_active']:
                active_hours_30min += 1
        
        if current_day:
            print(f"\nSummary for {current_day}:")
            print(f"  Hours with full activity: {active_hours_strict}")
            print(f"  Hours with 30+ min activity: {active_hours_30min}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error during verification: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_granular_activity()) 