export const structuralKinds=['passing-insertion','neighbor-insertion','repeat-split','internal-rhythm','combined'];
export function structuralVariation(original,kind,protectedIds=[]){
 const events=structuredClone(original),protectedSet=new Set(protectedIds),changes=[];
 const sites=()=>events.map((e,i)=>({e,i,next:events[i+1]})).filter(({e,next})=>e.kind==='note'&&e.durationRatio>=.25&&next?.kind==='note');
 const split=(site,pitches,label)=>{
  const {e,i}=site,before=e.durationRatio,d=before/(pitches.length+1);e.durationRatio=d;
  const added=pitches.map((pitchMidi,j)=>({id:`${e.id}-${label}-${j}`,kind:'note',pitchMidi,durationRatio:d,originId:e.id,generated:true}));
  events.splice(i+1,0,...added);changes.push({type:label,eventId:e.id,originalDuration:before,addedIds:added.map(n=>n.id)});
 };
 const passing=()=>{const s=sites().find(({e,next})=>[2,4].includes(Math.abs(next.pitchMidi-e.pitchMidi)));if(!s)throw Error('No passing insertion site');split(s,[(s.e.pitchMidi+s.next.pitchMidi)/2],'passing')};
 const neighbor=()=>{const s=sites().find(({e})=>e.durationRatio>=.5);if(!s)throw Error('No neighbor site');split(s,[s.e.pitchMidi+1,s.e.pitchMidi],'neighbor')};
 const repeat=()=>{const s=sites()[0];if(!s)throw Error('No repeat site');split(s,[s.e.pitchMidi],'repeat')};
 const rhythm=()=>{const s=sites().find(({e,next})=>!protectedSet.has(next.id)&&next.durationRatio>=.25);if(!s)throw Error('No internal rhythm site');const before=[s.e.durationRatio,s.next.durationRatio],delta=s.next.durationRatio/2;s.e.durationRatio+=delta;s.next.durationRatio-=delta;changes.push({type:'internal-rhythm',ids:[s.e.id,s.next.id],before,after:[s.e.durationRatio,s.next.durationRatio]})};
 if(kind==='passing-insertion')passing();else if(kind==='neighbor-insertion')neighbor();else if(kind==='repeat-split')repeat();else if(kind==='internal-rhythm')rhythm();else if(kind==='combined'){passing();neighbor()}else throw Error('Unknown kind');
 const timeline=xs=>{let t=0;return new Map(xs.map(e=>{const n=[e.id,{onset:t,pitch:e.pitchMidi}];t+=e.durationRatio;return n}))};
 const a=timeline(original),b=timeline(events);
 for(const id of protectedSet)if(!a.has(id)||!b.has(id)||Math.abs(a.get(id).onset-b.get(id).onset)>1e-8||a.get(id).pitch!==b.get(id).pitch)throw Error('Protected event changed');
 if(Math.abs(original.reduce((s,e)=>s+e.durationRatio,0)-events.reduce((s,e)=>s+e.durationRatio,0))>1e-8)throw Error('Duration drift');
 return {events,changes,protectedIds:[...protectedSet],sourceToQueryMap:original.map(e=>({sourceId:e.id,queryIds:events.filter(n=>n.id===e.id||n.originId===e.id).map(n=>n.id)}))};
}
