import os
import sys
import io
import time
import zipfile
import urllib.request
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\sound-canvas-japan-midi"
os.makedirs(TARGET_DIR, exist_ok=True)

url = 'https://archive.org/metadata/sound_canvas_midi_collection/files'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

files = data.get('result', [])
zip_files = [f for f in files if f.get('name', '').endswith('.zip')]
print(f"Found {len(zip_files)} zip packages in sound_canvas_midi_collection.")

total_extracted = 0
for idx, f in enumerate(zip_files):
    fname = f['name']
    download_url = f"https://archive.org/download/sound_canvas_midi_collection/{urllib.parse.quote(fname)}"
    try:
        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        
        # Determine extraction subpath
        rel_dir = os.path.dirname(fname)
        dest_subdir = os.path.join(TARGET_DIR, rel_dir)
        os.makedirs(dest_subdir, exist_ok=True)
        
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for item in zf.infolist():
                if item.is_dir():
                    continue
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', os.path.basename(item.filename)).strip('. ')
                if safe_name:
                    out_path = os.path.join(dest_subdir, safe_name)
                    with zf.open(item) as src, open(out_path, 'wb') as dst:
                        dst.write(src.read())
                    total_extracted += 1
    except Exception as e:
        print(f"Error on {fname}: {e}")

    if (idx + 1) % 10 == 0 or (idx + 1) == len(zip_files):
        print(f"Progress: {idx+1}/{len(zip_files)} archives processed ({total_extracted} files extracted)")

print(f"Done! Total extracted: {total_extracted} files to {TARGET_DIR}")
