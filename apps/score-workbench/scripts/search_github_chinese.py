import sys
import urllib.request
import urllib.parse
import json

sys.stdout.reconfigure(encoding='utf-8')

queries = [
    'chinese midi',
    'cpop midi',
    'mandopop midi',
    'chinese songs midi',
    'chinese karaoke',
    'midi_lyric_corpus',
    'chinese folk midi'
]

for q in queries:
    url = f'https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=5'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
            print(f"=== Query: {q} ({data.get('total_count', 0)} total) ===")
            for item in items:
                desc = (item.get('description') or '')[:100].replace('\n', ' ')
                print(f"  - [{item['full_name']}] (★ {item['stargazers_count']}): {desc}")
    except Exception as e:
        print(f"Error for {q}: {e}")
