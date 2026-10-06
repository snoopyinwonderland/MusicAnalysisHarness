"""Read-only MusicXML adapter for structural experiments; original XML untouched."""
import json, hashlib, sys
from pathlib import Path
from fractions import Fraction as F
from xml.etree import ElementTree as ET

def q(x): return {'n':x.numerator,'d':x.denominator}
def adapt(path):
    raw=Path(path).read_bytes(); root=ET.fromstring(raw)
    for node in root.iter(): node.tag=node.tag.split('}')[-1]
    if root.tag!='score-partwise': raise ValueError('Only score-partwise supported')
    events=[]; issues=[]
    for part in root.findall('part'):
        part_id=part.get('id'); absolute=F(0); divisions=None; meter=None; measure_length=None; active_ties={}; chain_count=0
        for ordinal,measure in enumerate(part.findall('measure'),1):
            cursor=F(0); extent=F(0); chord_start=F(0); note_index=0
            for element in measure:
                if element.tag=='attributes':
                    if element.findtext('divisions') is not None: divisions=F(element.findtext('divisions'))
                    t=element.find('time')
                    if t is not None:
                        beats=t.findtext('beats'); unit=t.findtext('beat-type')
                        meter=f'{beats}/{unit}'
                        try: measure_length=sum(F(b) for b in beats.split('+'))*4/F(unit)
                        except (ValueError,TypeError): measure_length=None
                if element.tag in ('backup','forward'):
                    if divisions is None: raise ValueError('Missing divisions')
                    cursor+=(1 if element.tag=='forward' else -1)*F(element.findtext('duration'))/divisions
                    if cursor<0: raise ValueError('Backup before measure start')
                    extent=max(extent,cursor)
                if element.tag!='note': continue
                note_index+=1; grace=element.find('grace') is not None
                if divisions is None and not grace: raise ValueError('Missing divisions')
                duration=F(element.findtext('duration','0'))/divisions if divisions else F(0)
                chord=element.find('chord') is not None
                start=chord_start if chord else cursor
                if not chord: chord_start=start; cursor+=duration
                extent=max(extent,start+duration)
                if element.find('unpitched') is not None:
                    issues.append({'part':part_id,'measureOrdinal':ordinal,'reason':'unpitched-excluded'});continue
                pitch=element.find('pitch'); rest=element.find('rest') is not None
                if pitch is None and not rest: continue
                voice=element.findtext('voice','1'); staff=element.findtext('staff','1')
                eid=f'{part_id}:m{ordinal}:n{note_index}'
                e={'id':eid,'xmlNoteId':element.get('id',eid),'xmlLocator':{'partId':part_id,'measureOrdinal':ordinal,'noteIndex':note_index},
                   'partId':part_id,'voiceId':voice,'staffId':staff,'kind':'rest' if rest else 'note',
                   'measureOrdinal':ordinal,'originalMeasureLabel':measure.get('number'),
                   'onsetQ':q(absolute+start),'durationQ':q(duration),'beatQ':q(start),'meter':meter,
                   'grace':grace,'cue':element.find('cue') is not None,'pitchMidi':None,
                   'identityDefaults':{'voice':element.find('voice') is None,'staff':element.find('staff') is None}}
                if not rest:
                    step=pitch.findtext('step'); octave=int(pitch.findtext('octave')); alter=F(pitch.findtext('alter','0'))
                    e.update(pitchMidi=float((octave+1)*12+{'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]+alter),
                             diatonicPitch=octave*7+'CDEFGAB'.index(step),writtenPitch={'step':step,'alter':str(alter),'octave':octave})
                    types={t.get('type') for t in element.findall('tie')}
                    key=(voice,staff,e['pitchMidi'])
                    if 'stop' in types:
                        e.update(tieStop=True,isAttack=False)
                        if key in active_ties:e['tieChainId']=active_ties[key]
                        else:issues.append({'eventId':eid,'reason':'orphan-tie-stop'})
                        if 'start' not in types:active_ties.pop(key,None)
                    if 'start' in types:
                        if key not in active_ties:chain_count+=1;active_ties[key]=f'{part_id}:tie{chain_count}'
                        e['tieChainId']=active_ties[key];e['tieStart']=True
                events.append(e)
            pickup=ordinal==1 and measure_length is not None and extent<measure_length
            if pickup:
                for e in events:
                    if e['partId']==part_id and e['measureOrdinal']==ordinal:e['pickup']=True
            # Explicit short/implicit measures use actual duration; normal bars retain meter.
            absolute+=extent if pickup or measure.get('implicit')=='yes' or measure_length is None else max(extent,measure_length)
        for key in active_ties:issues.append({'part':part_id,'reason':'open-tie-at-end','voiceStaffPitch':key})
    return {'sourceHash':hashlib.sha256(raw).hexdigest(),'sourcePath':str(Path(path).resolve()),'events':events,
            'adapterVersion':'structural-xml-source/1','adapterIssues':issues,
            'limitations':['Written pitch retained; transposing instruments are not converted to sounding pitch.',
                            'No harmony inference; harmony tags are not assumed to certify chord tones.',
                            'Missing voice/staff defaults are recorded, not inferred voice separation.']}

if __name__=='__main__':
    print(json.dumps(adapt(sys.argv[1]),ensure_ascii=True))
