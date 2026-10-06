"""Build an isolated audit SQLite index, never the production database."""
import hashlib
import json
import sqlite3
from pathlib import Path
from test_production_tie_fix import parser

out=Path('reports/tie-staging-2026-09-22');out.mkdir(parents=True,exist_ok=False)
db=sqlite3.connect(out/'audit.sqlite')
db.execute('CREATE TABLE streams (case_id TEXT, stream_id TEXT, source_hash TEXT, notes_json TEXT, warnings_json TEXT, PRIMARY KEY(case_id,stream_id))')
manifest=[]
for case in ['S-STRUCT-004','S-STRUCT-005','S-STRUCT-006','three-times-a-lady']:
    source=Path('reports/production-tie-notation-2026-09-22')/case/'source.musicxml'
    data=source.read_bytes();result=parser.parse_musicxml(source)
    folder=out/case;folder.mkdir();(folder/'source.musicxml').write_bytes(data)
    (folder/'indexed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for stream in result['streams']:
        db.execute('INSERT INTO streams VALUES(?,?,?,?,?)',(case,stream['id'],result['hash'],json.dumps(stream['notes']),json.dumps(result['tieWarnings'])))
    manifest.append(dict(case=case,sourceHash=hashlib.sha256(data).hexdigest(),streamCount=len(result['streams'])))
db.commit()
assert db.execute('SELECT COUNT(*) FROM streams').fetchone()[0]==sum(r['streamCount'] for r in manifest)
# Export actual staged rows for the JS analyzer, not an independent in-memory copy.
rows=[dict(case=c,stream=s,sourceHash=h,notes=json.loads(n),warnings=json.loads(w)) for c,s,h,n,w in db.execute('SELECT * FROM streams ORDER BY case_id,stream_id')]
db.close()
(out/'staged-rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Staged {len(rows)} streams in {out}/audit.sqlite')
