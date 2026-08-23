# Design Principles

1. **Canonical Music IR stores what is observed, not what is interpreted.**
2. **Interpretation belongs to versioned analysis layers.**
3. **Every analysis claim must be traceable back to score events.**
4. **Human annotations may be absent and must never be required for parsing or deterministic representation.**
5. **Human annotations, when available, must be stored separately from AI hypotheses.**
6. **The same canonical score representation must support analysis, retrieval, arrangement, composition, and evaluation.**
7. **Core schema stability is more important than adding every possible musical concept to the Core.**
8. **New musical concepts should normally be added as extensions or analysis records, not by mutating Core event semantics.**
9. **Uncertainty and competing interpretations are first-class data.**
10. **All ranges use a common time coordinate and stable referencing scheme.**

## 추가 운영 원칙

- 파싱과 결정론적 feature 계산에는 LLM을 사용하지 않는다.
- 원본 표기와 정규화 결과를 함께 보존한다.
- `key_signature`는 관찰이고 `local_key`는 분석이다.
- `lowest_sounding_pitch`는 관찰 가능한 derived evidence이고 `structural_bass`는 분석이다.
- `is_top_pitch_at_onset`은 derived evidence이고 `main_melody`는 분석이다.
- MusicXML `<chord>`는 동시 onset 표기이며 분석적 chord label이 아니다.
- 모든 시간 범위는 `[start, end)`이다.
- float는 표시·통계 편의를 위한 파생값으로만 허용하고 canonical time은 rational을 사용한다.
- parser policy, source hash, schema version, implementation version을 모든 run에 기록한다.
- 모호하거나 손실된 source 정보는 추측하지 않고 `null`, issue 또는 uncertainty로 보존한다.

