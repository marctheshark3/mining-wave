import os
import time
import schedule
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'mirror')
DB_PORT = os.getenv('DB_PORT', '5432')
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:{DB_PORT}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

API_URL = "http://sigscore:8000/sigscore/miner_setting"

def update_miner_settings():
    print("Updating miner settings...")
    try:
        # Fetch current settings from the API
        response = requests.get(API_URL)
        if response.status_code == 200:
            current_settings = response.json()
            
            # Update settings in the database
            with SessionLocal() as db:
                for setting in current_settings:
                    query = text("""
                        INSERT INTO miner_payouts (miner_address, minimum_payout_threshold, swapping)
                        VALUES (:miner_address, :minimum_payout_threshold, :swapping)
                        ON CONFLICT (miner_address) DO UPDATE
                        SET minimum_payout_threshold = :minimum_payout_threshold,
                            swapping = :swapping,
                            created_at = CURRENT_TIMESTAMP
                    """)
                    db.execute(query, setting)
                db.commit()
            print("Miner settings updated successfully.")
        else:
            print(f"Failed to fetch miner settings. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while updating miner settings: {str(e)}")

def run_scheduler():
    schedule.every(30).minutes.do(update_miner_settings)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
