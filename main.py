import argparse
import requests
import sqlite3
from datetime import datetime, timezone
from time import mktime
import sys

def get_fills(product, before=None):
    print(f"getting fills for {product} before {before}...", end="")
    url = f"https://dexterity.hxro.com/fills?product={product}"
    if before:
        url += f"&before={before}"
    response = requests.get(url)
    data = response.json()
    print("success!")
    return data['fills']

def convert_to_unix_timestamp(timestamp_str):
    """Convert the timestamp string to a UNIX timestamp."""
    dt = datetime.strptime(timestamp_str, '%a, %d %b %Y %H:%M:%S %Z')
    return int(dt.replace(tzinfo=timezone.utc).timestamp())

def save_to_db(fills):
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    for fill in fills:
        cursor.execute("""
            INSERT INTO fills (base_size, block_timestamp, inserted_at, maker_client_order_id, maker_order_id, maker_order_nonce,
            maker_trg, mpg, price, product, quote_size, slot, taker_client_order_id, taker_order_nonce, taker_side, taker_trg, tx_sig) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fill['base_size'], fill['block_timestamp'], fill['inserted_at'], fill['maker_client_order_id'], fill['maker_order_id'],
                  fill['maker_order_nonce'], fill['maker_trg'], fill['mpg'], fill['price'], fill['product'], fill['quote_size'],
                  fill['slot'], fill['taker_client_order_id'], fill['taker_order_nonce'], fill['taker_side'], fill['taker_trg'], fill['tx_sig']))

    conn.commit()
    conn.close()

def deduplicate_db():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    # Create a temporary table with unique rows
    cursor.execute("""
        CREATE TEMP TABLE temp_fills AS
        SELECT *
        FROM (
            SELECT *
            FROM fills
            ORDER BY maker_order_id, taker_order_nonce
        )
        GROUP BY maker_order_id, taker_order_nonce;
    """)

    # Delete all rows from original table
    cursor.execute("DELETE FROM fills;")

    # Copy unique rows back to the original table
    cursor.execute("INSERT INTO fills SELECT * FROM temp_fills;")

    # Drop temporary table
    cursor.execute("DROP TABLE temp_fills;")

    conn.commit()
    conn.close()

def total_volume():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(price * base_size) AS notional_volume FROM fills;")
    volume = cursor.fetchone()[0]

    conn.close()
    return volume

def volume_per_product():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUBSTR(product, 1, LENGTH(product)-8) AS underlying, 
        SUM(price * base_size) AS notional 
        FROM fills 
        GROUP BY underlying 
        ORDER BY notional DESC;
    """)
    
    results = cursor.fetchall()

    conn.close()
    return results

def best_days():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            SUBSTR(block_timestamp, 6, 11) AS date, 
            SUM(price * base_size) AS notional_volume
        FROM fills
        GROUP BY date
        ORDER BY notional_volume DESC
        LIMIT 7;
    """)
    
    results = cursor.fetchall()

    conn.close()
    return results

def average_notional_volume_per_day():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT AVG(notional_volume) 
        FROM (
            SELECT 
                SUBSTR(block_timestamp, 6, 11) AS date, 
                SUM(price * base_size) AS notional_volume
            FROM fills
            GROUP BY date
        );
    """)
    
    average = cursor.fetchone()[0]

    conn.close()
    return average

def average_notional_volume_per_day_per_product():
    conn = sqlite3.connect('fills.sqlite')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            SUBSTR(product, 1, LENGTH(product)-8) AS underlying,
            AVG(notional_volume) 
        FROM (
            SELECT 
                product,
                SUBSTR(block_timestamp, 6, 11) AS date, 
                SUM(price * base_size) AS notional_volume
            FROM fills
            GROUP BY product, date
        )
        GROUP BY underlying;
    """)
    
    results = cursor.fetchall()

    conn.close()
    return results

def format_as_usd(volume):
    return "${:,.2f}".format(volume)

def main():
    parser = argparse.ArgumentParser(description="Fetch and process data.")
    parser.add_argument('--skip-fetch', action='store_true', help="Skip fetching data from API.")
    parser.add_argument('--year', type=int, default=23, help="Last two digits of year to fetch data for. Default is 23.")
    parser.add_argument('--month', type=int, help="Month to fetch data for. If unspecified, fetches data for the whole year.")
    parser.add_argument('--day', type=int, help="Day to fetch data for. If unspecified, fetches data for the whole month.")

    args = parser.parse_args()

    underlyings = ['OPOS', 'BITCOIN', 'ETH']

    # Determine the range of months and days based on the provided arguments
    months = range(1, 13) if args.month is None else [args.month]
    days = range(1, 32)  # Default to 31 days, some checks might be redundant for months with less days but it keeps the logic simpler

    if not args.skip_fetch:
        for underlying in underlyings:
            for month in months:
                for day in days:
                    if args.day and day != args.day:
                        continue  # If a specific day is provided, skip other days
                    product = f"{underlying}0D{args.year}{month:02}{day:02}"
                    before = None
                    while True:
                        fills = get_fills(product, before)
                        if not fills:
                            break
                        oldest_timestamp = fills[-1]['block_timestamp']
                        before = convert_to_unix_timestamp(oldest_timestamp)
                        print(f"oldest timestamp = {oldest_timestamp}. before = {before}")
                        save_to_db(fills)
    
    deduplicate_db()
    print("\nTotal Volume:", format_as_usd(total_volume()))
    print("\nVolume Per Product:")
    for product, volume in volume_per_product():
        print(product, format_as_usd(volume))

    print("\nBest Days:")
    for date, volume in best_days():
        print(date, format_as_usd(volume))

    print("\nAverage Notional Volume Per Day:", format_as_usd(average_notional_volume_per_day()))

    print("\nAverage Notional Volume Per Day Per Product:")    
    for product, avg_volume in average_notional_volume_per_day_per_product():
        print(product, format_as_usd(avg_volume))

if __name__ == "__main__":
    main()
