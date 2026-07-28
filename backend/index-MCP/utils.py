import os
import bz2
import shutil
import requests
from pathlib import Path

def clear_directory_pathlib(dir_path):
    path = Path(dir_path)
    if path.exists() and path.is_dir():
        print(f"Leere Ordner: {path}...")
        for item in path.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    else:
        path.mkdir(parents=True, exist_ok=True)

def download_bz2(url, output_dir="."):
    local_filename = Path(output_dir) / url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            f.writelines(r.iter_content(chunk_size=8192))
    return str(local_filename)

def extract_grib_from_bz2(bz2_path, output_dir=None):
    if output_dir:
        filename = os.path.basename(bz2_path).replace(".bz2", "")
        output_path = os.path.join(output_dir, filename)
    else:
        output_path = bz2_path.replace(".bz2", "")
        
    with bz2.open(bz2_path, "rb") as source, open(output_path, "wb") as dest:
        dest.writelines(iter(lambda: source.read(10 * 1024 * 1024), b""))
    return output_path
