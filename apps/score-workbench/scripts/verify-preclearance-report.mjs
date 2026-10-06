import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import assert from 'node:assert/strict';
const [dir]=process.argv.slice(2);if(!dir||existsSync(join(dir,'verification.json')))throw new Error('Report directory without prior verification required');
const report=JSON.parse(readFileSync(join(dir,'report.json'),'utf8')),manifest=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8')),html=readFileSync(join(dir,'index.html'),'utf8');
assert.equal(report.title,'Copyright Infringement Report');assert.equal(manifest.renderAudit.filter(x=>x.error).length,0);
for(const r of manifest.renderAudit){assert(r.svgNotes>0);for(const id of r.redIds)assert(html.includes(`id="${id}"`),'Missing highlighted note '+id)}
assert(!/<(?:iframe|script)[^>]+src="https?:/.test(html),'Unexpected remote dependency');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];assert(script);
const created=[],elements={playing:{textContent:''},bpm:{value:'90'},stop:{}},button={dataset:{track:'0'},textContent:'A 입력'};
const automationDocument={getElementById:id=>elements[id],querySelectorAll:()=>[button]};
class FakeAudioContext{currentTime=10;destination={};resume(){return Promise.resolve()}createOscillator(){const n={frequency:{value:0},connect(){},start(t){this.started=t},stop(t){this.stopped=t}};created.push(n);return n}createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){}},connect(){}}}}
const tracks=new Function('document','AudioContext','setTimeout','clearTimeout',script+';return tracks;')(automationDocument,FakeAudioContext,()=>0,()=>{});
await button.onclick();const notes=tracks[0].filter(e=>e.kind==='note');assert.equal(created.length,notes.length,'Logical tied notes must sound once');
let onset=10.08,index=0;for(const e of tracks[0]){if(e.kind==='note'){assert(Math.abs(created[index].started-onset)<1e-6);assert(Math.abs(created[index].frequency.value-440*2**((e.pitchMidi-69)/12))<1e-6);index++}onset+=e.durationRatio*60/90}
elements.stop.onclick();created.length=0;await Promise.all([button.onclick(),button.onclick()]);assert.equal(created.length,notes.length,'Rapid A/B switch scheduled duplicate playback');elements.stop.onclick();
const result={works:report.works.length,matches:report.works.reduce((s,w)=>s+w.matches.length,0),renderedScores:manifest.renderAudit.length,highlightTargetsPresent:true,scriptParsed:true,audioScheduleAndCancellation:true,
 warning:'Audio scheduling verified with a test AudioContext; no claim of listening or original-engraving equivalence.'};
writeFileSync(join(dir,'verification.json'),JSON.stringify(result,null,2),{flag:'wx'});console.log(JSON.stringify(result));
