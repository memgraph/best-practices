# How to import data into other graph db

## 1. Copy CSV files to a running Docker container

Copy all the files from the [csv folder](https://github.com/memgraph/best-practices/tree/main/datasets/logistics_dataset/100K/csv) into a Docker container where a graph db is running. 

## 2. Create indexes

```
CREATE INDEX driver_id FOR (n:Driver) ON (n.id);
CREATE INDEX order_id FOR (n:Order) ON (n.id);
CREATE INDEX location_id FOR (n:Location) ON (n.id);
```

## 3. Import the dataset using the LOAD CSV clause

### Import nodes

`Driver` nodes:
```
LOAD CSV WITH HEADERS FROM “file:///node_driver_data.csv” AS row
CREATE (p:Driver {id: row.id, name: row.name, license_plate: row.licence_plate, status: row.status})
```

`Location` nodes:
```
LOAD CSV WITH HEADERS FROM “file:///node_location_data.csv” AS row
CREATE (p:Location {id: row.id, name: row.name, city: row.city, zipcode: row.zipcode});
```

`Order` nodes:
```
LOAD CSV WITH HEADERS FROM “file:///node_order_data.csv” AS row
CREATE (p:Order {id: row.id, status: row.status, order_id: row.order_id, product: row.product, quantity: row.quantity});
```

### Import relationships

`DRIVES` relationships:
```
:auto LOAD CSV WITH HEADERS FROM "file:///edge_drives_data.csv" AS row
CALL {
 WITH row
MATCH (p1:Driver {id: row.id})
MATCH (p2:Location {id: row.to_id})
CREATE (p1)-[f:DRIVES]->(p2)
} IN TRANSACTIONS OF 10 ROWS
```

`ASSIGNED_TO` relationships:
```
:auto LOAD CSV WITH HEADERS FROM "file:///edge_assigned_to_data.csv" AS row
CALL {
 WITH row
MATCH (p1:Order {id: row.id})
MATCH (p2:Driver {id: row.to_id})
CREATE (p1)-[f:ASSIGNED_TO]->(p2)
} IN TRANSACTIONS OF 10 ROWS
```

`BELONGS_TO` relationships:
```
:auto LOAD CSV WITH HEADERS FROM "file:///edge_belongs_to_data.csv" AS row
CALL {
 WITH row
MATCH (p1:Order {id: row.id})
MATCH (p2:Location {id: row.to_id})
CREATE (p1)-[f:BELONGS_TO]->(p2)
} IN TRANSACTIONS OF 10 ROWS
```

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

Copy the obtained Cypher files onto your local file system and use [n2mg_cypherl.sh](https://github.com/memgraph/memgraph/blob/master/import/n2mg_cypherl.sh) script to convert the Cypher files into CYPHERL files:

```
./n2mg_cypherl.sh export.cypher export.cypherl
```

