const clamp=x=>Math.max(0,Math.min(100,x));
const median=a=>{const b=[...a].sort((a,b)=>a-b),i=Math.floor(b.length/2);return b.length%2?b[i]:(b[i-1]+b[i])/2;};
/** One global tempo scale, unclipped durations AND attack intervals. */
export function patternRhythmSimilarity(query,candidate,coverage=1){
 if(!query.length||query.length!==candidate.length)return 0;
 const ratios=[];
 for(let i=0;i<query.length;i++){
  if(!(query[i].durationRatio>0&&candidate[i].durationRatio>0))return 0;
  ratios.push(candidate[i].durationRatio/query[i].durationRatio);
  if(i){const q=query[i].onset-query[i-1].onset,c=candidate[i].onset-candidate[i-1].onset;if(q>0&&c>0)ratios.push(c/q);else return 0;}
 }
 const logs=ratios.map(Math.log2),scale=median(logs),tolerance=Math.log2(1.03);
 const cost=logs.reduce((sum,x)=>sum+Math.min(1,Math.max(0,Math.abs(x-scale)-tolerance)),0)/logs.length;
 return clamp(100*(1-cost)*Math.max(0,Math.min(1,coverage)));
}
export function patternRhythmLocal(melody,rhythm){return clamp(.3*melody+.7*rhythm);}
export function patternRhythmRanking(exact,local,adjustment=0){return exact?100:Math.max(0,Math.min(97,local+Math.max(-1,Math.min(1,adjustment))));}
