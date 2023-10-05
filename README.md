# Dexterity Fills Metrics

This script 

1. Hits the /fills/ endpoint, inserting results into sqlite
2. Shows metrics about the fills, including total volume, average volume by day, etc.
3. Is currently hardcoded to only fetch data for ZDFs (NOT PERPs) 
4. Is currently hardcoded to a set of underlyings --- OPOS, ETH, BITCOIN

# Example Output

```
Total Volume: $69,512.43

Volume Per Product:
BITCOIN $48,160.99
OPOS $20,300.61
ETH $1,050.83

Best Days:
29 Sep 2023 $13,795.39
18 Sep 2023 $12,125.87
14 Sep 2023 $8,563.52
30 Sep 2023 $6,505.22
12 Sep 2023 $5,529.85
11 Sep 2023 $4,658.03
13 Sep 2023 $4,640.44

Average Notional Volume Per Day: 3159.6558272727275

Average Notional Volume Per Day Per Product:
BITCOIN $2,833.00
ETH $262.71
OPOS $6,766.87
```

# Running it

First, create an sqlite database at `fills.sqilte` inside the cloned repository:

```
sqlite3 fills.sqlite # run this inside the cloned repository
```

Second, create this table:

```
CREATE TABLE fills (
    base_size REAL,
    block_timestamp TEXT,
    inserted_at TEXT,
    maker_client_order_id INTEGER,
    maker_order_id TEXT,
    maker_order_nonce TEXT,
    maker_trg TEXT,
    mpg TEXT,
    price REAL,
    product TEXT,
    quote_size REAL,
    slot INTEGER,
    taker_client_order_id INTEGER,
    taker_order_nonce TEXT,
    taker_side TEXT,
    taker_trg TEXT,
    tx_sig TEXT
);
```

Eventually the script will do that^ for you.

Third, install the python project

```
poetry install
```

Finally, run the script

```
poetry run python3 main.py
```

### Important note

Manual management of the database is required.

The script merely prints metrics on what's in the database. 

It NEVER removes data from the database.

If you want to run metrics on a specific date, then you MUST delete all the data in the database manually before the script fetches the relevant data.

To delete everything in the database:

```
sqlite3 fills.db
sqlite> DELETE FROM fills;
```

### Skipping fetching if DB already populated

If you've already populated the database, you can skip fetching with `--skip-fetch`.

### Filter by specific years, days, or months

The args `--year`, `--day`, `--month` expect two-digit numbers (e.g., 2023 corresponds to `--year 23`).

For example, to get volume metrics for October 2023, run:

```
poetry run python3 main.py --year 23 --month 10
```

