import csv
import sys
import os


class Sizes:
    OPTIONS = ["small", "medium", "large"]


def run(size: str):

    file_nodes = ""
    file_edges = ""
    if size in Sizes.OPTIONS:
        directory = f"./{size}"
        for file in os.listdir(directory):
            if file.endswith(".edges"):
                file_edges = os.path.join(directory, file)
            elif file.endswith(".nodes"):
                file_nodes = os.path.join(directory, file)
        if file_nodes == "" or file_edges == "":
            print(f"No .edges or .nodes file found in {directory}.")
            return

    else:
        print("Invalid size argument. Please choose 'small', 'medium', or 'large'.")
        return

    OUTPUT_FILE_NODES = f"./{size}/nodes.csv"
    OUTPUT_FILE_RELATIONSHIPS = f"./{size}/relationships.csv"

    print("Converting nodes ...")
    nodes = []
    with open(file_nodes, "r") as file:
        with open(OUTPUT_FILE_NODES, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id"])
            lines = file.readlines()
            for line in lines:
                writer.writerow([int(line.strip())])

    print("Converting edges ...")
    edges = []
    with open(file_edges, "r") as file:
        with open(OUTPUT_FILE_RELATIONSHIPS, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["source", "sink"])
            lines = file.readlines()
            for line in lines:
                node_sink, node_source = line.strip().split()
                writer.writerow([int(node_sink), int(node_source)])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid number of arguments. Please provide the size argument.")
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)
