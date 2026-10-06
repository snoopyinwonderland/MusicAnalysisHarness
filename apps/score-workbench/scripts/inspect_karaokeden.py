import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.karaokeden.com/assets/index-BtRiBNvL.js'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    content = resp.read().decode('utf-8', errors='ignore')

# Search for fetch calls
fetch_calls = [m.start() for m in re.finditer(r'fetch\(', content)]
print(f"Total fetch calls: {len(fetch_calls)}")
for pos in fetch_calls:
    print("Fetch:", content[pos:pos+150])

# Search for zip download logic
zip_pos = [m.start() for m in re.finditer(r'\.zip', content)]
print(f"Total zip references: {len(zip_pos)}")
for pos in zip_pos:
    print("Zip snippet:", content[pos-50:pos+80])
