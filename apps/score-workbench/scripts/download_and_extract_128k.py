import os
import sys
import time
import zipfile
import re
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

URL = "https://archive.org/download/79-k-midi-archives-nov-2024/MIDI_ARCHIVES.zip"
TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\128k-midi-archive"
ZIP_PATH = r"K:\MusicSearch\data\global-pop-midi\MIDI_ARCHIVES.zip"

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

if not os.path.exists(ZIP_PATH) or os.path.getsize(ZIP_PATH) < 550 * 1024 * 1024:
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp, open(ZIP_PATH, 'wb') as f:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        last_log = 0
        chunk_size = 1024 * 1024  # 1MB
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
    print(f"Download complete: {os.path.getsize(ZIP_PATH)/(1024*1024):.1f} MB in {time.time()-t0:.1f}s")
else:
    print(f"File already downloaded ({os.path.getsize(ZIP_PATH)/(1024*1024):.1f} MB). Skipping download.")

# 2. Extract
print(f"Extracting {ZIP_PATH} to {TARGET_DIR}...")
t1 = time.time()
extracted_count = 0
error_count = 0

with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    infolist = zf.infolist()
    total_files = len(infolist)
    print(f"Total entries in archive: {total_files}")
    
    for idx, info in enumerate(infolist):
        if info.is_dir():
            continue
        clean_rel = sanitize_path(info.filename)
        if not clean_rel:
            continue
        dest_path = os.path.join(TARGET_DIR, clean_rel)
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with zf.open(info) as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            extracted_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"Warning extracting {info.filename}: {e}")
        
        if (idx + 1) % 25000 == 0 or (idx + 1) == total_files:
            print(f"Progress: {idx+1}/{total_files} processed ({extracted_count} extracted, {error_count} errors)")

print(f"Extraction complete! {extracted_count} files extracted in {time.time()-t1:.1f}s ({error_count} errors).")

# Clean up zip archive to save space
if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
    print(f"Removed temporary archive {ZIP_PATH} to save disk space.")
