# 실제 MusicXML 모음 투입 안내

## 폴더

실제 악보는 저장소의 `corpus/incoming/` 아래에 넣습니다. 원본은 수정하지 않습니다.

```text
corpus/
├── incoming/       새 원본 MusicXML/MXL
├── accepted/       파서 검증을 통과한 원본
├── quarantine/     파싱 실패 또는 구조 검토가 필요한 원본
└── gold/           사람이 분석·검수한 소규모 평가 세트
```

## 첫 투입 권장량

처음에는 10~20곡이면 충분합니다. 다음 사례가 섞이면 좋습니다.

- 독주 선율, 피아노, 다성부/다악장 악보
- 마디를 넘는 타이와 여러 voice
- pickup, 박자표·조표 변화, 반복기호와 1·2번 엔딩
- 분산화음, 계류음, 페달음, 반음계 진행
- 중간 dominant와 half cadence
- secondary dominant, tonicization, modulation
- 프레이즈와 모티프 경계가 애매한 사례

## 파일과 메타데이터

`*.musicxml`, `*.xml`, `*.mxl`을 사용할 수 있습니다. 파일명은 유지하되, 가능하면 별도 `corpus_manifest.csv`에 다음을 기록합니다.

```text
file_name,title,composer,work,movement,edition,source_url,license,analysis_status,notes
```

저작권과 출처가 불명확한 파일은 공개 데이터셋이나 재배포 산출물에 포함하지 않습니다.

## 처리 원칙

1. 원본 checksum을 기록합니다.
2. `parse` 단계에서 Canonical IR과 validation report를 만듭니다.
3. 오류 파일은 자동 수정하지 않고 quarantine으로 분류합니다.
4. warning은 사람이 검토한 뒤 accepted 여부를 정합니다.
5. Gold Set은 전체 corpus와 분리하며 자기 개선 루프가 수정하지 못하게 합니다.

