#!/bin/bash

#TODO(antejavor): Add more options for different sizes

# Define the array of options
declare -A options=(
    ["small"]="graph500-scale18-ef16_adj.zip"
    ["medium"]="graph500-scale21-ef16_adj.zip"
)

# Check if no arguments were passed or if help was requested
if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./download_dataset.sh SIZE"
    echo "Available sizes:"
    for size in "${!options[@]}"; do
        echo "  $size   :   ${options[$size]}" 
    done
    exit 0
fi

# Read the option from the size argument
size="$1"

# Check if the size is a valid option
if [[ ${options[$size]+_} ]]; then
    option="${options[$size]}"
else
    echo "Invalid size option"
    exit 1
fi

# Make a  directory for the size
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
