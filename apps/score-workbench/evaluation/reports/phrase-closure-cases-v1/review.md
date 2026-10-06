# 기존 사례 경계 관찰 점검

현재 엔진으로 저장 입력을 재분석한 오프라인 점검. 사용자 정답과의 정확도 평가나 병합 실행이 아니다.

| 사례 | 상태 | 음표 매핑 | 경계 | 박자 환산 가능 | 보호 |
|---|---|---:|---:|---:|---:|
| S-STRUCT-001 | unavailable | -/- | - | - | - |
| S-STRUCT-002 | unavailable | -/- | - | - | - |
| S-STRUCT-003 | unavailable | -/- | - | - | - |
| S-STRUCT-004 | audited | 298/298 | 33 | 33 | 8 |
| S-STRUCT-005 | audited | 444/444 | 29 | 29 | 11 |
| S-STRUCT-006 | audited | 431/431 | 41 | 41 | 15 |

## 보류 사유
- S-STRUCT-001: ["review-snapshot.json"]
- S-STRUCT-002: ["review-snapshot.json"]
- S-STRUCT-003: ["review-snapshot.json"]
- S-STRUCT-004: {}
- S-STRUCT-005: {}
- S-STRUCT-006: {}

보호되지 않은 경계를 잘못된 경계나 병합 대상으로 자동 분류하지 않는다. 원본 파일은 기존 case-assets에 보존하고 hash로 연결했다. 001–003 입력은 현재 snapshot 형식으로 임의 복원하지 않았다.