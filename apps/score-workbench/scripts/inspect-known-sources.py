import json
import sqlite3

db = sqlite3.connect("file:data/search-index-v2/search.sqlite?mode=ro", uri=True)
ids = [
    "work-bd980e8b68c3e32f-57f4f3bb",
    "work-c3bb8d9f02aff4ad-3ba9e1fb",
    "work-0e8609b50c02be68-30d416f5",
    "work-ced30f312d13b14a-88a85b71",
]
for work_id in ids:
    row = db.execute("select id,title,composer,source,license,access_policy,pdmx_metadata,source_metadata from works where id=? limit 1", (work_id,)).fetchone()
    print(json.dumps(row, ensure_ascii=False))
db.close()
