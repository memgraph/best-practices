"""
Monitor Memgraph memory usage relative to the license/allocation limit.

Uses SHOW STORAGE INFO to track memory_tracked (the license-enforced value)
and compares it against allocation_limit.

Usage:
    python monitor_memory.py                          # Poll every 30s, warn at 80%
    python monitor_memory.py --interval 10            # Poll every 10s
    python monitor_memory.py --warn-threshold 0.90    # Warn at 90%
    python monitor_memory.py --once                   # Single check, no polling
"""

import argparse
import re
import sys
import time
from datetime import datetime

from gqlalchemy import Memgraph

# Regex to parse human-readable sizes like "12.45GiB", "512.00MiB", etc.
SIZE_PATTERN = re.compile(r"([\d.]+)\s*(B|KiB|MiB|GiB|TiB)")

SIZE_UNITS_TO_BYTES = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
}


def parse_size_to_bytes(value):
    """Parse a human-readable size string (e.g. '12.45GiB') to bytes."""
    if isinstance(value, (int, float)):
        return float(value)
    match = SIZE_PATTERN.match(str(value).strip())
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2)
    return number * SIZE_UNITS_TO_BYTES[unit]


def format_gib(bytes_value):
    """Format bytes as GiB with 2 decimal places."""
    if bytes_value is None:
        return "N/A"
    return f"{bytes_value / SIZE_UNITS_TO_BYTES['GiB']:.2f} GiB"


def get_storage_info(memgraph):
    """Fetch SHOW STORAGE INFO and return as a dict."""
    result = memgraph.execute_and_fetch("SHOW STORAGE INFO")
    info = {}
    for row in result:
        key = row.get("storage info")
        value = row.get("value")
        if key:
            info[key] = value
    return info


def check_memory(memgraph, warn_threshold):
    """Check memory usage and print status. Returns True if above warning threshold."""
    info = get_storage_info(memgraph)

    memory_tracked = parse_size_to_bytes(info.get("memory_tracked", 0))
    allocation_limit = parse_size_to_bytes(info.get("allocation_limit", 0))
    graph_memory = parse_size_to_bytes(info.get("graph_memory_tracked", 0))
    vector_memory = parse_size_to_bytes(info.get("vector_index_memory_tracked", 0))
    memory_res = parse_size_to_bytes(info.get("memory_res", 0))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if allocation_limit and allocation_limit > 0:
        usage_pct = memory_tracked / allocation_limit
        if usage_pct >= warn_threshold:
            print(
                f"[{timestamp}] WARNING: Memory at {usage_pct:.1%} of limit! "
                f"{format_gib(memory_tracked)} / {format_gib(allocation_limit)}"
            )
            return True
        else:
            print(
                f"[{timestamp}] Memory: {format_gib(memory_tracked)} / {format_gib(allocation_limit)} ({usage_pct:.1%}) "
                f"| Graph: {format_gib(graph_memory)} "
                f"| Vector: {format_gib(vector_memory)} "
                f"| Res: {format_gib(memory_res)}"
            )
    else:
        print(
            f"[{timestamp}] Memory tracked: {format_gib(memory_tracked)} "
            f"(no allocation limit detected)"
        )

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Memgraph memory usage relative to the license limit."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Memgraph host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7687, help="Memgraph port (default: 7687)")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (default: 30)")
    parser.add_argument("--warn-threshold", type=float, default=0.80, help="Warning threshold as fraction (default: 0.80)")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit")
    args = parser.parse_args()

    memgraph = Memgraph(host=args.host, port=args.port)

    print(f"Connecting to Memgraph at {args.host}:{args.port}")
    print(f"Warning threshold: {args.warn_threshold:.0%} of allocation_limit")

    if args.once:
        check_memory(memgraph, args.warn_threshold)
        return

    print(f"Polling every {args.interval}s (Ctrl+C to stop)\n")
    try:
        while True:
            check_memory(memgraph, args.warn_threshold)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()
