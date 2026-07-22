# Legacy 신뢰성 대조 리포트

- 기준(baseline): `legacy/etc/metabolites_step29.xlsx` — 기존 수기 큐레이션 DB
- 대조(reproduced): `data/export/{species}_final.xlsx` — 새 InChIKey 정규화 파이프라인 재현
- 대조 축: 공통 InChIKey 교집합 (full 27자 / skeleton 14자)

분류 라벨(endogenous/exogenous/unverified) 일치율과 외부 식별자·효소 커버리지 일치를 계산한다.

## mouse_feces — 재현 mouse_feces(쥐 분변) vs 기존 step29 (핵심 신뢰성 검증)

### InChIKey full 교집합 (n=489)

- **classification 일치**: 468/489 (95.7%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 479 | 441/479 (92.1%) |
| KEGG | 94 | 72/94 (76.6%) |
| HMDB | 143 | 143/143 (100.0%) |
| ChEBI | 259 | 259/259 (100.0%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 461/489 (94.3%) |
| hmdb_enzymes | 468/489 (95.7%) |
| reactome_catalysts | 478/489 (97.8%) |
| brenda_enzymes | 488/489 (99.8%) |

### InChIKey skeleton 교집합 (n=861)

- **classification 일치**: 787/861 (91.4%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 831 | 449/831 (54.0%) |
| KEGG | 115 | 82/115 (71.3%) |
| HMDB | 181 | 160/181 (88.4%) |
| ChEBI | 302 | 258/302 (85.4%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 811/861 (94.2%) |
| hmdb_enzymes | 819/861 (95.1%) |
| reactome_catalysts | 848/861 (98.5%) |
| brenda_enzymes | 857/861 (99.5%) |

## human — human vs 기존 step29

### InChIKey full 교집합 (n=18)

- **classification 일치**: 18/18 (100.0%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 18 | 16/18 (88.9%) |
| KEGG | 12 | 5/12 (41.7%) |
| HMDB | 14 | 14/14 (100.0%) |
| ChEBI | 14 | 14/14 (100.0%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 11/18 (61.1%) |
| hmdb_enzymes | 16/18 (88.9%) |
| reactome_catalysts | 18/18 (100.0%) |
| brenda_enzymes | 17/18 (94.4%) |

### InChIKey skeleton 교집합 (n=28)

- **classification 일치**: 25/28 (89.3%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 28 | 16/28 (57.1%) |
| KEGG | 15 | 5/15 (33.3%) |
| HMDB | 17 | 14/17 (82.4%) |
| ChEBI | 20 | 14/20 (70.0%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 18/28 (64.3%) |
| hmdb_enzymes | 22/28 (78.6%) |
| reactome_catalysts | 28/28 (100.0%) |
| brenda_enzymes | 26/28 (92.9%) |

## mouse_serum — mouse_serum(쥐 혈청) vs 기존 step29

### InChIKey full 교집합 (n=54)

- **classification 일치**: 48/54 (88.9%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 53 | 47/53 (88.7%) |
| KEGG | 30 | 23/30 (76.7%) |
| HMDB | 33 | 33/33 (100.0%) |
| ChEBI | 37 | 37/37 (100.0%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 46/54 (85.2%) |
| hmdb_enzymes | 47/54 (87.0%) |
| reactome_catalysts | 51/54 (94.4%) |
| brenda_enzymes | 53/54 (98.1%) |

### InChIKey skeleton 교집합 (n=90)

- **classification 일치**: 71/90 (78.9%)

| 외부 ID | 양쪽 보유 | 값 일치 |
|---|---|---|
| PubChem | 88 | 49/88 (55.7%) |
| KEGG | 36 | 23/36 (63.9%) |
| HMDB | 49 | 37/49 (75.5%) |
| ChEBI | 56 | 37/56 (66.1%) |

| 효소 소스 | 유무 플래그 일치 |
|---|---|
| kegg_enzymes | 76/90 (84.4%) |
| hmdb_enzymes | 73/90 (81.1%) |
| reactome_catalysts | 87/90 (96.7%) |
| brenda_enzymes | 87/90 (96.7%) |
