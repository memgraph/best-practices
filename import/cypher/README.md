Cypher queries that are being imported in Memgraph can be generated dynamically in your code, similar to how it's done in the examples in the [`neo4jpy`](./neo4jpy/) and [`pymgclient`](./pymgclient/) folders with the [`graph500`](../../datasets/graph500/) dataset. 

Suppose you are using a database that allows you to [export data into Cypher queries](#how-to-export-data-from-another-graph-db-into-cypher-queries). In that case, you don't have to generate Cypher queries dynamically, but you can [import them directly into Memgraph](#how-to-import-cypherl-into-memgraph). 

For the **best import speed** of large datasets, export the data into [separate Cypher files in batches](#export-into-separate-files) (with `UNWIND` clauses used) representing schema, nodes, relationships and cleanup and import nodes and then relationships concurrently. Examples on how to do that can be found under [`neo4jpy`](./neo4jpy/) and [`pymgclient`](./pymgclient/) folders. That approach is not straightforward because it requires some coding on your side. 

The most **straightforward approach**, not suitable for large scale, is to export data into one Cypher file and [import it into Memgraph](#how-to-import-cypherl-into-memgraph) via mgconsole or Memgraph Lab. 

# How to export data from another graph db into Cypher queries

When exporting data from another graph db into Cypher queries, use `plain` format, which exports plain Cypher without `begin`, `commit` or `await` commands. 

## Export with optimizations (`UNWIND`s)

This is the default behavior regarding optimizations. Exports the file by batching with the `UNWIND` method.

### Export into one file

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20}
})
```

To import Cypher file into Memgraph, first [convert it](#how-to-convert-cypher-files-into-memgraph-cypherl).

### Export into separate files
```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20},
    separateFiles: true
})
```

The above code generates `export.schema.cypher`, `export.nodes.cypher`, `export.relationships.cypher` and `export.cleanup.cypher` in the `import` folder. To import Cypher files into Memgraph, first [convert them](#how-to-convert-cypher-files-into-memgraph-cypherl).

## Export without optimizations (without `UNDWIND`s)
When `useOptimizations` is set to NONE, only `CREATE` statements will be used. 

### Export into one file

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "NONE"}
})
```
To import Cypher file into Memgraph, first [convert it](#how-to-convert-cypher-files-into-memgraph-cypherl).

### Export into separate files

```
CALL apoc.export.cypher.all("export.cypher", {
    format: "plain",
    useOptimizations: {type: "NONE"},
    separateFiles: true
})
```

The above code generates `export.schema.cypher`, `export.nodes.cypher`, `export.relationships.cypher` and `export.cleanup.cypher` in the `import` folder. To import Cypher files into Memgraph, first [convert them](#how-to-convert-cypher-files-into-memgraph-cypherl).

# How to convert Cypher files into Memgraph CYPHERL

If you exported the database into **one Cypher file**, then copy it onto your local file system and use [n2mg_cypherl.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script to convert the Cypher file into `CYPHERL file:

```
./n2mg_cypherl.sh export.cypher export.cypherl
```

If you exported the database into **separate Cypher files**, then copy it onto your local file system and use [n2mg_separate_files_cypherl.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script to convert the Cypher files into CYPHERL file:

```
./n2mg_separate_files_cypherl.sh export.schema.cypher export.nodes.cypher export.relationships.cypher export.cleanup.cypher export.cypherl
```

If you wish to convert **separate Cypher files into separate CYPHERL files**, then use [n2mg_separate_files_cypherls.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script:

```
./n2mg_separate_files_cypherls.sh export.schema.cypher export.nodes.cypher export.relationships.cypher export.cleanup.cypher export-schema.cypherl export-nodes.cypherl export-relationships.cypherl export-cleanup.cypherl
```

# How to import CYPHERL into Memgraph

There are a couple of approaches to importing CYPHERL into Memgraph:
1. [via mgconsole](https://github.com/memgraph/mgconsole?tab=readme-ov-file#export--import-into-memgraph)
2. [via Memgraph Lab](https://memgraph.com/docs/data-migration/csv#csv-file-import-in-memgraph-lab)
3. via driver


To import via mgconsole or driver, copy the CYPHERL file(s) into the Docker container where Memgraph is running:

```
docker cp export.cypherl <container_id>:export.cypherl
```

CYPHERL files can be imported using [mgconsole](https://github.com/memgraph/mgconsole?tab=readme-ov-file#export--import-into-memgraph):

```
cat export.cypherl | mgconsole
```

If you converted the exported files into separate CYPHERL files, make sure to import them in the following order: schema, nodes, relationships and cleanup.

To lower memory usage during import, use in-memory analytical storage mode. Still, you should be aware of its [implications](https://memgraph.com/docs/fundamentals/storage-memory-usage#implications). 

If you import a CYPHERL file via driver concurrently in the in-memory transactional mode, queries updating the same graph objects can run concurrently. Such concurrent transactions are considered conflicting, leading to the [`SerializationError`](https://memgraph.com/docs/help-center/errors/serialization). Make sure you handle such errors and retry transactions that fail due to that error. If you first import nodes and then relationships concurrently, you'll experience fewer `SerializationErrors`. With the in-memory analytical storage mode, you won't experience `SerializationErrors`, but you lose the ACID properties of the database.


