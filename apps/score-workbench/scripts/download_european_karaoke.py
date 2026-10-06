import os
import sys
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

BASE_TARGET = r"K:\MusicSearch\data\global-pop-midi\european-karaoke-kar"
os.makedirs(BASE_TARGET, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0'}

COUNTRY_CATEGORIES = {
    'france': ['Francais', 'Francais-2', 'Francais-3'],
    'italy': ['Italian', 'Italian-2'],
    'spain': ['Spanish', 'Spanish-2', 'Spanish-3', 'Spanish-4'],
    'portugal': ['Portugese', 'Portugese-2'],
    'netherlands': ['Nederland', 'Nederland-2'],
    'germany': ['German']
}

all_tasks = []
print("Fetching European karaoke song lists from KaraokeDen...")
for country, cats in COUNTRY_CATEGORIES.items():
    c_dir = os.path.join(BASE_TARGET, country)
    os.makedirs(c_dir, exist_ok=True)
    for cat in cats:
        url = f"https://www.karaokeden.com/api/browse.php?category={cat}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                files = data.get('files', [])
                print(f"  [{country}] {cat}: {len(files)} files")
                for f in files:
                    all_tasks.append((country, cat, f))
        except Exception as e:
            print(f"Error fetching {cat}: {e}")

print(f"Total European songs to download: {len(all_tasks)}")

def download_file(item):
    country, cat, fname = item
    safe_name = f"{cat}_{fname}"
    dest_path = os.path.join(BASE_TARGET, country, safe_name)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True, safe_name, "cached"
    
    url = f"https://www.karaokeden.com/api/download.php?category={cat}&file={urllib.parse.quote(fname)}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
        with open(dest_path, 'wb') as f:
            f.write(content)
        return True, safe_name, len(content)
    except Exception as e:
        return False, safe_name, str(e)

print(f"Downloading {len(all_tasks)} European .kar files with 16 workers...")
t0 = time.time()
success = 0
failed = 0

with ThreadPoolExecutor(max_workers=16) as executor:
    futures = {executor.submit(download_file, item): item for item in all_tasks}
    for idx, fut in enumerate(as_completed(futures)):
        ok, sname, res = fut.result()
        if ok:
            success += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"Warning {sname}: {res}")
        if (idx + 1) % 1000 == 0 or (idx + 1) == len(all_tasks):
            print(f"Progress: {idx+1}/{len(all_tasks)} ({success} ok, {failed} fail) in {time.time()-t0:.1f}s")

print(f"European Karaoke download complete! {success} downloaded ({failed} failed) in {time.time()-t0:.1f}s.")
