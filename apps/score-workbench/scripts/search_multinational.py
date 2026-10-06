import sys
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

searches = [
    'karaoke AND (spanish OR espanol OR latino)',
    'karaoke AND (italian OR italia OR canzone)',
    'karaoke AND (french OR chanson)',
    'karaoke AND (korea OR korean)',
    'karaoke AND (japan OR japanese OR jpop OR anime)',
    'karaoke AND (china OR chinese OR cpop)',
    'karaoke AND (vietnam OR thai OR filipino OR tagalog)',
    'midi AND (anime OR touhou)',
    'vanbasco collection'
]

for s in searches:
    url = f'https://archive.org/advancedsearch.php?q={urllib.parse.quote(s)}&fl[]=identifier,title,downloads,item_size,mediatype&sort[]=downloads+desc&rows=4&output=json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            docs = data.get('response', {}).get('docs', [])
            print(f'=== Search: {s} ({len(docs)} items) ===')
            for d in docs:
                mb = d.get('item_size', 0) / (1024*1024)
                print(f"  [{d.get('identifier')}]: {d.get('title')} ({mb:.1f} MB, {d.get('mediatype')}, {d.get('downloads')} dl)")
    except Exception as e:
        print(f'Error for {s}: {e}')
