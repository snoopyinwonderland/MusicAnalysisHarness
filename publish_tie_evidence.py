"""Evidence-only patch. Never changes attacks, IDs, durations, or postings."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

apply='--apply' in sys.argv
root=Path('reports/tie-evidence-publish-2026-09-22')
dbpath=Path('K:/MusicSearch/data/search-index-v2/search.sqlite')
db=sqlite3.connect(str(dbpath) if apply else dbpath.as_uri()+'?mode=ro',uri=not apply,timeout=5)
plans=[];skipped=[]
for case in ['S-STRUCT-004','S-STRUCT-005','S-STRUCT-006']:
    result=json.loads((Path('reports/tie-staging-2026-09-22')/case/'indexed.json').read_text(encoding='utf-8'))
    base='work-'+result['hash'][:16]
    for s in result['streams']:
        ids=[base,base+'-'+hashlib.sha1(s['id'].encode()).hexdigest()[:8]]
        rows=db.execute('SELECT id,source,stream_id,notes FROM works WHERE id IN (?,?)',ids).fetchall()
        row=next((r for r in rows if r[2]==s['id']),None)
        if not row:skipped.append([case,s['id'],'not-found']);continue
        live=Path('U:/KYSing_MusicXML')/row[1][7:] if row[1].startswith('kysing/') else Path('K:/Music Analysis/MusicXML')/row[1]
        if not live.is_file() or hashlib.sha256(live.read_bytes()).hexdigest()!=result['hash']:raise ValueError(f'Live source mismatch: {case} {row[0]} source={row[1]} expected={result["hash"]} actual={hashlib.sha256(live.read_bytes()).hexdigest() if live.is_file() else "missing"}')
        old=json.loads(row[3]);new=s['notes']
        stripped=lambda ns:[{k:v for k,v in n.items() if k not in ('sd','stm')} for n in ns]
        if stripped(old)!=stripped(new):raise ValueError('Would change indexed music: '+row[0])
        updated=[dict(n,**{k:c[k] for k in ('sd','stm') if k in c}) for n,c in zip(old,new)]
        if old!=updated:plans.append(dict(id=row[0],source=row[1],stream=row[2],before=row[3],after=json.dumps(updated,separators=(',',':')),sourceHash=result['hash']))
if apply:
    root.mkdir(parents=True,exist_ok=False)
    # Exact row before-images, enough to reverse this notes-only transaction.
    (root/'row-backup.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        db.execute('BEGIN IMMEDIATE')
        for p in plans:
            c=db.execute('UPDATE works SET notes=? WHERE id=? AND notes=?',(p['after'],p['id'],p['before']))
            if c.rowcount!=1:raise ValueError('Concurrent row change')
        db.commit()
    except Exception:
        db.rollback();raise
    for p in plans:assert db.execute('SELECT notes FROM works WHERE id=?',(p['id'],)).fetchone()[0]==p['after']
    (root/'summary.json').write_text(json.dumps(dict(updated=[{k:p[k] for k in ('id','source','stream','sourceHash')} for p in plans],skipped=skipped,deferred='Three Times a Lady attack-changing reindex'),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(apply=apply,planned=[{k:p[k] for k in ('id','source','stream')} for p in plans],skipped=skipped),ensure_ascii=False,indent=2))
db.close()
