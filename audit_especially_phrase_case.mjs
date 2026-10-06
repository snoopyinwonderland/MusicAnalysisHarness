// Counterfactual diagnosis only. Never writes the source, index or UI analysis.
import {readFileSync} from 'node:fs';
import {analyzePhraseBoundaries} from 'file:///K:/MusicSearch/server/phrase-boundaries.mjs';
const data=JSON.parse(readFileSync(new URL('./reports/reviewer-cases/especially-first-phrase-2026-09-23/api-snapshot.json',import.meta.url),'utf8'));
const work=data.structureWork??data;
const original=analyzePhraseBoundaries(work.notes);
const changed=structuredClone(work.notes);
// Test the notated dotted-half reading; this is not an authorized source repair.
changed[8].durationRatio=3;
const alternative=analyzePhraseBoundaries(changed);
const summarize=a=>({atM3Beat4:a.boundaries[9],atM5Start:a.boundaries[11],firstSupported:a.boundaries.find(b=>b.supported)?.index});
console.log(JSON.stringify({original:summarize(original),notatedDurationCounterfactual:summarize(alternative)},null,2));
