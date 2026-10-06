export const harderKinds=['two-pitches','two-octaves','two-rhythm-pairs','two-leaps','two-rest-splits'];
export function harderVariation(original,kind){
 const events=structuredClone(original),notes=events.filter(e=>e.kind==='note'),changes=[];
 const pitch=(index,delta)=>{const n=notes[index],before=n.pitchMidi;n.pitchMidi+=delta;delete n.spelling;changes.push({index,field:'pitchMidi',before,after:n.pitchMidi});};
 const length=(index,value)=>{const n=notes[index],before=n.durationRatio;n.durationRatio=value;changes.push({index,field:'durationRatio',before,after:value});};
 if(notes.length<8)throw Error('At least eight notes');
 if(kind==='two-pitches'){pitch(2,notes[2].pitchMidi<=124?2:-2);pitch(6,notes[6].pitchMidi>=3?-3:3);}
 else if(kind==='two-octaves'){pitch(2,notes[2].pitchMidi<=115?12:-12);pitch(6,notes[6].pitchMidi>=12?-12:12);}
 else if(kind==='two-rhythm-pairs'){for(const [a,b] of [[2,3],[6,7]]){const d=notes[b].durationRatio/2;length(a,notes[a].durationRatio+d);length(b,notes[b].durationRatio-d);}}
 else if(kind==='two-leaps'){
  const edges=notes.slice(1).map((n,i)=>({i:i+1,delta:n.pitchMidi-notes[i].pitchMidi})).filter(x=>Math.abs(x.delta)>=4&&x.i<notes.length-1).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta));
  const chosen=[];for(const x of edges){if(chosen.every(y=>Math.abs(y.i-x.i)>1))chosen.push(x);if(chosen.length===2)break;}
  if(chosen.length!==2)throw Error('Two separated leaps required');for(const x of chosen)pitch(x.i,-Math.sign(x.delta)*Math.min(5,Math.abs(x.delta)-1));
 }else if(kind==='two-rest-splits'){for(const i of [2,6]){const d=notes[i].durationRatio/2;length(i,d);events.splice(events.indexOf(notes[i])+1,0,{id:'split-rest-'+i,kind:'rest',pitchMidi:null,durationRatio:d});changes.push({index:i,field:'insert-rest',duration:d});}}
 else throw Error('Unknown variation');
 if(events.some(e=>!(e.durationRatio>0)||e.kind==='note'&&(e.pitchMidi<0||e.pitchMidi>127)))throw Error('Invalid mutation');
 return {events,changes};
}
