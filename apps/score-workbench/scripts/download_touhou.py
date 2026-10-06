import os
import sys
import io
import zipfile
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIR = r"K:\MusicSearch\data\global-pop-midi\touhou-project-midi"
os.makedirs(TARGET_DIR, exist_ok=True)

zip_names = ['Touhou 6.zip', 'Touhou 7.zip', 'Touhou 8.zip', 'Touhou 9.zip']
headers = {'User-Agent': 'Mozilla/5.0'}

total_extracted = 0
for zn in zip_names:
    url = f"https://archive.org/download/touhou-project-raw-midi-collection/{urllib.parse.quote(zn)}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        sub_dir = os.path.join(TARGET_DIR, zn.replace('.zip', ''))
        os.makedirs(sub_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(sub_dir)
            cnt = len([x for x in zf.namelist() if not x.endswith('/')])
            total_extracted += cnt
            print(f"Extracted {zn} ({cnt} tracks) to {sub_dir}")
    except Exception as e:
        print(f"Error {zn}: {e}")

print(f"Touhou Project MIDIs extracted! Total tracks: {total_extracted}")
