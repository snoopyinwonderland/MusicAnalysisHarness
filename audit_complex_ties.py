"""Synthetic diagnostic fixtures, not production fixes or musical gold labels."""
import hashlib
import importlib.util
import json
from pathlib import Path
from single_score_melody_review import parse_source, sounding, fq


def note(step, octave, duration=1, tie=None, chord=False):
    ties='' if not tie else f'<tie type="{tie}"/>'
    tied='' if not tie else f'<notations><tied type="{tie}"/></notations>'
    typ={1:'quarter',2:'half',4:'whole'}[duration]
    return f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step><octave>{octave}</octave></pitch><duration>{duration}</duration>{ties}<voice>1</voice><type>{typ}</type><staff>1</staff>{tied}</note>'


def xml(measures):
    attrs='<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>'
    return ('<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list><part id="P1">'+''.join(f'<measure number="{i+1}">{attrs if i==0 else ""}{body}</measure>' for i,body in enumerate(measures))+'</part></score-partwise>').encode()


def run():
    parser_path=Path('K:/MusicSearch/scripts/build-musicxml-search-index.py')
    spec=importlib.util.spec_from_file_location('index_parser',parser_path)
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    root=Path('reports/complex-ties-2026-09-22');root.mkdir(parents=True,exist_ok=False)
    fixtures={
        'across-barline':(xml([note('C',5,4,'start'),note('C',5,1,'stop')+note('D',5)+note('E',5)+note('F',5)]),[[72,0,5],[74,5,1],[76,6,1],[77,7,1]]),
        'upper-chord-tie':(xml([note('C',4)+note('G',4,tie='start',chord=True)+note('C',4)+note('G',4,tie='stop',chord=True)+note('A',4)+note('B',4)]),[[67,0,2],[69,2,1],[71,3,1]]),
        'tie-hidden-by-higher-attack':(xml([note('C',5,tie='start')+note('C',5,tie='stop')+note('E',5,chord=True)+note('G',4)+note('A',4)]),[[72,0,2],[76,1,1],[67,2,1],[69,3,1]]),
        'broken-tie-across-rest':(xml([note('C',5,tie='start')+'<note><rest/><duration>1</duration><voice>1</voice><type>quarter</type></note>'+note('C',5,tie='stop')+note('D',5),note('E',5,4)]),[[72,0,1],[72,2,1],[74,3,1],[76,4,4]])
    }
    results=[]
    for name,(data,expected) in fixtures.items():
        folder=root/name;folder.mkdir();source=folder/'source.musicxml';source.write_bytes(data)
        parsed=parser.parse_musicxml(source);stream=next(s for s in parsed['streams'] if s['id']=='P1:1:1')
        actual=[[n['p'],n['o'],n['d']] for n in stream['notes']]
        _,events,_=parse_source(data);sounds,warnings=sounding(events)
        record=dict(case=name,sourceHash=hashlib.sha256(data).hexdigest(),
            expectation='Preserve sounding duration for selected attacks; do not bridge explicit rest on malformed tie.',
            expected=expected,actual=actual,matches=actual==expected,production=parsed,
            experimentalSounding=[[n['pitch'],float(fq(n['onset'])),float(fq(n['duration']))] for n in sounds],warnings=warnings)
        (folder/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        results.append({k:record[k] for k in ['case','matches','expected','actual','warnings']})
    (root/'summary.json').write_text(json.dumps(dict(results=results,parserHash=hashlib.sha256(parser_path.read_bytes()).hexdigest(),testHash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':run()
