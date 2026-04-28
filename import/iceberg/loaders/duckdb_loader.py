"""Read Iceberg tables via DuckDB's iceberg extension.

PyIceberg is used only to resolve the latest metadata.json location from
the catalog. The actual table scan is performed by DuckDB's vectorized
engine — typically faster than PyIceberg's pure-Python scan on larger
tables, and a useful A/B against the pyiceberg backend.
"""
from pathlib import Path
from typing import Iterator

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

from .base import Loader

DEFAULT_WAREHOUSE = Path(__file__).resolve().parent.parent / "warehouse"
NAMESPACE = "default"


class DuckDBLoader(Loader):
    def __init__(
        self,
        warehouse: Path = DEFAULT_WAREHOUSE,
        batch_size: int = 10_000,
    ) -> None:
        self.batch_size = batch_size
        self.catalog = SqlCatalog(
            "default",
            **{
                "uri": f"sqlite:///{warehouse}/catalog.db",
                "warehouse": f"file://{warehouse}",
            },
        )
        # The iceberg extension is community-maintained and not bundled with
        # DuckDB; INSTALL is idempotent so it's safe on every run.
        self.conn = duckdb.connect()
        self.conn.execute("INSTALL iceberg")
        self.conn.execute("LOAD iceberg")

    def _metadata_path(self, table_name: str) -> str:
        # PyIceberg returns "file:///..." which DuckDB on the local FS reads
        # fine without the scheme prefix.
        loc = self.catalog.load_table(
            f"{NAMESPACE}.{table_name}"
        ).metadata_location
        return loc[len("file://") :] if loc.startswith("file://") else loc

    def _scan(self, table_name: str) -> Iterator[list[dict]]:
        path = self._metadata_path(table_name)
        arrow = self.conn.execute(
            "SELECT * FROM iceberg_scan(?)", [path]
        ).fetch_arrow_table()
        for batch in arrow.to_batches(max_chunksize=self.batch_size):
            yield batch.to_pylist()

    def users(self) -> Iterator[list[dict]]:
        return self._scan("users")

    def transactions(self) -> Iterator[list[dict]]:
        return self._scan("transactions")
