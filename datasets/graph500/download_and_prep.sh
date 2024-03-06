#!/bin/bash

# Define the options using separate arrays
sizes=("small" "medium")
small_option="graph500-scale18-ef16_adj.zip" # Nodes: 174k  Edges: 7,6M
medium_option="graph500-scale21-ef16_adj.zip" # Nodes: 1M Edges: 63M 
large_option="graph500-scale23-ef16_adj.zip" # Nodes: 5M Edges: 259M

# Check if no arguments were passed or if help was requested
if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./download_dataset.sh SIZE"
    echo "Available sizes:"
    for size in "${sizes[@]}"; do
        if [ "$size" == "small" ]; then
            echo "  $size   :   $small_option"
        elif [ "$size" == "medium" ]; then
            echo "  $size   :   $medium_option"
        fi
    done
    exit 0
fi

# Read the option from the size argument
size="$1"

# Check if the size option is valid
valid_option=false
for valid_size in "${sizes[@]}"; do
    if [ "$size" == "$valid_size" ]; then
        valid_option=true
        break
    fi
done

if [ "$valid_option" == false ]; then
    echo "Invalid size option"
    exit 1
fi

# Determine the option based on the size
if [ "$size" == "small" ]; then
    option="$small_option"
elif [ "$size" == "medium" ]; then
    option="$medium_option"
fi

# Make a directory for the size
mkdir -p "$size"
cd "$size"

# Check if the downloaded file with .edges extension is present
if [ -f "${option%.zip}.edges" ]; then
    echo "Downloaded file with .edges extension is present"
else
    echo "Downloaded file with .edges extension is not found"
    # Download the file
    wget https://nrvis.com/download/data/graph500/"$option"
    # Unzip the file
    unzip "$option"
    rm "$option"
    rm readme.html
fi

cd ..

echo "Running node extraction script..."
python3 node_extraction.py "$size"

echo "Running csv conversion script..."
python3 csv_converter.py "$size"

echo "Running csv splitter script..."
python3 csv_splitter.py "$size"
