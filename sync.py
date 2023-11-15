import csv
import os
from requests import get
import sys
from urllib.request import urlretrieve
from zipfile import ZipFile

from utils import get_all_assets, Timer

# avoid _csv.Error: field larger than field limit (131072)
csv.field_size_limit(sys.maxsize)

skiplist = []

select_asset_ids = []

# grab all assets
limit = 1000

assets = get_all_assets(limit)

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

    # print("met:", metadata)
    if metadata["assetType"] not in ["dataset", "filter"]:
        print(f"[{id}] skipping because it's not a dataset or filter")
        continue              


    download_path = f"./data/{id}.csv"
    download_url = f"{base}/api/views/{id}/rows.csv?accessType=DOWNLOAD"
    print(f'[{id}] downloading "{name}"')
    with Timer(f"[{id}] retrieving data"):
      try:
        urlretrieve(download_url, download_path)
      except Exception as e:
         # skip this asset if problem downloading
         continue
    print(f'[{id}] downloaded "{name}"')

    zip_path = download_path + '.zip'
    with Timer(f"[{id}] zipping"):
      with ZipFile(zip_path, 'w') as zip:
        zip.write(download_path)

    with Timer(f"[{id}] deleting old csv"):
      os.remove(download_path)

    with Timer(f"[{id}] checking size"):
      size = os.path.getsize(zip_path)
      if size >= 5e+7:
        print(f"[{id}] removing {zip_path} because it's too large")
        # file is too large for Github (without lfs)
        os.remove(zip_path)
