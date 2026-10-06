import os
import sys
import time
import tarfile
import re
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

URL = "http://hog.ee.columbia.edu/craffel/lmd/lmd_matched.tar.gz"
TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\lmd_matched"
TAR_PATH = r"K:\MusicSearch\data\global-pop-midi\lmd_matched.tar.gz"

os.makedirs(TARGET_DIR, exist_ok=True)

def sanitize_path(path):
    parts = path.replace('\\', '/').split('/')
    clean_parts = []
    for p in parts:
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', p).strip('. ')
        if cleaned:
            clean_parts.append(cleaned)
    return os.path.join(*clean_parts) if clean_parts else ""

# 1. Download
print(f"Starting download: {URL}")
t0 = time.time()

if not os.path.exists(TAR_PATH) or os.path.getsize(TAR_PATH) < 1300 * 1024 * 1024:
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(TAR_PATH, 'wb') as f:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        last_log = 0
        chunk_size = 2 * 1024 * 1024  # 2MB
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            pct = int(downloaded / total * 100) if total else 0
            if pct >= last_log + 10:
                elapsed = time.time() - t0
                speed = downloaded / (1024 * 1024) / elapsed if elapsed > 0 else 0
                print(f"Downloaded: {downloaded/(1024*1024):.1f} / {total/(1024*1024):.1f} MB ({pct}%) at {speed:.2f} MB/s")
                last_log = pct
    print(f"Download complete: {os.path.getsize(TAR_PATH)/(1024*1024):.1f} MB in {time.time()-t0:.1f}s")
else:
    print(f"File already downloaded ({os.path.getsize(TAR_PATH)/(1024*1024):.1f} MB). Skipping download.")

# 2. Extract
print(f"Extracting {TAR_PATH} to {TARGET_DIR}...")
t1 = time.time()
extracted_count = 0
error_count = 0

with tarfile.open(TAR_PATH, 'r:gz') as tar:
    for idx, member in enumerate(tar):
        if not member.isfile():
            continue
        clean_rel = sanitize_path(member.name)
        if not clean_rel:
            continue
        dest_path = os.path.join(TARGET_DIR, clean_rel)
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            f_in = tar.extractfile(member)
            if f_in:
                with open(dest_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                extracted_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"Warning extracting {member.name}: {e}")
        
        if (extracted_count) % 10000 == 0 and extracted_count > 0:
            print(f"Progress: {extracted_count} files extracted ({error_count} errors)")

print(f"Extraction complete! {extracted_count} files extracted in {time.time()-t1:.1f}s ({error_count} errors).")

# Clean up tar archive
if os.path.exists(TAR_PATH):
    os.remove(TAR_PATH)
    print(f"Removed temporary archive {TAR_PATH} to save disk space.")
