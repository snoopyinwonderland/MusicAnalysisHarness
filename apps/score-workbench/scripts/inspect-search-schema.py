import json
import sqlite3

db = sqlite3.connect("file:data/search-index-v2/search.sqlite?mode=ro", uri=True)
print(json.dumps({
    "tables": db.execute("select name from sqlite_master where type='table' order by name").fetchall(),
    "works_columns": db.execute("pragma table_info(works)").fetchall(),
    "works_sample": db.execute("select * from works limit 2").fetchall(),
}, ensure_ascii=False, indent=2))
db.close()
