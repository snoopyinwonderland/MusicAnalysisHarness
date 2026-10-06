import hashlib
import json
from pathlib import Path
from test_production_tie_fix import parser

out=Path('reports/production-tie-fix-2026-09-22');out.mkdir(parents=True,exist_ok=False)
rows=[]
for folder in sorted(Path('reports/production-tie-notation-2026-09-22').iterdir()):
    if not folder.is_dir():continue
    old=json.loads((folder/'parser-check.json').read_text(encoding='utf-8'))
    for name,key in [('source.musicxml','before'),('split.musicxml','after')]:
        result=parser.parse_musicxml(folder/name)
        def projected(r):return {s['id']:[{k:v for k,v in n.items() if k not in ('sd','stm')} for n in s['notes']] for s in r['streams']}
        changed=projected(result)!=projected(old[key])
        file=f'{folder.name}-{key}.json'
        (out/file).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        rows.append(dict(case=folder.name,variant=key,projectedChanged=changed,warnings=len(result['tieWarnings']),sourceHash=result['hash']))
summary=dict(rows=rows,parserHash=hashlib.sha256(Path('K:/MusicSearch/scripts/build-musicxml-search-index.py').read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
