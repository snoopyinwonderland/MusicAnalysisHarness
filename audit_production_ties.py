"""Call production index parser read-only; never rebuild live corpus."""
import importlib.util
import hashlib
import json
from pathlib import Path

parser_path=Path('K:/MusicSearch/scripts/build-musicxml-search-index.py')
spec=importlib.util.spec_from_file_location('production_index',parser_path)
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
root=Path('reports/production-tie-notation-2026-09-22');root.mkdir(parents=True,exist_ok=False)
summaries=[]
for case in ['S-STRUCT-004','S-STRUCT-005','S-STRUCT-006','three-times-a-lady']:
    source=Path('reports/phrase-tie-notation-2026-09-22')/case
    before=parser.parse_musicxml(source/'source.musicxml')
    after=parser.parse_musicxml(source/'split.musicxml')
    folder=root/case;folder.mkdir()
    for name in ['source.musicxml','split.musicxml']:(folder/name).write_bytes((source/name).read_bytes())
    def facts(stream):return [{k:n.get(k) for k in ['m','mn','b','o','d','p','s']} for n in stream['notes']]
    left={s['id']:s for s in before['streams']};right={s['id']:s for s in after['streams']}
    comparisons=[]
    for id in sorted(set(left)|set(right)):
        a,b=left.get(id),right.get(id)
        comparisons.append(dict(stream=id,existsBoth=a is not None and b is not None,
            musicalEqual=a is not None and b is not None and facts(a)==facts(b),
            rawEqual=a is not None and b is not None and a['notes']==b['notes'],
            beforeCount=len(a['notes']) if a else None,afterCount=len(b['notes']) if b else None))
    result=dict(case=case,before=before,after=after,comparisons=comparisons,parserHash=hashlib.sha256(parser_path.read_bytes()).hexdigest())
    (folder/'parser-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    summaries.append(dict(case=case,comparisons=comparisons))
(root/'summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
print(json.dumps(summaries,indent=2))
