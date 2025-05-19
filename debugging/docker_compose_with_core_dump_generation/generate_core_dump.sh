#!/bin/bash

set -e

CONTAINER_NAME="memgraph"

echo "=== Step 1: Set up host for core dumps ==="
sudo mkdir -p cores
sudo chmod a+rwx cores
echo "/tmp/cores/core.%e.%p.%h.%t" | sudo tee /proc/sys/kernel/core_pattern

echo "=== Step 2: Install GCC and create crash program inside container ==="
set +e
docker exec -it -u root "$CONTAINER_NAME" bash -c "
  apt update && apt install -y gcc &&
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

echo "=== Step 3: Check for core dump in /tmp/cores ==="
ls -lh cores || echo 'No core file found — double-check permissions and core pattern.'
