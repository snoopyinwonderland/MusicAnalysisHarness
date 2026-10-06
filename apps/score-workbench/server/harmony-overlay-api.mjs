import { getWorkScoreSha256 } from './search-api.mjs';
import { appendFileSync, mkdirSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const defaultBase = 'http://127.0.0.1:8766';
const reviewReasons = new Set(['surface_compatible', 'non_chord_tone', 'inversion_or_bass', 'local_key_or_tonicization', 'alignment_or_timeline', 'source_label_suspect', 'cannot_judge']);
const automaticReasons = new Set(['accepted', 'wrong_chord', 'wrong_key', 'wrong_extent', 'non_chord_tone', 'cannot_judge']);
const automaticReviewPath = process.env.MUSICANOTE_HARMONY_REVIEW_PATH || fileURLToPath(new URL('../data/harmony-feedback/automatic-harmony-review.jsonl', import.meta.url));
export function extractBracketedRomanLabels(note) {
  return [...String(note || '').matchAll(/\[([^\]\r\n]{1,64})\]/g)].map(match => match[1].trim()).filter(Boolean);
}
export function createAutomaticHarmonyReviewRecord(request, now = new Date(), id = randomUUID()) {
  const reason = String(request.reason || ''), segment = request.segment, comment = String(request.note || '').slice(0, 2000).trim() || null, romanLabels = extractBracketedRomanLabels(comment), secondaryFunctionCandidate = romanLabels.some(label => label.includes('/'));
  if (!request.workId || !request.streamId || !automaticReasons.has(reason) || !segment?.analysisId || !segment?.span) throw new Error('Invalid automatic harmony feedback');
  return { schemaName: 'musicanote-automatic-harmony-review', schemaVersion: '0.2.0', reviewId: `ahr_${id}`, createdAt: now.toISOString(), workId: String(request.workId), sourceId: request.sourceId ? String(request.sourceId) : null, streamId: String(request.streamId), engineVersion: String(request.engineVersion || 'unknown'), target: { analysisId: String(segment.analysisId), span: segment.span, displayLocation: segment.displayLocation || null }, hypothesis: { selected: segment.selected || null, alternatives: segment.alternatives || [], key: request.keyHypothesis || null, reviewReasons: segment.reviewReasons || [], context: request.context || null }, human: { status: reason, comment, romanLabels, suggestedRomanLabel: romanLabels[0] || null }, caseCandidate: { adjudicationStatus: 'pending', tags: secondaryFunctionCandidate ? ['secondary-function'] : [], retrievalEligible: false }, trainingEligible: false, ruleUpdateEligible: false };
}
const json = (res, status, payload) => {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(payload));
};

export function harmonyOverlayApiPlugin() {
  return {
    name: 'musicanote-harmony-overlay-api',
    configureServer(server) {
      server.middlewares.use('/api/analysis/harmony-overlay', async (req, res) => {
        if (req.method !== 'GET') return json(res, 405, { error: 'Method not allowed' });
        const url = new URL(req.url || '', 'http://localhost');
        const workId = url.searchParams.get('workId') || '';
        const scoreSha256 = getWorkScoreSha256(workId);
        if (!scoreSha256) return json(res, 404, { available: false, reason: 'score_source_unavailable' });
        const base = String(process.env.MUSICANOTE_HARMONY_CATALOG_URL || defaultBase).replace(/\/$/, '');
        try {
          const response = await fetch(`${base}/api/overlay/by-score-sha256/${scoreSha256}`, {
            signal: AbortSignal.timeout(10000),
          });
          const payload = await response.json();
          if (response.status === 404) return json(res, 200, { available: false, reason: 'no_audited_source', scoreSha256 });
          if (response.status === 409) return json(res, 200, { available: false, reason: 'multiple_interpretations', scoreSha256, candidates: payload.candidates || [] });
          if (!response.ok) throw new Error(payload.error || `Harmony catalog ${response.status}`);
          return json(res, 200, { available: true, ...payload });
        } catch (error) {
          return json(res, 200, {
            available: false,
            reason: 'harmony_catalog_unavailable',
            scoreSha256,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      });
      server.middlewares.use('/api/analysis/harmony-feedback', async (req, res) => {
        if (req.method !== 'POST') return json(res, 405, { error: 'Method not allowed' });
        let body = '';
        req.on('data', chunk => { if (body.length <= 16000) body += chunk; });
        req.on('end', async () => {
          try {
            const request = JSON.parse(body || '{}');
            if (request.analysisKind === 'automatic') {
              const record = createAutomaticHarmonyReviewRecord(request);
              mkdirSync(dirname(automaticReviewPath), { recursive: true });
              appendFileSync(automaticReviewPath, `${JSON.stringify(record)}\n`, 'utf8');
              return json(res, 201, { saved: true, reviewId: record.reviewId, record });
            }
            const workId = String(request.workId || ''), catalogRecordId = String(request.catalogRecordId || ''), annotationId = String(request.annotationId || ''), reason = String(request.reason || '');
            const note = String(request.note || '').slice(0, 2000);
            if (!/^[0-9a-f]{16}$/.test(catalogRecordId) || !annotationId || !reviewReasons.has(reason)) return json(res, 400, { error: 'Invalid harmony feedback' });
            const scoreSha256 = getWorkScoreSha256(workId);
            if (!scoreSha256) return json(res, 404, { error: 'Score source unavailable' });
            const base = String(process.env.MUSICANOTE_HARMONY_CATALOG_URL || defaultBase).replace(/\/$/, '');
            const identityResponse = await fetch(`${base}/api/overlay/by-score-sha256/${scoreSha256}`, { signal: AbortSignal.timeout(10000) });
            if (!identityResponse.ok) return json(res, 409, { error: 'Harmony source identity could not be verified' });
            const identity = await identityResponse.json();
            if (identity.catalog_record?.id !== catalogRecordId || !identity.overlay?.items?.some(item => item.annotation_id === annotationId)) return json(res, 409, { error: 'Harmony feedback target does not match this score' });
            const response = await fetch(`${base}/api/reviews/${catalogRecordId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ annotation_id: annotationId, reason, note }), signal: AbortSignal.timeout(10000) });
            const payload = await response.json();
            return json(res, response.status, payload);
          } catch (error) {
            return json(res, 500, { error: error instanceof Error ? error.message : String(error) });
          }
        });
      });
    },
  };
}
