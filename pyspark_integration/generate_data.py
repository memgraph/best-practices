"""Generate sample nodes.csv and edges.csv for the PySpark-Memgraph integration demo."""

import csv
import random

NUM_NODES = 10_000
NUM_EDGES = 50_000

LABELS = ["Person", "Company", "Product"]
PERSON_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Heidi"]
COMPANY_NAMES = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne", "Oscorp"]
PRODUCT_NAMES = ["Widget", "Gadget", "Gizmo", "Doohickey", "Thingamajig"]


def generate_nodes(path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "label", "name", "age_or_value"])
        for i in range(1, NUM_NODES + 1):
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
    print(f"Wrote {NUM_NODES} nodes to {path}")


def generate_edges(path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "weight"])
        for _ in range(NUM_EDGES):
            src = random.randint(1, NUM_NODES)
            dst = random.randint(1, NUM_NODES)
            while dst == src:
                dst = random.randint(1, NUM_NODES)
            weight = round(random.uniform(0.1, 10.0), 2)
            writer.writerow([src, dst, weight])
    print(f"Wrote {NUM_EDGES} edges to {path}")


if __name__ == "__main__":
    generate_nodes("nodes.csv")
    generate_edges("edges.csv")
