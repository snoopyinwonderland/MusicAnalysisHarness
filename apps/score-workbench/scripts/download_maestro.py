import os
import sys
import zipfile
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

URL = "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip"
TARGET_DIR = r"K:\MusicSearch\data\classical-corpora\maestro-piano-midi"
ZIP_PATH = r"K:\MusicSearch\data\classical-corpora\maestro-v3.0.0-midi.zip"

os.makedirs(TARGET_DIR, exist_ok=True)

print(f"Downloading MAESTRO v3.0.0 MIDI ({URL})...")
t0 = time.time()
urllib.request.urlretrieve(URL, ZIP_PATH)
print(f"Downloaded {os.path.getsize(ZIP_PATH)/(1024*1024):.2f} MB in {time.time()-t0:.1f}s")

print(f"Extracting {ZIP_PATH} to {TARGET_DIR}...")
t1 = time.time()
with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    zf.extractall(TARGET_DIR)

print(f"Extraction complete in {time.time()-t1:.1f}s!")

if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
    print("Removed temporary zip to save space.")
