import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'mirror')
DB_PORT = os.getenv('DB_PORT', '5432')
DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{DB_HOST}:{DB_PORT}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_miner_settings(miner_address, minimum_payout_threshold, swapping):
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

if __name__ == "__main__":
    # Example usage
    update_miner_settings("9iNFqptqcnMQL4BEtVgjnsJGqiJFDb6xm1pzPCKCJvvnwuYD1Jo", 2.0, True)
