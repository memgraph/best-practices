#!/bin/bash

set -e

CONTAINER_NAME="memgraph"
CORE_DIR="cores"
CORE_PATTERN="/tmp/cores/core.%e.%p.%h.%t"
MEMGRAPH_BINARY_PATH="/usr/lib/memgraph/memgraph"

echo "=== Step 1: Set up host for core dumps ==="
sudo mkdir -p "$CORE_DIR"
sudo chmod a+rwx "$CORE_DIR"
echo "$CORE_PATTERN" | sudo tee /proc/sys/kernel/core_pattern

echo "=== Step 2: Install GCC and create crash program inside container ==="
set +e
docker exec -it -u root "$CONTAINER_NAME" bash -c "
  apt update && apt install -y gcc gdb &&
  mkdir -p /tmp/cores &&
  echo '$CORE_PATTERN' > /proc/sys/kernel/core_pattern &&
  cat <<EOF > crash.c
#include <stdlib.h>
int main() {
  int *ptr = NULL;
  *ptr = 42;  // Force SIGSEGV
  return 0;
}
EOF
  gcc -g crash.c -o crash &&
  ulimit -c unlimited &&
  ./crash
"
set -e

echo "=== Step 3: Check for core dump in $CORE_DIR ==="
CORE_FILE=$(ls -t "$CORE_DIR"/core.* 2>/dev/null | head -n 1)

if [[ -f "$CORE_FILE" ]]; then
echo "✅ Found core dump: $CORE_FILE"
echo "=== Step 4: Running gdb to print stack trace and source context ==="
docker exec -i -u root "$CONTAINER_NAME" bash -c "
  gdb -q ./crash /tmp/cores/$(basename "$CORE_FILE") \
      -ex 'bt' \
      -ex 'frame 0' \
      -ex 'list' \
      -ex 'quit'
"
else
  echo "❌ No core dump found in $CORE_DIR"
fi
