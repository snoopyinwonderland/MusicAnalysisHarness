import os
import sys
import zipfile
import re
import io
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

URL = "https://github.com/00sapo/OpenEWLD/archive/refs/heads/master.zip"
TARGET_DIR = r"K:\MusicSearch\data\pop-and-analysis-corpora\openewld-leadsheets"
os.makedirs(TARGET_DIR, exist_ok=True)

def sanitize_path(path):
    parts = path.replace('\\', '/').split('/')
    clean_parts = []
    for p in parts:
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', p).strip('. ')
        if cleaned:
            clean_parts.append(cleaned)
    return os.path.join(*clean_parts) if clean_parts else ""

print(f"Downloading OpenEWLD zip from {URL}...")
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = resp.read()

print(f"Downloaded {len(data)/(1024*1024):.2f} MB. Extracting with Windows path sanitization...")
extracted = 0
with zipfile.ZipFile(io.BytesIO(data)) as zf:
    for item in zf.infolist():
        if item.is_dir():
            continue
        rel_path = item.filename
        # Strip top directory (OpenEWLD-master/)
        parts = rel_path.split('/')
        if len(parts) > 1:
            clean_rel = sanitize_path('/'.join(parts[1:]))
        else:
            clean_rel = sanitize_path(parts[0])
        
        if not clean_rel:
            continue
        out_path = os.path.join(TARGET_DIR, clean_rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with zf.open(item) as src, open(out_path, 'wb') as dst:
            dst.write(src.read())
        extracted += 1

print(f"OpenEWLD successfully extracted! {extracted} files saved to {TARGET_DIR}")
