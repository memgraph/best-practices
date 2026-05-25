"""Generate users + transactions and write them to a local Iceberg warehouse.

Defaults: 1,000,000 users and 5,000,000 transactions.

Generation is vectorized with numpy, so producing 1M+5M rows takes only a
few seconds. Random seeds are fixed, so runs are deterministic.

In production your Iceberg tables already live in your data lake (S3 + Glue
or REST catalog). This script just creates a reproducible stand-in so the
example runs end-to-end on a fresh clone — only the catalog config block
below changes when you point at a real lake.
"""
import argparse
from pathlib import Path

import numpy as np
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import NoSuchNamespaceError, NoSuchTableError
from pyiceberg.io.pyarrow import schema_to_pyarrow
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

ROOT = Path(__file__).resolve().parent
WAREHOUSE = ROOT / "warehouse"
NAMESPACE = "default"

DEFAULT_USERS = 1_000_000
DEFAULT_TXS = 5_000_000

COUNTRIES = ["US", "UK", "DE", "FR", "JP", "ES", "IT", "BR", "IN", "CA"]

USERS_SCHEMA = Schema(
    NestedField(1, "user_id", LongType(), required=True),
    NestedField(2, "name", StringType()),
    NestedField(3, "email", StringType()),
    NestedField(4, "country", StringType()),
)

TX_SCHEMA = Schema(
    NestedField(1, "tx_id", LongType(), required=True),
    NestedField(2, "from_user", LongType(), required=True),
    NestedField(3, "to_user", LongType(), required=True),
    NestedField(4, "amount", DoubleType()),
    NestedField(5, "timestamp", TimestampType()),
)


def generate_users(n: int, seed: int = 42) -> pa.Table:
    rng = np.random.default_rng(seed)
    user_ids = np.arange(1, n + 1, dtype=np.int64)
    countries = np.array(COUNTRIES)[rng.integers(0, len(COUNTRIES), size=n)]

    # Synthetic but unique per user. List comp on 1M rows takes ~1s.
    names = [f"User_{i:07d}" for i in user_ids]
    emails = [f"user{i}@example.com" for i in user_ids]

    # Derive the PyArrow schema from the Iceberg schema so column nullability
    # matches `required=True` declarations — otherwise iceberg_table.append()
    # rejects the table with a "required vs optional" mismatch.
    return pa.table(
        {
            "user_id": user_ids,
            "name": names,
            "email": emails,
            "country": countries,
        },
        schema=schema_to_pyarrow(USERS_SCHEMA),
    )


def generate_transactions(n_txs: int, n_users: int, seed: int = 43) -> pa.Table:
    rng = np.random.default_rng(seed)
    tx_ids = np.arange(1, n_txs + 1, dtype=np.int64)
    from_user = rng.integers(1, n_users + 1, size=n_txs, dtype=np.int64)
    to_user = rng.integers(1, n_users + 1, size=n_txs, dtype=np.int64)

    # Avoid self-loops: bump any equal target by 1 (wrapping at n_users).
    eq = from_user == to_user
    to_user[eq] = (to_user[eq] % n_users) + 1

    amount = rng.uniform(1.0, 10000.0, size=n_txs).round(2)

    # Spread timestamps uniformly across one year (microsecond precision).
    base = np.datetime64("2025-01-01T00:00:00", "us")
    seconds_in_year = 365 * 24 * 60 * 60
    offsets_us = (
        rng.integers(0, seconds_in_year, size=n_txs) * 1_000_000
    ).astype("timedelta64[us]")
    timestamps = base + offsets_us

    return pa.table(
        {
            "tx_id": tx_ids,
            "from_user": from_user,
            "to_user": to_user,
            "amount": amount,
            "timestamp": timestamps,
        },
        schema=schema_to_pyarrow(TX_SCHEMA),
    )


def get_catalog() -> SqlCatalog:
    WAREHOUSE.mkdir(parents=True, exist_ok=True)
    return SqlCatalog(
        "default",
        **{
            "uri": f"sqlite:///{WAREHOUSE}/catalog.db",
            "warehouse": f"file://{WAREHOUSE}",
        },
    )


def ensure_namespace(catalog: SqlCatalog, namespace: str) -> None:
    try:
        catalog.load_namespace_properties(namespace)
    except NoSuchNamespaceError:
        catalog.create_namespace(namespace)


def reset_table(catalog: SqlCatalog, name: str, schema: Schema):
    full = f"{NAMESPACE}.{name}"
    try:
        catalog.drop_table(full)
    except NoSuchTableError:
        pass
    return catalog.create_table(full, schema=schema)


def write_iceberg(
    catalog: SqlCatalog, name: str, schema: Schema, arrow_table: pa.Table
):
    iceberg_table = reset_table(catalog, name, schema)
    iceberg_table.append(arrow_table)
    return iceberg_table


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic users + transactions into local Iceberg tables."
    )
    parser.add_argument(
        "--users",
        type=int,
        default=DEFAULT_USERS,
        help=f"Number of users to generate (default: {DEFAULT_USERS:,})",
    )
    parser.add_argument(
        "--transactions",
        type=int,
        default=DEFAULT_TXS,
        help=f"Number of transactions to generate (default: {DEFAULT_TXS:,})",
    )
    args = parser.parse_args()

    catalog = get_catalog()
    ensure_namespace(catalog, NAMESPACE)

    print(f"Generating {args.users:,} users...")
    users_table = generate_users(args.users)
    print(f"Generating {args.transactions:,} transactions...")
    txs_table = generate_transactions(args.transactions, args.users)

    print("Writing Iceberg tables...")
    write_iceberg(catalog, "users", USERS_SCHEMA, users_table)
    write_iceberg(catalog, "transactions", TX_SCHEMA, txs_table)

    print(f"\nusers:        {args.users:,} rows")
    print(f"transactions: {args.transactions:,} rows")
    print(f"warehouse:    {WAREHOUSE}")


if __name__ == "__main__":
    main()
