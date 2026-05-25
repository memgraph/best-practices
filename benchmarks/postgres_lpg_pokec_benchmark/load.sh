#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PG_DATASET_URL="https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.sql"
MG_DATASET_URL="https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.cypher"
PG_DATA="${HERE}/pokec_medium_import.sql"
MG_DATA="${HERE}/pokec_medium_import.cypher"

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"
export PGHOST PGPORT PGUSER PGDATABASE
PSQL=(psql -v ON_ERROR_STOP=1 -X)

MG_HOST="${MG_HOST:-localhost}"
MG_PORT="${MG_PORT:-7687}"

download() {
    local url="$1"
    local dest="$2"
    if [ -f "$dest" ]; then
        return
    fi
    echo ">>> downloading $url"
    curl -fL --progress-bar "$url" -o "$dest"
}

wait_for_tcp() {
    local host="$1"
    local port="$2"
    local name="$3"
    echo ">>> waiting for $name at $host:$port"
    for _ in $(seq 1 60); do
        if (exec 3<>"/dev/tcp/$host/$port") >/dev/null 2>&1; then
            exec 3<&- 3>&-
            echo "    ready"
            return 0
        fi
        sleep 1
    done
    echo "!!! $name at $host:$port not reachable after 60s" >&2
    return 1
}

# ─── Postgres ────────────────────────────────────────────────────────────────
wait_for_tcp "$PGHOST" "$PGPORT" "Postgres"
download "$PG_DATASET_URL" "$PG_DATA"

echo ">>> applying Postgres schema"
"${PSQL[@]}" -f "$HERE/schema.sql"

echo ">>> loading $(wc -l < "$PG_DATA") rows into Postgres (single transaction)"
"${PSQL[@]}" --single-transaction -f "$PG_DATA" >/dev/null

echo ">>> creating Postgres property graph"
"${PSQL[@]}" -f "$HERE/graph.sql"

# ─── Memgraph ────────────────────────────────────────────────────────────────
wait_for_tcp "$MG_HOST" "$MG_PORT" "Memgraph"
download "$MG_DATASET_URL" "$MG_DATA"

if ! command -v mgconsole >/dev/null 2>&1; then
    echo "!!! mgconsole not found on PATH" >&2
    echo "    install: https://memgraph.com/docs/getting-started/install-memgraph/mgconsole" >&2
    exit 1
fi

MGCONSOLE=(mgconsole --host "$MG_HOST" --port "$MG_PORT")

echo ">>> wiping Memgraph and creating indexes"
"${MGCONSOLE[@]}" <<'EOF' >/dev/null
STORAGE MODE IN_MEMORY_ANALYTICAL;
DROP GRAPH;
CREATE INDEX ON :User;
CREATE INDEX ON :User(id);
EOF

echo ">>> loading $(wc -l < "$MG_DATA") cypher statements into Memgraph"
"${MGCONSOLE[@]}" < "$MG_DATA" >/dev/null

"${MGCONSOLE[@]}" <<'EOF' >/dev/null
STORAGE MODE IN_MEMORY_TRANSACTIONAL;
EOF

echo ">>> done"
