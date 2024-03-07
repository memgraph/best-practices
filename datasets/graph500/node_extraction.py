
import sys
import os

class Sizes:
    OPTIONS = ["small", "medium", "large"]


def run(size: str):
    file_path = ""
    if size in Sizes.OPTIONS:
        directory = f"./{size}"
        for file in os.listdir(directory):
            if file.endswith(".edges"):
                file_path = os.path.join(directory, file)
                break
        if file_path == "":
            print(f"No .edges file found in {directory}.")
            return
    
    else:
        print("Invalid size argument. Please choose 'small', 'medium', or 'large'.")
        return

    with open(file_path, "r") as file:
        lines = file.readlines()

    nodes = set()

    for line in lines:
        node1, node2 = line.strip().split()
    
        nodes.add(node1)
        nodes.add(node2)

    file_path = file_path[:-6]


    with open(file_path + ".nodes", "w") as file:
        for node in sorted(nodes):
            file.write(node + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node_extraction.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)

