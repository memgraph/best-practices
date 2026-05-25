"""Source-backend registry. Add new backends here.

To plug in a new source (e.g. DuckDB, raw Parquet, LOAD CSV):

    1. Implement loaders/<name>.py with a Loader subclass.
    2. Register it in LOADERS below.
    3. Run: python iceberg_to_memgraph.py --source <name>
"""
from .base import Loader
from .duckdb_loader import DuckDBLoader
from .pyiceberg_loader import PyIcebergLoader

LOADERS: dict[str, type[Loader]] = {
    "pyiceberg": PyIcebergLoader,
    "duckdb": DuckDBLoader,
    # "parquet":  ParquetLoader,   # TODO
}


def get_loader(source: str, batch_size: int = 10_000) -> Loader:
    if source not in LOADERS:
        raise ValueError(
            f"Unknown source: {source!r}. Available: {sorted(LOADERS)}"
        )
    return LOADERS[source](batch_size=batch_size)


def available_sources() -> list[str]:
    return sorted(LOADERS)
