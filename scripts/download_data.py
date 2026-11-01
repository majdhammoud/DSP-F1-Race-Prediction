"""Download the Kaggle "Formula One Data 2000-2024" dataset (no account needed).

Uses only the Python standard library. Run ONCE before prepare_data_and_model.py:

    python scripts/download_data.py [target_dir]

Downloads the dataset zip and extracts the CSVs into target_dir
(default: kaggle_data/ in the current directory).
"""

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "henriquerezermosqur/formula-one-data-2000-2024"
)


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "kaggle_data")
    target.mkdir(parents=True, exist_ok=True)

    print(f"downloading {URL} ...")
    with urllib.request.urlopen(URL, timeout=120) as resp:
        payload = resp.read()
    print(f"downloaded {len(payload) / 1e6:.1f} MB")

    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        zf.extractall(target, members=names)
    print(f"extracted {len(names)} CSVs into {target}/:")
    for n in sorted(names):
        print(f"  {n}")


if __name__ == "__main__":
    main()
