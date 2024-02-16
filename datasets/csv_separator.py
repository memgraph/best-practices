import pandas as pd
import os

# Script that separates an input .csv file into separate .csv files based on the label and relationship type

def create_csv_files(input_csv):
    df = pd.read_csv(input_csv)

    output_directory = "output_files"
    os.makedirs(output_directory, exist_ok=True)

    empty_rows = df[df['_labels'].isna() & df['_type'].isna()]

    empty_file_path = os.path.join(output_directory, "empty_labels.csv")
    empty_rows.to_csv(empty_file_path, index=False)

    # Iterate over unique values in the '_labels' column
    for label_value in df['_labels'].unique():
        if pd.notna(label_value):  # Check for NaN
            # Filter rows based on the '_labels' column value
            label_rows = df[df['_labels'] == label_value]

            sanitized_label_value = str(label_value).replace(':', '')

            # Write the filtered rows to a CSV file
            label_file_path = os.path.join(output_directory, f"{sanitized_label_value}_nodes.csv")
            label_rows.to_csv(label_file_path, index=False)

    # Iterate over unique values in the '_type' column
    for type_value in df['_type'].unique():
        if pd.notna(type_value):  # Check for NaN
            # Filter rows based on the '_type' column value
            type_rows = df[df['_type'] == type_value]

            sanitized_type_value = str(type_value).replace(':', '_')

            # Write the filtered rows to a CSV file
            type_file_path = os.path.join(output_directory, f"{sanitized_type_value}_edges.csv")
            type_rows.to_csv(type_file_path, index=False)

if __name__ == "__main__":
    input_csv_file = "your_input_file.csv" #Change value to your input csv file
    create_csv_files(input_csv_file)
