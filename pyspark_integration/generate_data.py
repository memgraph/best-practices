"""Generate sample nodes.csv and edges.csv for the PySpark-Memgraph integration demo."""

import argparse
import csv
import random

LABELS = ["Person", "Company", "Product"]
PERSON_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Heidi"]
COMPANY_NAMES = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne", "Oscorp"]
PRODUCT_NAMES = ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig"]


def generate_nodes(path: str, num_nodes: int) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "label", "name", "age_or_value"])
        for i in range(1, num_nodes + 1):
            label = random.choice(LABELS)
            if label == "Person":
                name = f"{random.choice(PERSON_NAMES)}_{i}"
                extra = random.randint(18, 80)  # age
            elif label == "Company":
                name = f"{random.choice(COMPANY_NAMES)}_{i}"
                extra = random.randint(1000, 1_000_000)  # revenue
            else:
                name = f"{random.choice(PRODUCT_NAMES)}_{i}"
                extra = round(random.uniform(9.99, 999.99), 2)  # price
            writer.writerow([i, label, name, extra])
    print(f"Wrote {num_nodes} nodes to {path}")


def generate_edges(path: str, num_edges: int, num_nodes: int) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "weight"])
        for _ in range(num_edges):
            src = random.randint(1, num_nodes)
            dst = random.randint(1, num_nodes)
            while dst == src:
                dst = random.randint(1, num_nodes)
            weight = round(random.uniform(0.1, 10.0), 2)
            writer.writerow([src, dst, weight])
    print(f"Wrote {num_edges} edges to {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=10_000, help="Number of nodes to generate (default: 10000)")
    parser.add_argument("--edges", type=int, default=50_000, help="Number of edges to generate (default: 50000)")
    parser.add_argument("--nodes-path", default="nodes.csv", help="Output path for nodes CSV (default: nodes.csv)")
    parser.add_argument("--edges-path", default="edges.csv", help="Output path for edges CSV (default: edges.csv)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_nodes(args.nodes_path, args.nodes)
    generate_edges(args.edges_path, args.edges, args.nodes)
