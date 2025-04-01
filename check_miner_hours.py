import asyncio
import asyncpg
import datetime
from tabulate import tabulate

async def check_miner_hours():
    # Use one of the miners we saw in the previous script
    miner_address = "9effDLCFNCcfxaff26utAWK7dfLZU4zqMd5rc2CVzQ3yzs5ME8R"
    
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=7)
    
    try:
        conn = await asyncpg.connect(
            host='***REMOVED***',
            port=5432,
            user='miningcore',
            password='this_IS_thesigmining',
            database='miningcore'
        )
        
        print(f"Checking hours for miner: {miner_address}")
        
        # Get detailed hourly breakdown
        hourly_data = await conn.fetch('''
            SELECT 
                date_trunc('hour', created) AS hour,
                DATE(created) AS day,
                AVG(hashrate) AS avg_hashrate
            FROM minerstats
            WHERE created >= $1 AND created <= $2
            AND miner = $3
            GROUP BY date_trunc('hour', created), DATE(created)
            ORDER BY hour
        ''', start_time, end_time, miner_address)
        
        print(f"Found {len(hourly_data)} hours of data")
        
        # Organize by day
        days = {}
        for row in hourly_data:
            day = row['day'].strftime('%Y-%m-%d')
            if day not in days:
                days[day] = []
            days[day].append({
                'hour': row['hour'].strftime('%H:%M'),
                'hashrate': float(row['avg_hashrate'])
            })
        
        # Print summary by day
        print("\nDaily Summary:")
        day_summary = []
        for day, hours in days.items():
            active_hours = len([h for h in hours if h['hashrate'] > 0])
            avg_hashrate = sum(h['hashrate'] for h in hours) / len(hours) if hours else 0
            day_summary.append([day, active_hours, f"{avg_hashrate:.2f}"])
        
        print(tabulate(day_summary, headers=["Day", "Active Hours", "Avg Hashrate"]))
        
        # Print detailed breakdown for each day
        print("\nDetailed Hours Breakdown (hours with hashrate > 0):")
        for day, hours in days.items():
            active_hours = [h for h in hours if h['hashrate'] > 0]
            if active_hours:
                print(f"\n{day} - {len(active_hours)} active hours:")
                hour_details = [[h['hour'], f"{h['hashrate']:.2f}"] for h in active_hours]
                print(tabulate(hour_details, headers=["Hour", "Hashrate"]))
        
        # Check consecutive hours
        print("\nConsecutive Hours Analysis:")
        for day, hours in days.items():
            if not hours:
                continue
                
            # Sort by hour
            hours.sort(key=lambda h: h['hour'])
            
            # Find consecutive hour sequences
            sequences = []
            current_seq = []
            last_hour = None
            
            for hour_data in hours:
                hour_obj = datetime.datetime.strptime(f"{day} {hour_data['hour']}", '%Y-%m-%d %H:%M')
                
                if hour_data['hashrate'] <= 0:
                    # Skip hours with zero hashrate
                    if current_seq:
                        sequences.append(current_seq)
                        current_seq = []
                    last_hour = None
                    continue
                    
                if not last_hour:
                    current_seq = [hour_data]
                else:
                    # Check if this is consecutive to the last hour
                    expected_next = last_hour + datetime.timedelta(hours=1)
                    if expected_next.hour == hour_obj.hour:
                        current_seq.append(hour_data)
                    else:
                        # Not consecutive, start a new sequence
                        if current_seq:
                            sequences.append(current_seq)
                        current_seq = [hour_data]
                
                last_hour = hour_obj
            
            # Add the final sequence if it exists
            if current_seq:
                sequences.append(current_seq)
            
            # Report longest consecutive sequence
            if sequences:
                longest_seq = max(sequences, key=len)
                print(f"{day}: Longest consecutive sequence is {len(longest_seq)} hours")
                
                # Print sequence details if significant
                if len(longest_seq) >= 5:
                    start = longest_seq[0]['hour']
                    end = longest_seq[-1]['hour']
                    print(f"  Sequence from {start} to {end}")
            else:
                print(f"{day}: No consecutive hours with hashrate > 0")
        
        await conn.close()
        
    except Exception as e:
        print(f'Error checking miner hours: {str(e)}')

if __name__ == "__main__":
    asyncio.run(check_miner_hours()) 