"""
Load nodes.csv and edges.csv into Memgraph via local PySpark 3.4 + Neo4j Spark Connector.

This uses a local Spark session with the Neo4j Spark Connector JAR to read
CSVs as DataFrames and write them into Memgraph over Bolt.

Admin operations (clear, indexes, verify) use the neo4j Python driver directly,
since the Spark Connector only supports read-only queries.

Usage:
    python csv_to_memgraph.py [nodes.csv] [edges.csv]

Prerequisites:
    - Java 11+ installed (for Spark)
    - pip install -r requirements.txt
    - Memgraph running (docker compose up -d from parent directory)
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from neo4j import GraphDatabase
from pyspark.sql import SparkSession

MG_URI = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
NEO4J_FORMAT = "org.neo4j.spark.DataSource"

# Neo4j Spark Connector 5.3.2 — works with Spark 3.4+
NEO4J_SPARK_JAR = "org.neo4j:neo4j-connector-apache-spark_2.12:5.4.0_for_spark_3"


def get_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("csv-to-memgraph-spark34")
        .master("local[*]")
        .config("spark.jars.packages", NEO4J_SPARK_JAR)
        .getOrCreate()
    )


def get_driver():
    return GraphDatabase.driver(MG_URI, auth=("", ""))


def clear_memgraph(driver) -> None:
    """Delete all nodes and edges in Memgraph."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("Cleared existing data.")


def create_indexes(driver) -> None:
    """Create label indexes and property indexes on node id."""
    with driver.session() as session:
        for label in ["Person", "Company", "Product"]:
            session.run(f"CREATE INDEX ON :{label}")
            session.run(f"CREATE INDEX ON :{label}(id)")
    print("Indexes created.")


def write_nodes(spark, csv_path: str) -> None:
    """Read nodes CSV and write to Memgraph, one label at a time."""
    nodes_df = spark.read.csv(csv_path, header=True, inferSchema=True)
    total = nodes_df.count()
    print(f"Read {total} nodes from {csv_path}")

    for label in ["Person", "Company", "Product"]:
        label_df = nodes_df.filter(nodes_df.label == label).drop("label")
        count = label_df.count()

        (
            label_df.write.format(NEO4J_FORMAT)
            .mode("Append")
            .option("url", MG_URI)
            .option("authentication.type", "none")
            .option("labels", f":{label}")
            .option("node.keys", "id")
            .save()
        )
        print(f"  {label}: {count} nodes")


def write_edges(spark, nodes_csv_path: str, edges_csv_path: str) -> None:
    """Read edges CSV and write to Memgraph via the Spark Connector.

    The connector requires explicit source/target labels, so we join edges with
    nodes to resolve the label for each endpoint, then write per
    (source_label, target_label) combination.
    """
    edges_df = spark.read.csv(edges_csv_path, header=True, inferSchema=True)
    nodes_df = spark.read.csv(nodes_csv_path, header=True, inferSchema=True).select("id", "label")

    total = edges_df.count()
    print(f"Read {total} edges from {edges_csv_path}")

    # Join to resolve source and target labels
    src_nodes = nodes_df.withColumnRenamed("id", "src_id").withColumnRenamed("label", "src_label")
    tgt_nodes = nodes_df.withColumnRenamed("id", "tgt_id").withColumnRenamed("label", "tgt_label")

    enriched = (
        edges_df
        .join(src_nodes, edges_df.source == src_nodes.src_id)
        .join(tgt_nodes, edges_df.target == tgt_nodes.tgt_id)
        .drop("src_id", "tgt_id")
    )

    # Write per (src_label, tgt_label) combo since the connector requires labels
    combos = enriched.select("src_label", "tgt_label").distinct().collect()

    # Cache the enriched DataFrame since multiple threads will read from it
    enriched.cache()

    def write_combo(src_label: str, tgt_label: str) -> str:
        subset = (
            enriched
            .filter(
                (enriched.src_label == src_label)
                & (enriched.tgt_label == tgt_label)
            )
            .withColumnRenamed("source", "source.id")
            .withColumnRenamed("target", "target.id")
            .select("`source.id`", "`target.id`", "weight")
        )
        count = subset.count()

        (
            subset.write.format(NEO4J_FORMAT)
            .mode("Append")
            .option("url", MG_URI)
            .option("authentication.type", "none")
            .option("relationship", "CONNECTED_TO")
            .option("relationship.save.strategy", "keys")
            .option("relationship.source.save.mode", "Match")
            .option("relationship.source.labels", f":{src_label}")
            .option("relationship.source.node.keys", "source.id:id")
            .option("relationship.target.save.mode", "Match")
            .option("relationship.target.labels", f":{tgt_label}")
            .option("relationship.target.node.keys", "target.id:id")
            .save()
        )
        return f"  CONNECTED_TO ({src_label} -> {tgt_label}): {count} edges"

    with ThreadPoolExecutor(max_workers=len(combos)) as pool:
        futures = {
            pool.submit(write_combo, combo["src_label"], combo["tgt_label"]): combo
            for combo in combos
        }
        for future in as_completed(futures):
            print(future.result())

    enriched.unpersist()


def verify(driver) -> None:
    """Quick count check."""
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
        edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
    print(f"\nVerification: {node_count} nodes, {edge_count} edges in Memgraph.")


def main() -> None:
    nodes_csv = sys.argv[1] if len(sys.argv) > 1 else "nodes.csv"
    edges_csv = sys.argv[2] if len(sys.argv) > 2 else "edges.csv"

    spark = get_spark()
    driver = get_driver()

    clear_memgraph(driver)
    create_indexes(driver)

    print(f"\nLoading nodes from {nodes_csv} ...")
    write_nodes(spark, nodes_csv)

    print(f"\nLoading edges from {edges_csv} ...")
    write_edges(spark, nodes_csv, edges_csv)

    verify(driver)

    driver.close()
    spark.stop()


if __name__ == "__main__":
    main()
