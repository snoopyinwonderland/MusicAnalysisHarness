import {it,expect} from 'vitest';
import {selectUpperStructureStream} from './structure-stream.mjs';
const row=(stream_id,p,role=1)=>({id:stream_id,stream_id,role,notes:JSON.stringify(p.map(p=>({p})))});
const xml='<score-partwise><part-list><score-part id="P9"/><score-part id="P1"/></part-list></score-partwise>';
it('uses written part order rather than ID, role score or highest pitch in another part',()=>{
 expect(selectUpperStructureStream([row('P1:1:1',[90]),row('P9:2:2',[40],1),row('P9:1:1',[65],.1)],xml).row.id).toBe('P9:1:1');
});
it('selects the upper whole voice on a shared staff and excludes derived search streams',()=>{
 expect(selectUpperStructureStream([row('P9:1:1',[45,50]),row('P9:1:2',[65,70]),row('P9:1:1:structural',[100])],xml).row.id).toBe('P9:1:2');
});
it('does not manufacture an analysis stream when no source part is available',()=>{
 expect(selectUpperStructureStream([row('unknown:1:1',[70])],xml)).toBeNull();
});
