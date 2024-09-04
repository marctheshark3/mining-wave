import os
import time
import psycopg2
import requests

def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        host=os.environ['DB_HOST'],
        port=os.environ['DB_PORT']
    )

def update_blocks():
    conn = get_db_connection()
    cur = conn.cursor()

    api_url = "https://api.ergoplatform.com/api/v0/blocks"
    response = requests.get(api_url)
    data = response.json()

    for block in data['items']:
        cur.execute("""
            INSERT INTO blocks (height, hash, timestamp)
            VALUES (%s, %s, %s)
            ON CONFLICT (height) DO NOTHING
        """, (block['height'], block['id'], block['timestamp']))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    while True:
        update_blocks()
        time.sleep(600)  # Wait for 10 minutes