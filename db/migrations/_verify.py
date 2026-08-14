"""Verify migration and explore DB state."""
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

# Check migration log
cur.execute('SELECT * FROM migration_log ORDER BY id')
print('=== MIGRATION LOG ===')
for row in cur.fetchall():
    print(row)

# Check distinct normalized_category in watch_list
cur.execute("""
    SELECT DISTINCT normalized_category 
    FROM watch_list 
    WHERE normalized_category IS NOT NULL AND normalized_category != ''
    ORDER BY normalized_category
""")
print('\n=== WATCH LIST CATEGORIES ===')
rows = cur.fetchall()
for row in rows:
    print(f'  "{row[0]}"')
print(f'Total distinct categories: {len(rows)}')

# Count totals
cur.execute('SELECT COUNT(*) FROM watch_list')
print(f'Watch list total: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM latest_prices')
print(f'Latest prices total: {cur.fetchone()[0]}')

# Check how many match between latest_prices and watch_list
cur.execute("""
    SELECT COUNT(*) 
    FROM latest_prices lp
    JOIN watch_list wl ON lp.nabkade_product_id = wl.nabkade_product_id
    WHERE wl.normalized_category IS NOT NULL AND wl.normalized_category != ''
""")
print(f'Products with categories (via join): {cur.fetchone()[0]}')

# Check actual category column in latest_prices
cur.execute("""
    SELECT category, COUNT(*) as cnt 
    FROM latest_prices 
    WHERE category IS NOT NULL AND category != '' 
    GROUP BY category 
    ORDER BY cnt DESC 
    LIMIT 20
""")
print('\n=== CATEGORIES IN latest_prices (after migration) ===')
for row in cur.fetchall():
    print(f'  "{row[0]}": {row[1]}')

# Null categories
cur.execute("SELECT COUNT(*) FROM latest_prices WHERE category IS NULL OR category = ''")
print(f'Null/empty categories: {cur.fetchone()[0]}')

# Sample a few rows
cur.execute("""
    SELECT nabkade_product_id, torob_product_id, sku, category 
    FROM latest_prices 
    WHERE category IS NOT NULL AND category != ''
    LIMIT 5
""")
print('\n=== SAMPLE PRODUCTS WITH CATEGORIES ===')
for row in cur.fetchall():
    print(f'  {row[0]} -> sku={row[2]}, category="{row[3]}"')

cur.close()
conn.close()