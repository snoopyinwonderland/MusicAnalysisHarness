import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {analyzePhraseBoundaries} from '../server/phrase-boundaries.mjs';
const run=process.argv[2];if(!/^[a-z0-9-]+$/.test(run??''))throw Error('Run name required');
const out=`evaluation/reports/${run}`;if(existsSync(out))throw Error('Refusing overwrite');
const hash=x=>createHash('sha256').update(x).digest('hex'),rows=[];
for(const id of ['004','005','006','007','008']){
 const root=`evaluation/case-assets/S-STRUCT-${id}`,raw=readFileSync(root+'/review-snapshot.json'),s=JSON.parse(raw),xml=readFileSync(root+'/context.musicxml');if(hash(xml)!==s.xmlSha256)throw Error('Source mismatch');
 const old=analyzePhraseBoundaries(s.work.notes,{repeatBreath:false}),current=analyzePhraseBoundaries(s.work.notes);
 rows.push({caseId:id,sourceHash:hash(xml),snapshotHash:hash(raw),changed:current.boundaries.filter((b,i)=>b.supported!==old.boundaries[i].supported).map(b=>({index:b.index,eventId:s.work.notes[b.index].id,supported:b.supported})),evidence:current.repeatedBreath});
}
mkdirSync(out,{recursive:true});writeFileSync(out+'/regression.json',JSON.stringify({version:'local-boundary-evidence-v1.15',codeHashes:Object.fromEntries(['server/phrase-boundaries.mjs','server/repeated-breath-rule.mjs','server/phrase-breath-symbols.mjs'].map(p=>[p,hash(readFileSync(p))])),rows},null,2));console.log(JSON.stringify(rows.map(r=>({caseId:r.caseId,changed:r.changed})),null,2));
