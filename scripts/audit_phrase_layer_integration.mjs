// Read-only review of a separate phrase worktree. Output only in this workspace.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';

const root=resolve(process.argv[2]), output=resolve(process.argv[3]);
if(existsSync(output))throw new Error('output_exists_no_overwrite');
const files=['server/phrase-breath-layer.mjs','server/phrase-breath-layer.test.js','server/search-api.mjs',
 'server/boundary-harmony.mjs','src/components/FullScorePage.tsx','src/components/PhraseLayersPanel.tsx'];
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const before=Object.fromEntries(files.map(p=>[p,sha(join(root,p))]));
// Commit supplied from a separate read-only git check: managed Node runtime
// may prohibit child-process creation. File hashes remain checked here.
const commit=process.argv[4];
if(!/^[0-9a-f]{40}$/.test(commit||''))throw new Error('observed_git_commit_required');
const {analyzeBreathLayer,analyzePhraseLayers}=await import(pathToFileURL(join(root,files[0])).href);
const line=units=>{
 const notes=[];let t=0;
 for(let u=0;u<units;u++){
  for(const [p,d] of [[60,1],[62,1],[64,1],[65,1],[67,1],[65,1]]){notes.push({pitchMidi:p,onset:t,durationRatio:d});t+=d;}
  notes.push({pitchMidi:64,onset:t,durationRatio:1});t+=2;
 }
 return notes.map(n=>({...n,measureOrdinal:Math.floor(n.onset/4)+1,mstart:Math.floor(n.onset/4)*4,meterCount:4,meterUnit:4}));
};
const tests=[];
const test=(name,fn)=>{fn();tests.push({name,passed:true});};
test('four rested two-bar units',()=>assert.deepEqual(analyzeBreathLayer(line(4)).starts,[7,14,21]));
const tied=[...line(2).slice(0,6),{...line(2)[6],durationRatio:1},
 {...line(2)[6],onset:7,durationRatio:1,tieStop:true,isAttack:false},...line(2).slice(7)];
test('correct tie extends release without new attack',()=>assert.deepEqual(analyzeBreathLayer(tied).starts,[8]));
const at=(strength)=>analyzePhraseLayers(line(4),{key:{tonicPc:0,minor:false},
 cadenceAt:indices=>new Map(indices.filter(i=>i===7).map(i=>[i,{type:'PAC',strength}]))});
test('supplied authentic cadence can close upper unit',()=>assert.ok(at(.8).phrases.starts.includes(7)));
test('MusicXML beat fallback',()=>assert.deepEqual(analyzeBreathLayer(line(2).map(({mstart,...n})=>({...n,beat:1+n.onset-mstart}))).starts,[7]));
test('missing metre rejected',()=>assert.throws(()=>analyzeBreathLayer([{pitchMidi:60,onset:0,durationRatio:1},{pitchMidi:62,onset:1,durationRatio:1}])));
const weak=at(0), strong=at(1);
const wrongTie=structuredClone(tied);wrongTie[7].pitchMidi=61;wrongTie[7].voiceId='other';
let wrongTieRejected=false;try{analyzeBreathLayer(wrongTie)}catch{wrongTieRejected=true;}
const negative=structuredClone(line(2));negative[3].durationRatio=-1;
let negativeRejected=false;try{analyzeBreathLayer(negative)}catch{negativeRejected=true;}
const after=Object.fromEntries(files.map(p=>[p,sha(join(root,p))]));
assert.deepEqual(after,before);
const report={complete:true,worktree:root,commit,commit_observed_by_external_git_check:true,input_hashes:before,
 source_files_unchanged:true,smoke_tests:tests,vitest_suite_executed:false,corpus_evaluation_reexecuted:false,
 probes:{cadence_strength_changes_upper_boundaries:JSON.stringify(weak.phrases.starts)!==JSON.stringify(strong.phrases.starts),
 cadence_strength_zero_still_selects_cadence:weak.phrases.boundaries.some(b=>b.cadence?.type==='PAC'),
 wrong_pitch_or_voice_tie_rejected:wrongTieRejected,negative_duration_rejected:negativeRejected},
 limits:['Synthetic read-only integration probes, not real-score accuracy or browser verification.',
 'Cadence strength is an uncalibrated evidence score, not a correctness probability.',
 'No merge, remote write, external worktree edit, dependency installation or server change.']};
if(process.argv[5]){
 const reportRoot=resolve(process.argv[5]);
 report.external_evaluation_snapshots={};
 for(const name of ['phrase_layers_final.json','layers_port_check.json','folk_benchmark.json']){
  const p=join(reportRoot,name), data=readFileSync(p), digest=createHash('sha256').update(data).digest('hex');
  assert.equal(sha(p),digest);
  report.external_evaluation_snapshots[name]={source_path:p,sha256:digest,value:JSON.parse(data.toString('utf8'))};
 }
}
mkdirSync(output,{recursive:true});writeFileSync(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n','utf8');
const {external_evaluation_snapshots,...summary}=report;
console.log(JSON.stringify({...summary,external_evaluation_snapshots:external_evaluation_snapshots?Object.keys(external_evaluation_snapshots):[]},null,2));
