"""Read Iceberg tables via PyIceberg's local SQL catalog.

Swap the SqlCatalog construction below for `load_catalog("rest", ...)` or
`load_catalog("glue", ...)` to point at a real lake — the rest of the
loader (and iceberg_to_memgraph.py) is unchanged.
"""
from pathlib import Path
from typing import Iterator

from pyiceberg.catalog.sql import SqlCatalog

from .base import Loader

DEFAULT_WAREHOUSE = Path(__file__).resolve().parent.parent / "warehouse"
NAMESPACE = "default"


class PyIcebergLoader(Loader):
    def __init__(
        self, warehouse: Path = DEFAULT_WAREHOUSE, batch_size: int = 10_000
    ) -> None:
        self.batch_size = batch_size
        self.catalog = SqlCatalog(
            "default",
            **{
                "uri": f"sqlite:///{warehouse}/catalog.db",
                "warehouse": f"file://{warehouse}",
            },
        )

    def _scan(self, table_name: str) -> Iterator[list[dict]]:
        table = self.catalog.load_table(f"{NAMESPACE}.{table_name}")
        arrow = table.scan().to_arrow()
        for batch in arrow.to_batches(max_chunksize=self.batch_size):
            yield batch.to_pylist()

    def users(self) -> Iterator[list[dict]]:
        return self._scan("users")

    def transactions(self) -> Iterator[list[dict]]:
        return self._scan("transactions")
