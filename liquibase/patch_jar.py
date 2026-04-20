"""
Patch liquibase-neo4j-4.29.2.jar for Memgraph compatibility.

Three changes are made to CONSTANT_Utf8 entries in Neo4jDatabase.class:

1. Version-detection query — hardcode the return to "3.5.0" / "community"
   so liquibase-neo4j routes all DDL to its Neo4j 3.5 code paths, which use
   CREATE CONSTRAINT ON / CREATE INDEX ON syntax that Memgraph supports.
   Edition "community" also skips node-key constraints (not supported by
   Memgraph).

2. Internal unique-constraint DDL — replace with a no-op RETURN.
   Memgraph does not allow DDL inside explicit multi-statement transactions,
   which is how liquibase-neo4j executes its internal schema setup.

3. Internal index DDL — same reason as #2.

Constant pool entries are referenced by index, not by byte offset, so
changing an entry's length is safe and requires no other bytecode changes.
"""

import struct
import sys
import zipfile
import shutil

JAR_PATH = sys.argv[1]
TARGET_CLASS = "liquibase/ext/neo4j/database/Neo4jDatabase.class"

PATCHES = [
    (
        # Hardcode version to "3.5.0" to select the Memgraph-compatible DDL
        # path and "community" to skip enterprise-only node-key constraints.
        b'CALL dbms.components() YIELD name, edition, versions'
        b' WHERE name = "Neo4j Kernel"'
        b' RETURN edition, versions[0] AS version LIMIT 1',
        b"RETURN '3.5.0' AS version, 'community' AS edition",
    ),
    (
        # Internal unique constraint: DDL is not allowed in explicit Memgraph
        # transactions, so replace with a harmless no-op.
        b"CREATE CONSTRAINT ON (n:`%s`) ASSERT n.`%s` IS UNIQUE",
        b"RETURN true",
    ),
    (
        # Internal index creation: same reason.
        b"CREATE INDEX ON :`%s`(%s)",
        b"RETURN true",
    ),
]


def patch_class(data: bytes) -> bytes:
    for old_str, new_str in PATCHES:
        old_entry = b"\x01" + struct.pack(">H", len(old_str)) + old_str
        new_entry = b"\x01" + struct.pack(">H", len(new_str)) + new_str
        if old_entry not in data:
            raise RuntimeError(
                f"Target string not found in class file: {old_str[:60]!r}..."
            )
        data = data.replace(old_entry, new_entry, 1)
        print(f"  Patched: {old_str[:60]!r} -> {new_str!r}")
    return data


tmp_path = JAR_PATH + ".tmp"
with zipfile.ZipFile(JAR_PATH, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        if info.filename == TARGET_CLASS:
            print(f"Found {TARGET_CLASS}")
            data = patch_class(data)
        zout.writestr(info, data)

shutil.move(tmp_path, JAR_PATH)
print("JAR patched successfully.")
