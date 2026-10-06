import os
import sys
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\chinese-karaoke-kar"
CATALOG_PATH = os.path.join(TARGET_DIR, "chinese_karaoke_catalog.json")

files = [f for f in os.listdir(TARGET_DIR) if f.endswith('.kar')]
print(f"Total downloaded .kar files: {len(files)}")

headers = {'User-Agent': 'Mozilla/5.0'}

def fetch_meta(fname):
    url = f"https://www.karaokeden.com/api/lyrics.php?category=Chinese&file={fname}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return fname, data
    except Exception as e:
        return fname, {"error": str(e)}

catalog = {}
t0 = time.time()
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(fetch_meta, f): f for f in files}
    for idx, fut in enumerate(as_completed(futures)):
        fname, data = fut.result()
        catalog[fname] = data
        if (idx + 1) % 150 == 0 or (idx + 1) == len(files):
            print(f"Metadata progress: {idx+1}/{len(files)} in {time.time()-t0:.1f}s")

with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print(f"Metadata catalog successfully saved to {CATALOG_PATH} with {len(catalog)} songs!")
