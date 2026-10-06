import {DatabaseSync} from 'node:sqlite';
import {statSync} from 'node:fs';
export const CONTOUR_SEED_VERSION='contour-seeds/1';
export const contourString=p=>p.slice(1).map((v,i)=>v===p[i]?'S':v>p[i]?'U':'D').join('');
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)]||1;
const sequence=(a,b)=>{let row=Array.from({length:b.length+1},(_,i)=>i);for(let i=1;i<=a.length;i++){const n=[i];for(let j=1;j<=b.length;j++)n[j]=Math.min(row[j]+1,n[j-1]+1,row[j-1]+Number(a[i-1]!==b[j-1]));row=n}return Math.max(0,1-row[b.length]/Math.max(1,a.length,b.length));};
export function detailedContour(pitches){
 const p=pitches.filter(Number.isFinite),lo=Math.min(...p),range=Math.max(...p)-lo,dirs=contourString(p),steps=p.slice(1).map((v,i)=>Math.abs(v-p[i])),unit=median(steps.filter(x=>x>0));
 const envelope=Array.from({length:16},(_,i)=>{const x=(p.length-1)*i/15,a=Math.floor(x),b=Math.min(p.length-1,a+1);return range?((p[a]*(1-x+a)+p[b]*(x-a))-lo)/range:0;});
 const runs=[];for(const d of dirs){if(runs.at(-1)?.direction===d)runs.at(-1).length++;else runs.push({direction:d,length:1})}
 return {directions:dirs,envelope,runs,relativeSteps:steps.map(x=>x===0?'repeat':x>=unit*2?'large':'small'),flat:range===0,noteCount:p.length};
}
export function compareDetailedContour(a,b){
 if(a.length<4||b.length<4)return {score:0,status:'insufficient-notes'};
 const x=detailedContour(a),y=detailedContour(b),direction=sequence(x.directions,y.directions),envelope=1-x.envelope.reduce((s,v,i)=>s+Math.abs(v-y.envelope[i]),0)/16,runOrder=sequence(x.runs.map(r=>r.direction),y.runs.map(r=>r.direction)),relativeSteps=sequence(x.relativeSteps,y.relativeSteps);
 return {score:100*(.45*direction+.30*envelope+.15*runOrder+.10*relativeSteps),direction:100*direction,envelope:100*envelope,runOrder:100*runOrder,relativeSteps:100*relativeSteps,status:x.flat||y.flat?'low-information':'experimental',calibrated:false};
}
let cached;
/** Complete corpus-derived strings, not a LIMIT prefix of common three-grams.
 * The cap applies after local shape comparison. No metadata or expected IDs used. */
export function contourSeedCandidates(path,sourcePath,pitches,{limit=120,allowed=null,excluded=new Set(),onRank}={}){
 const st=statSync(sourcePath),side=statSync(path),key=path+':'+side.mtimeMs;
 if(cached?.key!==key){const db=new DatabaseSync(path,{readOnly:true}),meta=JSON.parse(db.prepare('SELECT value FROM metadata').get().value);
  if(meta.version!==CONTOUR_SEED_VERSION||meta.sourceSize!==st.size||meta.sourceMtime!==st.mtimeMs||!meta.complete){db.close();throw Error('Stale or incomplete contour sidecar')}
  const rows=db.prepare('SELECT id,contour,pitches FROM streams').all();db.close();cached={key,rows,meta};}
 if(cached.meta.sourceSize!==st.size||cached.meta.sourceMtime!==st.mtimeMs)throw Error('Stale contour sidecar');
 const q=contourString(pitches),patterns=[];for(const width of [7,5])for(let pos=0;pos+width<=q.length;pos++){const token=q.slice(pos,pos+width);if(new Set(token).size>=2)patterns.push({token,pos});}
 if(!patterns.length)return [];
 const best=[];
 for(const row of cached.rows){if((allowed&&!allowed.has(row.id))||excluded.has(row.id))continue;
  const starts=new Map();for(const {token,pos} of patterns){let at=row.contour.indexOf(token);while(at>=0){const start=Math.max(0,at-pos);starts.set(start,(starts.get(start)||0)+token.length);at=row.contour.indexOf(token,at+1)}}
  if(!starts.size)continue;const p=[...Buffer.from(row.pitches,'base64')];let winner;
  for(const [start] of [...starts].sort((a,b)=>b[1]-a[1]||a[0]-b[0]).slice(0,3)){if(start+pitches.length>p.length)continue;const shape=compareDetailedContour(pitches,p.slice(start,start+pitches.length));if(!winner||shape.score>winner.shape.score)winner={id:row.id,start,shape};}
  if(winner&&winner.shape.status==='experimental'&&winner.shape.score>=75)best.push(winner);
 }
 best.sort((a,b)=>b.shape.score-a.shape.score||a.id.localeCompare(b.id));
 if(onRank)try{onRank(best.map((r,i)=>({id:r.id,start:r.start,score:r.shape.score,rank:i+1,returned:i<limit})))}catch{}
 return best.slice(0,limit);
}
