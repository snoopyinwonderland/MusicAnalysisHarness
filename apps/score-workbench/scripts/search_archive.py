import sys
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

queries = [
    'title:karaoke AND (kar OR mid) AND mediatype:(audio OR data)',
    'karaoke files .kar',
    'subject:karaoke AND mediatype:data',
    'title:karaoke AND mediatype:software',
    'subject:"midi" AND subject:"karaoke"',
    'vanbasco karaoke'
]

for q in queries:
    url = 'https://archive.org/advancedsearch.php?q=' + urllib.parse.quote(q) + '&fl[]=identifier,title,downloads,item_size,description&sort[]=downloads+desc&rows=5&output=json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            docs = data.get('response', {}).get('docs', [])
            print(f'=== Query: {q} ({len(docs)} results) ===')
            for d in docs:
                mb = d.get('item_size', 0) / (1024*1024)
                print(f"  - [{d.get('identifier')}]: {d.get('title')} ({mb:.1f} MB, {d.get('downloads', 0)} dl)")
    except Exception as e:
        print('Error:', e)
