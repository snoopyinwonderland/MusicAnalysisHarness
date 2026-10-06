/** Experimental read-only SQL aggregation. Preserve each legacy LIMIT prefix and
 * Map insertion order: ties in downstream sorting rely on first encounter order.
 * No new index, row cap, candidate pruning or score is introduced here. */
export function aggregateSqlSeeds(db,requests){
 if(!requests.length)return empty();
 if(requests.length>400)return null; // SQLite compound-select bound: use legacy path.
 for(const r of requests)if(!Number.isSafeInteger(r.pos)||r.pos<0||!Number.isSafeInteger(r.limit)||r.limit<0)throw Error('Invalid seed request');
 const tokens=new Map();for(const r of requests){const prior=tokens.get(r.token);if(prior)prior.limit=Math.max(prior.limit,r.limit);else tokens.set(r.token,{id:tokens.size,limit:r.limit})}
 const stride=Math.max(...requests.map(r=>r.limit))+1,args=[],ctes=[];
 for(const [token,{id,limit}] of tokens){
  // Inner SELECT is deliberately identical to the established query. Do not add
  // ORDER BY / covering-index hints without a separately verified migration.
  ctes.push(`t${id} AS MATERIALIZED (SELECT work_id,pos FROM grams WHERE token=? LIMIT ?), p${id} AS MATERIALIZED (SELECT work_id,pos,row_number() OVER () rn FROM t${id})`);args.push(token,limit);
 }
 const branches=requests.map((r,i)=>{const t=tokens.get(r.token),short=Number(r.token.startsWith('i:')),long=Number(r.token.startsWith('i5:')),interval=short||long,rhythm=Number(r.token.startsWith('r:')),contour=Number(r.token.startsWith('c:'));
 return `SELECT work_id,max(0,pos-${r.pos}) start,${i*stride}+rn seq,${i} gi,${r.pos} qp,${long?50:interval?3:1} weight,${interval} ii,${short} si,${rhythm} rr,${contour} cc FROM p${t.id} WHERE rn<=${r.limit}`});
 const sql=`WITH ${ctes.join(',')}, entries AS MATERIALIZED (${branches.join(' UNION ALL ')})
 SELECT 0 type,work_id,start,SUM(weight) hits,SUM(ii) intervals,SUM(weight*ii) intervalWeight,SUM(rr) rhythm,
 MIN(seq) seq,MIN(CASE WHEN ii=1 THEN seq END) iseq,MIN(CASE WHEN rr=1 THEN seq END) rseq,
 json_group_array(json_array(qp,seq)) FILTER (WHERE si=1) shorts
 FROM entries GROUP BY work_id,start
 UNION ALL
 SELECT 1,work_id,0,COUNT(DISTINCT gi),0,0,0,MIN(seq),NULL,NULL,'[]' FROM entries WHERE cc=1 GROUP BY work_id`;
 const rows=db.prepare(sql).all(...args),result=empty(),hits=rows.filter(r=>r.type===0),shorts=[];
 const key=r=>`${r.work_id}\u0000${r.start}`;
 for(const r of [...hits].sort((a,b)=>a.seq-b.seq)){result.hits.set(key(r),r.hits);for(const [pos,seq] of JSON.parse(r.shorts))shorts.push({key:key(r),pos,seq})}
 for(const r of hits.filter(r=>r.intervals).sort((a,b)=>a.iseq-b.iseq)){result.intervalHits.set(key(r),r.intervals);result.intervalSeedEvidence.set(key(r),r.intervalWeight)}
 for(const r of hits.filter(r=>r.rhythm).sort((a,b)=>a.rseq-b.rseq))result.rhythmSeedEvidence.set(key(r),r.rhythm);
 for(const r of rows.filter(r=>r.type===1).sort((a,b)=>a.seq-b.seq))result.contourWorkEvidence.set(r.work_id,r.hits);
 for(const r of shorts.sort((a,b)=>a.seq-b.seq)){
  if(!result.interval3Seeds.has(r.pos))result.interval3Seeds.set(r.pos,[]);result.interval3Seeds.get(r.pos).push(r.key);
  if(!result.splitIntervalPositions.has(r.key))result.splitIntervalPositions.set(r.key,new Set());result.splitIntervalPositions.get(r.key).add(r.pos);
 }
 // Legacy inserts a short-gram position even when the posting prefix is empty.
 const ordered=new Map();for(const r of requests)if(r.token.startsWith('i:'))ordered.set(r.pos,result.interval3Seeds.get(r.pos)??[]);result.interval3Seeds=ordered;
 result.profile={sqlRows:rows.length,shortReferences:shorts.length,tokenCount:tokens.size};return result;
}
function empty(){return {hits:new Map(),intervalHits:new Map(),intervalSeedEvidence:new Map(),rhythmSeedEvidence:new Map(),contourWorkEvidence:new Map(),interval3Seeds:new Map(),splitIntervalPositions:new Map(),profile:{sqlRows:0,shortReferences:0,tokenCount:0}}}
