export type EvidenceFamily='timing'|'metric'|'melodic'|'recurrence';
export const pillarRuleFamilies={
 'beat-duration':'timing','beat-position':'metric','middle-beat':'metric',
 'rest-entry':'timing','syncopated-sustain':'timing','neighbor-return':'melodic',
 'relative-duration':'timing','downbeat':'metric','following-gap':'timing',
 'step-arrival':'melodic','exact-repeat':'recurrence','variation-match':'recurrence',
} as const satisfies Record<string,EvidenceFamily>;
export type PillarRule=keyof typeof pillarRuleFamilies;
export type PillarEvidence={ruleId:PillarRule;ruleVersion:'pillar-evidence-0.1';family:EvidenceFamily;eventRefs:string[];label:string;provenance:'local-input';reviewEligibility:'unverified'};
export function groupPillarEvidence(evidence:PillarEvidence[]){
 // Conservative grouping, not an independence claim or a probability.
 return [...new Set(evidence.map(e=>e.family))].map(family=>({family,rules:evidence.filter(e=>e.family===family)}));
}

export type EvidenceNode={id:string;revision:string;parents:string[];analysisRefs:string[];observationKey?:string;complete:boolean};
/** Fail-closed dependency audit. No graph result can mutate phrase boundaries. */
export function auditEvidence(graph:EvidenceNode[],roots:string[],revision:string,targetPhraseRun:string,baselineRoots?:string[]){
 const nodes=new Map<string,EvidenceNode>();const errors=new Set<string>();
 for(const node of graph){if(nodes.has(node.id))errors.add(`duplicate-id:${node.id}`);nodes.set(node.id,node);}
 const resolve=(ids:string[])=>{
  const leaves=new Set<string>(),done=new Set<string>(),active=new Set<string>();
  const visit=(id:string)=>{
   if(active.has(id)){errors.add(`cycle:${id}`);return;}if(done.has(id))return;
   const n=nodes.get(id);if(!n){errors.add(`missing:${id}`);return;}
   if(n.revision!==revision)errors.add(`revision:${id}`);
   if(!n.complete)errors.add(`incomplete:${id}`);
   if(n.analysisRefs.includes(targetPhraseRun))errors.add(`phrase-dependent:${id}`);
   if(!n.parents.length&&!n.observationKey)errors.add(`untraced:${id}`);
   active.add(id);for(const p of n.parents)visit(p);active.delete(id);done.add(id);
   if(n.observationKey)leaves.add(n.observationKey);
  };
  ids.forEach(visit);return leaves;
 };
 const observations=resolve(roots);
 // Baseline dependencies are expected to belong to the target analysis, so only
 // primitive evidence roots (not the phrase-result node itself) belong here.
 const used=baselineRoots===undefined?null:resolve(baselineRoots);
 if(!revision||!targetPhraseRun)errors.add('missing-context');
 const blocked=errors.size>0||used===null;
 return {status:errors.size?'blocked':used===null?'baseline-unverified':'verified',issues:[...errors].sort(),
  observations:[...observations].sort(),alreadyUsed:used?[...observations].filter(x=>used.has(x)).sort():[],
  additional:blocked?[]:[...observations].filter(x=>!used!.has(x)).sort(),autoApply:false as const};
}
