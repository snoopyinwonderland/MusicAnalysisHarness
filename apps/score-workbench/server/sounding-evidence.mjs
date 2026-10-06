// Optional indexed evidence only; never substitutes search duration or boundary input.
export function indexedSoundingEvidence(n){
 if(!Number.isFinite(n.sd)||!Number.isFinite(n.d)||n.sd<n.d||n.sd<=0||!Number.isInteger(n.stm)||n.stm<n.m)return {};
 return {soundingEvidence:{durationQuarters:n.sd,endMeasureOrdinal:n.stm,origin:'validated-source-tie'}};
}
