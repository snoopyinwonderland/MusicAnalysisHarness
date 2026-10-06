import os
import sys
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\chinese-karaoke-kar"
os.makedirs(TARGET_DIR, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Fetch file list
print("Fetching Chinese karaoke song list from KaraokeDen...")
req = urllib.request.Request('https://www.karaokeden.com/api/browse.php?category=Chinese', headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

file_list = data.get('files', [])
print(f"Total Chinese karaoke songs found: {len(file_list)}")

# 2. Download files with thread pool
def download_file(fname):
    dest_path = os.path.join(TARGET_DIR, fname)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True, fname, "cached"
    
    url = f"https://www.karaokeden.com/api/download.php?category=Chinese&file={fname}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
        with open(dest_path, 'wb') as f:
            f.write(content)
        return True, fname, len(content)
    except Exception as e:
        return False, fname, str(e)

print(f"Downloading {len(file_list)} .kar files to {TARGET_DIR}...")
t0 = time.time()
success = 0
failed = 0

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(download_file, fname): fname for fname in file_list}
    for idx, fut in enumerate(as_completed(futures)):
        ok, fname, res = fut.result()
        if ok:
            success += 1
        else:
            failed += 1
            if failed <= 5:
                print(f"Failed {fname}: {res}")
        
        if (idx + 1) % 100 == 0 or (idx + 1) == len(file_list):
            print(f"Progress: {idx+1}/{len(file_list)} ({success} downloaded, {failed} failed) in {time.time()-t0:.1f}s")

print(f"Download complete! Successfully downloaded {success} files ({failed} failed) in {time.time()-t0:.1f}s.")
