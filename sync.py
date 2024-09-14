import csv
import gzip
import json
import os
from requests import get
import shutil
from subprocess import call
import sys
from urllib.request import urlretrieve
import zipfile

from utils import bytes_to_megabytes, get_all_assets, Timer

# avoid _csv.Error: field larger than field limit (131072)
csv.field_size_limit(sys.maxsize)

skiplist = []

select_asset_ids = []

# grab all assets
limit = 100_000

assets = get_all_assets(limit)

rows = []

for base, asset in assets:
    id = asset["id"]
    name = asset["name"]

    print(f'\n[{id}] checking "{name}"')

    if len(select_asset_ids) >= 1 and id not in select_asset_ids:
        print(f"[{id}] skipping because it's not in the select asset ids")
        continue

    if id in skiplist:
        print(f"[{id}] skipping because it's in skiplist")
        continue

    # skip community assets
    if asset["provenance"] != "OFFICIAL":
        print(f'[{id}] skipping unofficial asset "{name}"')
        continue

    metadata_url = f"{base}/api/views/{id}.json"
    print(f"[{id}] fetching " + metadata_url)
    with Timer(f"[{id}] fetching metadata"):
        metadata = get(metadata_url).json()

    if "error" in metadata:
        if "message" in metadata:
            print(metadata["message"])
            continue

    if "columns" in metadata:
        for column in metadata["columns"]:
            if "cachedContents" in column:
                del column["cachedContents"]

    assetType = metadata["assetType"]
    print(f"[{id}] assetType:", assetType)
    if assetType not in ["dataset", "filter"]:
        print(f"[{id}] skipping because it's not a dataset or filter")
        continue

    dataset_dirpath = f"./data/{id}"
    if not os.path.isdir(dataset_dirpath):
        os.mkdir(dataset_dirpath)
        print(f'[{id}] created dataset directory "{dataset_dirpath}"')

    # save metadata
    metadata_path = os.path.join(dataset_dirpath, f"{id}.metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
        print(f'[{id}] saved metadata to "{metadata_path}"')

    csv_filename = id + ".csv"

    download_csv_path = os.path.join(dataset_dirpath, csv_filename)
    download_url = f"{base}/api/views/{id}/rows.csv?accessType=DOWNLOAD"
    print(f'[{id}] downloading "{name}"')
    with Timer(f"[{id}] retrieving data"):
        try:
            urlretrieve(download_url, download_csv_path)
        except Exception as e:
            # skip this asset if problem downloading
            continue
    print(f'[{id}] downloaded "{name}"')

    size_of_csv = os.path.getsize(download_csv_path)
    print(f"[{id}] size of csv: {size_of_csv}")

    #stat_path = os.path.join(dataset_dirpath, f"{id}.stats.txt")
    #with open(stat_path, "w") as f:
    #    call(["csvstat", download_csv_path], shell=False, stdout=f)

    zip_path = download_csv_path + ".zip"
    with Timer(f"[{id}] zipping"):
        with zipfile.ZipFile(
            zip_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zip:
            zip.write(download_csv_path)
    
    size_of_zip = os.path.getsize(zip_path)
    print(f"[{id}] size of zip: {size_of_zip}")

    gzip_path = download_csv_path + ".gz"
    with Timer(f"[{id}] gzipping"):
        with open(download_csv_path, 'rb') as f_in:
            with gzip.open(gzip_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    size_of_gzip = os.path.getsize(gzip_path)
    print(f"[{id}] size of gzip: {size_of_gzip}")
    
    with Timer(f"[{id}] deleting old csv"):
        os.remove(download_csv_path)

    with Timer(f"[{id}] checking size"):
        included = size_of_zip < 5e7
        if not included:
            print(f"[{id}] removing {zip_path} because it's too large")
            # file is too large for Github (without lfs)
            os.remove(zip_path)

    with Timer(f"[{id}] checking size"):
        included = size_of_gzip < 5e7
        if not included:
            print(f"[{id}] removing {gzip_path} because it's too large")
            # file is too large for Github (without lfs)
            os.remove(gzip_path)    

    rows.append(
        {
            "id": id,
            "name": name,
            "type": assetType,
            "github": included,
            "size_csv": bytes_to_megabytes(size_of_csv),
            "size_zip": bytes_to_megabytes(size_of_zip),
            "url": download_url,
        }
    )

with open("metadata.csv", "w") as f:
    writer = csv.DictWriter(
        f, fieldnames=["id", "name", "type", "github", "size_csv", "size_zip", "url"]
    )
    writer.writeheader()
    writer.writerows(rows)
