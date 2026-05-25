#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_URL="https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.sql"
DATA="${HERE}/pokec_medium_import.sql"

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"
export PGHOST PGPORT PGUSER PGDATABASE
PSQL=(psql -v ON_ERROR_STOP=1 -X)

if [ ! -f "$DATA" ]; then
    echo ">>> downloading Pokec medium dump (~123 MB)"
    curl -L "$DATASET_URL" -o "$DATA"
fi

echo ">>> creating schema"
"${PSQL[@]}" -f "$HERE/schema.sql"

echo ">>> loading $(wc -l < "$DATA") rows (single transaction)"
"${PSQL[@]}" --single-transaction -f "$DATA" > /dev/null

echo ">>> creating property graph and running queries"
"${PSQL[@]}" -f "$HERE/graph.sql"
