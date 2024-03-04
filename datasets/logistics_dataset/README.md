# How to export data from a graph db into Cypher queries
Format plain will be used which exports plain Cypher without `begin`, `commit` or `await` commands. 

## Export with optimizations (UNWINDs)

This is the default behaviour regarding optimizations. Exports the file by batching with the UNWIND method.

### Export into one file

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20}
})
```

### Export into separate files
```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20},
    separateFiles: true
})
```

The above code generates `export.schema.cypher`, `export.nodes.cypher`, `export.relationships.cypher` and `export.cleanup.cypher` in the `import` folder.

## Export without optimizations (without UNDWINDs)
When `useOptimizations` is set to NONE, only `CREATE` statements will be used. 

### Export into one file

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "NONE"}
})
```

### Export into separate files

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "NONE"},
    separateFiles: true
})
```

The above code generates `export.schema.cypher`, `export.nodes.cypher`, `export.relationships.cypher` and `export.cleanup.cypher` in the `import` folder.

# How to convert Cypher files into Memgraph CYPHERL

If you exported the database into one Cypher file, then copy it onto your local file system and use [n2mg_cypherl.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script to convert the Cypher file into CYPHERL file:

```
./n2mg_cypherl.sh export.cypher export.cypherl
```

If you exported the database into separate Cypher files, then copy it onto your local file system and use [n2mg_separate_files_cypherl.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script to convert the Cypher files into CYPHERL file:

```
./n2mg_separate_files_cypherl.sh export.schema.cypher export.nodes.cypher export.relationships.cypher export.cleanup.cypher export.cypherl
```

If you wish to convert separate Cypher files into separate CYPHERL files, then use [n2mg_separate_files_cypherls.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script:

```
./n2mg_separate_files_cypherls.sh export.schema.cypher export.nodes.cypher export.relationships.cypher export.cleanup.cypher export-schema.cypherl export-nodes.cypherl export-relationships.cypherl export-cleanup.cypherl
```

# How to import CYPHERL into Memgraph

If you're running Memgraph with Docker, copy the CYPHERL files into the Docker container where Memgraph is running:

```
docker cp export.cypherl <container_id>:export.cypherl
```

CYPHERL files can be imported using [mgconsole](https://github.com/memgraph/mgconsole?tab=readme-ov-file#export--import-into-memgraph):

```
cat export.cypherl | mgconsole
```

If you converted the exported files into separate CYPHERL files, make sure to import them in the following order: schema, nodes, relationships and cleanup.

Additional speed improvement can be achieved with the in-memory analytical storage mode, but you should be aware of its [implications](https://memgraph.com/docs/fundamentals/storage-memory-usage#implications). 

The mgconsole offers batched and parallelized import as an experimental feature as well:

```
cat export.cypherl | mgconsole --import-mode=batched-parallel
```

If used in in-memory transactional mode, then [`SerializationError`](https://memgraph.com/docs/help-center/errors/serialization) can be occur due to conflicting transactions. To avoid this, first import nodes, then relationships and make sure your queries don't update the same properties on the node or create the relationships on the same node concurrently. With this experimental feature, it is best to use only MATCH, CREATE and MERGE clauses for now (without UNWINDs).




