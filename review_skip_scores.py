"""Prepare source-linked notation review, with unchanged musical content."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def prepare(root):
    root=Path(root)
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        review=json.loads((folder/'review.json').read_text(encoding='utf-8'))
        original=json.loads((folder/'input-review.json').read_text(encoding='utf-8'))
        data=(folder/'source.musicxml').read_bytes()
        if hashlib.sha256(data).hexdigest()!=review['sourceHash']: raise ValueError('Source changed')
        tree=ET.fromstring(data)
        for el in tree.iter(): el.tag=el.tag.split('}')[-1]
        mapping={}
        for part in tree.findall('part'):
            for mi,measure in enumerate(part.findall('measure'),1):
                for ei,el in enumerate(measure):
                    if el.tag!='note': continue
                    sid=f'{review["sourceHash"][:16]}:{part.attrib["id"]}:m{mi}:e{ei}'
                    anchor=f'review-note-{len(mapping)}'
                    mapping[sid]=anchor
                    el.set('id',anchor)
        byid={n['id']:n for n in original['baseline']['sounding']}
        notes=[byid[id] for id in original['baseline']['baseline']]
        def anchors(ids): return [mapping[s] for id in ids for s in byid[id]['sourceIds']]
        cards=[]
        for proposal in review['proposals']:
            a,z=proposal['start'],proposal['endExclusive']
            # Pick one supporting window; retain all others in the JSON evidence.
            pi=proposal['supportPairs'][0]
            pair=original['recurrence']['pairs'][pi]
            for side in (0,1):
                match={m[side]:m[1-side] for m in pair['matches']}
                if a-1 in match and z in match and match[z]-match[a-1]==1: break
            else: raise ValueError('Missing adjacent counterpart')
            lo,hi=match[a-1],match[z]
            counterpart=[n['id'] for n in notes[max(0,lo-1):hi+2]]
            cards.append(dict(id=proposal['id'],status=proposal['status'],blockers=proposal['blockers'],
                omitted=anchors(proposal['omittedIds']),context=anchors(proposal['contextIds']),
                counterpart=anchors(counterpart),counterpartAnchors=anchors([notes[lo]['id'],notes[hi]['id']]),
                description=' → '.join(f"m{byid[id]['printedMeasure']} {byid[id]['spelling']}" for id in proposal['contextIds']),
                pairIndex=pi))
        (folder/'render.musicxml').write_bytes(ET.tostring(tree,encoding='utf-8',xml_declaration=True))
        (folder/'notation.json').write_text(json.dumps(dict(source=review['source'],cards=cards),ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');prepare(parser.parse_args().root)
