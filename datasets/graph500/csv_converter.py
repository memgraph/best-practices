
import csv
import sys
import os

class Sizes:
    OPTIONS = ["small", "medium", "large"]

def run(size: str):

    FILE_PATH = ""
    if size in Sizes.OPTIONS:
        directory = f"./{size}"
        for file in os.listdir(directory):
            if file.endswith(".edges"):
                FILE_PATH = os.path.join(directory, file)
                break
        if FILE_PATH == "":
            print(f"No .edges file found in {directory}.")
            return
    
    else:
        print("Invalid size argument. Please choose 'small', 'medium', or 'large'.")
        return

    OUTPUT_FILE_NODES = f"./{size}/nodes.csv"
    OUTPUT_FILE_RELATIONSHIPS = f"./{size}/relationships.csv"
    
    nodes_set = set()
    relationship_set = set()
    
    with open(FILE_PATH, "r") as file:
        while True:
            line = file.readline()
            if not line:
                break
            else:
                node_sink, node_source = line.strip().split()  
                nodes_set.add(node_source)
                nodes_set.add(node_sink)
                relationship_set.add((int(node_source), int(node_sink)))

    print("Writing nodes ...")
    print("Nodes: ", len(nodes_set))
    with open(OUTPUT_FILE_NODES, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id"])
        for node in sorted(nodes_set):
            writer.writerow([int(node)])
    
    print("Writing relationships ...")
    print("Relationships: ", len(relationship_set))
    with open(OUTPUT_FILE_RELATIONSHIPS, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["source", "sink"])
        for relationship in sorted(relationship_set):
            writer.writerow([relationship[0], relationship[1]])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid number of arguments. Please provide the size argument.")
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)
