import os
import sys
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\vietnamese-karaoke-kar"
os.makedirs(TARGET_DIR, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0'}
categories = ['Vietnamese', 'Vietnamese-2', 'Vietnamese-3']

all_tasks = []
print("Fetching Vietnamese karaoke song lists from KaraokeDen...")
for cat in categories:
    url = f"https://www.karaokeden.com/api/browse.php?category={cat}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            files = data.get('files', [])
            print(f"  {cat}: {len(files)} files")
            for f in files:
                all_tasks.append((cat, f))
    except Exception as e:
        print(f"Error fetching {cat}: {e}")

print(f"Total Vietnamese songs to download: {len(all_tasks)}")

def download_file(item):
    cat, fname = item
    safe_name = f"{cat}_{fname}"
    dest_path = os.path.join(TARGET_DIR, safe_name)
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

print(f"Downloading {len(all_tasks)} Vietnamese .kar files...")
t0 = time.time()
success = 0
failed = 0

with ThreadPoolExecutor(max_workers=12) as executor:
    futures = {executor.submit(download_file, item): item for item in all_tasks}
    for idx, fut in enumerate(as_completed(futures)):
        ok, sname, res = fut.result()
        if ok:
            success += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"Warning {sname}: {res}")
        if (idx + 1) % 300 == 0 or (idx + 1) == len(all_tasks):
            print(f"Progress: {idx+1}/{len(all_tasks)} ({success} ok, {failed} fail) in {time.time()-t0:.1f}s")

print(f"Vietnamese Karaoke download complete! {success} downloaded ({failed} failed) in {time.time()-t0:.1f}s.")
