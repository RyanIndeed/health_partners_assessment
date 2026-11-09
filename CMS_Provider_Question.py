# Imports
import requests
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import re
import sys


# Constants
URL = "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items"
THEME = "Hospitals"
PROCESSED_IDS_PATH = "./processed_ids.txt" # TODO: Use a simple table for this
LAST_RUN_PATH = "./last_run.txt" # TODO: Programmtically read when this job last ran, via an API or similar
DATE_FORMAT = "%Y-%m-%d"


# Variables
run_date = datetime.now().strftime(DATE_FORMAT)
new_ids = []


# Functions
def get_all_items(endpoint):
    items = requests.get(endpoint)
    return items.json()


def filter_items(items):
    filtered_items = []
    
    processed_ids = _read_processed_ids()
    last_run_date = _read_last_run_date()

    for item in items:
        # Only process records with the correct theme
        if THEME in item["theme"]: # TODO: Find out if all theme values are indeed single-item lists

            # Process new records
            if item["identifier"] not in processed_ids: # TODO: Confirm that the identifier field is actually unique
                filtered_items.append(item)
                new_ids.append(item["identifier"])

            # Process recntly modified records
            elif datetime.strptime(item["modified"], DATE_FORMAT).date() >= last_run_date:
                filtered_items.append(item)

    return filtered_items


def _read_processed_ids():
    with open(PROCESSED_IDS_PATH, "r") as file:
        processed_ids = file.read().splitlines()
    
    print(f"Successfully read {len(processed_ids)} processed IDs")
    return processed_ids


def write_processed_ids(processed_ids):
    with open(PROCESSED_IDS_PATH, "a") as file:
        for id in processed_ids:
            file.write(id + "\n")
    
    print(f"Successfully wrote {len(processed_ids)} processed IDs")
    

def _read_last_run_date():
    with open(LAST_RUN_PATH, "r") as file:
        last_run_string = file.read().strip("\n")
    
    last_run_date = datetime.strptime(last_run_string, DATE_FORMAT).date()

    print(f"Retrieved last run date: {last_run_date}")
    return last_run_date


def write_last_run_date(run_date):
    with open(LAST_RUN_PATH, "w") as file:
        file.write(run_date)

    print(f"Last run date successfully updated to {run_date}")


def download_csv(item):
    # Get CSV file contents
    csv_url = item["distribution"][0]["downloadURL"]
    content = requests.get(csv_url).text
    
    # Format the CSV header row
    header_row = content.split("\n")[0]
    formatted_header_row = _format_header_row(header_row)

    # Replace the header row
    content = content.replace(header_row, formatted_header_row) # TODO: Use Pandas to do this rather than string replacement

    # Write out CSV file
    file_path = item["identifier"] + "_" + csv_url.split("/")[-1]
    with open(file_path, "w") as file:
        file.write(content)
    

def _format_header_row(header_row):
    formatted_column_names = []

    column_names = header_row.split(",")

    for column_name in column_names:
        # Remove special characters
        cleaned_column_name = re.sub(r"[^a-zA-Z0-9 ]", " ", column_name)

        # Convert to snake case
        formatted_column_name = cleaned_column_name.lower().strip().replace(" ", "_")
        formatted_column_names.append(formatted_column_name)

    formatted_header_row = ",".join(formatted_column_names)
    return formatted_header_row

    
# Script

# Get the appropriate JSON items
items = get_all_items(URL)
filtered_items = filter_items(items)

# Check if there are new records
if not filtered_items:
    print("No records to process")
    
else:
    # Process CSVs in parallel
    with ProcessPoolExecutor() as executor:
        for item in filtered_items:
            executor.submit(download_csv, item)

    # Perform final tracking tasks
    write_processed_ids(new_ids)
    write_last_run_date(run_date)
