import os
import json

f = open("./export_list.md", "w")

# create table header
table_header = "|four_by_four|dataset_name|dataset_link|duck_db|" + "\n"
f.write(table_header)
spacer = "| ----------- | ----------- |------------|-----------|"
f.write(spacer)
# get all the names from the files
def extract_name_id_from_json(file_path):
    with open(file_path, 'r', encoding="utf8") as json_file:
        data = json.load(json_file)
        name = data.get('name')
        id = data.get('id')
        return name, id

def traverse_directory(directory_path):
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                name, id = extract_name_id_from_json(file_path)
                link = f"https://raw.githubusercontent.com/officeofperformancemanagement/chattadata-exports/main/data/{id}/{id}.csv.zip"
                duckdb_link=f"https://shell.duckdb.org/#queries=v0,CREATE-TABLE-dataset-AS-SELECT-*-FROM-'https%3A%2F%2Fwww.chattadata.org%2Fapi%2Fviews%2F{id.replace('-','%20')}%2Frows.csv%3FaccessType%3DDOWNLOAD'~,Describe-dataset~"
                f.write (f"\n|{id}|{name}|[Link]({link})|[DuckDB]({duckdb_link})|")
directory_path = "./data"
traverse_directory(directory_path)
print("All good :)")

f.close()
