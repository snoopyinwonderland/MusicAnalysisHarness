import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request('https://www.karaokeden.com/api/categories.php', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    cats = json.loads(resp.read().decode('utf-8'))
for c in cats:
    print(f"{c['name']}: {c['fileCount']} files")
