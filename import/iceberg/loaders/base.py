"""Common interface every source backend must implement.

The point of this abstraction is that iceberg_to_memgraph.py is identical
regardless of where the data is read from — Iceberg via PyIceberg, Iceberg
via DuckDB, raw Parquet, CSV, etc. Each backend yields batches of plain
dicts; the writer turns them into Cypher.
"""
from abc import ABC, abstractmethod
from typing import Iterator


class Loader(ABC):
    """Yield users and transactions as batches of dicts.

    Keep the dict keys aligned with the Cypher in iceberg_to_memgraph.py:
        users:        user_id, name, email, country
        transactions: tx_id, from_user, to_user, amount, timestamp
    """

    @abstractmethod
    def users(self) -> Iterator[list[dict]]: ...

    @abstractmethod
    def transactions(self) -> Iterator[list[dict]]: ...
