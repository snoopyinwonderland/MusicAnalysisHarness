import type {PillarCandidate} from './pillarCandidates';
export type PillarView='surface'|'shared';
// A review filter, not another reduction algorithm or structural ranking.
export function selectPillarView<T extends PillarCandidate&{origin?:string}>(candidates:T[],view:PillarView):T[]{
 return view==='surface'?candidates:candidates.filter(c=>c.origin!=='phrase-hint-only'&&c.correspondences.length>0);
}
