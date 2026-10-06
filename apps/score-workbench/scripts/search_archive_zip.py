import sys
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

q = '(karaoke OR midi) AND (format:ZIP OR format:7z) AND (item_size:[10000000 TO 2000000000])'
url = f'https://archive.org/advancedsearch.php?q={urllib.parse.quote(q)}&fl[]=identifier,title,downloads,item_size,description&sort[]=downloads+desc&rows=30&output=json'

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        docs = data.get('response', {}).get('docs', [])
        print(f'Total results: {len(docs)}')
        for d in docs:
            mb = d.get('item_size', 0) / (1024*1024)
            desc = (d.get('description') or '')[:100].replace('\n', ' ')
            print(f"- [{d.get('identifier')}]: {d.get('title')} ({mb:.1f} MB, {d.get('downloads')} dl)")
            if desc:
                print(f"    Desc: {desc}")
except Exception as e:
    print('Error:', e)
