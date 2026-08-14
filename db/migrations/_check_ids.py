"""Check real product IDs and verify Torob URLs."""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2

p = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'dbname': os.getenv('DB_NAME', 'torob_intel'),
    'user': os.getenv('DB_USER', 'torob_user'),
    'password': os.getenv('DB_PASSWORD', 'SecurePassword123'),
}

conn = psycopg2.connect(**p)
cur = conn.cursor()

cur.execute("""
    SELECT torob_product_id, nabkade_product_id, sku, category 
    FROM latest_prices 
    LIMIT 5
""")
print('=== REAL PRODUCT IDS ===')
for row in cur.fetchall():
    print(f'  torob_id={row[0]}, sku={row[2]}, category={row[3]}')

# Also check market_snapshot for more torob_product_ids
cur.execute("""
    SELECT torob_product_id 
    FROM market_snapshot 
    WHERE torob_product_id IS NOT NULL 
    LIMIT 5
""")
print('\n=== SAMPLE TOROB IDS FROM market_snapshot ===')
for row in cur.fetchall():
    print(f'  {row[0]}')

cur.close()
conn.close()