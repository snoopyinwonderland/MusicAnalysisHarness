import sqlite3

db = sqlite3.connect("file:data/search-index-v2/search.sqlite?mode=ro", uri=True)
print("access", db.execute("select access_policy,count(*),count(distinct source) from works group by access_policy").fetchall())
print("license", db.execute("select license,count(*) from works group by license order by count(*) desc limit 12").fetchall())
for row in db.execute("select source,pdmx_metadata,source_metadata,access_policy from works where pdmx_metadata <> '{}' or source_metadata is not null limit 15"):
    print(str(row)[:1200])
db.close()
