/** Two non-overlapping interval seeds separated by exactly one candidate note.
 * No extra database query; input is existing interval-3 posting evidence.
 * Merely nominates bounded windows, never certifies a match.
 */
export function singleOmissionSeeds(positions,queryLength,{limit=60,perWork=2}={}){
 if(queryLength<8||queryLength>48)return [];
 const output=[];
 for(const [key,left] of positions){
  const at=key.lastIndexOf('\u0000'),id=key.slice(0,at),start=Number(key.slice(at+1));
  if(!Number.isInteger(start)||start<0)continue;
  const right=positions.get(`${id}\u0000${start+1}`);if(!right)continue;
  const pairs=[];for(const l of left)for(const r of right)if(l>=0&&r+3<queryLength&&r>=l+3)pairs.push([l,r]);
  if(!pairs.length)continue;
  const covered=new Set(pairs.flatMap(([l,r])=>[l,l+1,l+2,r,r+1,r+2]));
  output.push({key,start,workId:id,evidence:covered.size,pairs});
 }
 const counts=new Map();return output.sort((a,b)=>b.evidence-a.evidence||a.workId.localeCompare(b.workId)||a.start-b.start).filter(x=>{const n=counts.get(x.workId)||0;if(n>=perWork)return false;counts.set(x.workId,n+1);return true}).slice(0,limit);
}
