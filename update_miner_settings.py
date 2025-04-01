import os
import time
import schedule
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'mirror')
DB_PORT = os.getenv('DB_PORT', '5432')
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:{DB_PORT}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_miner_setting(miner_address: str, minimum_payout_threshold: float, swapping: bool):
    print(f"Updating settings for miner: {miner_address}")
    try:
        with SessionLocal() as db:
            query = text("""
                INSERT INTO miner_payouts (miner_address, minimum_payout_threshold, swapping)
                VALUES (:miner_address, :minimum_payout_threshold, :swapping)
                ON CONFLICT (miner_address) DO UPDATE
                SET minimum_payout_threshold = :minimum_payout_threshold,
                    swapping = :swapping,
                    created_at = CURRENT_TIMESTAMP
            """)
            db.execute(query, {
                "miner_address": miner_address,
                "minimum_payout_threshold": minimum_payout_threshold,
                "swapping": swapping
            })
            db.commit()
        print(f"Settings updated successfully for miner: {miner_address}")
    except Exception as e:
        print(f"An error occurred while updating settings for miner {miner_address}: {str(e)}")

def update_all_miners():
    # You can call update_miner_setting for each miner here
    # For example:
    # update_miner_setting("9iNFqptqcnMQL4BEtVgjnsJGqiJFDb6xm1pzPCKCJvvnwuYD1Jo", 2.0, True)
    # update_miner_setting("9hrFxcVeaNeBYXUx69nbUJkQHE5PgYpdscKPLNo6z6zKkUVNBmE", 20.5, False)
    # Add more miners as needed
    pass

def run_scheduler():
    schedule.every(30).minutes.do(update_all_miners)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
