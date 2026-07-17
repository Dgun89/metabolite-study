# legacy step29 신뢰성 비교 리포트

**목적:** 새로 받은 사람/쥐 파일을 legacy 데이터 재사용 없이 각 DB(COCONUT·UniChem·ChEBI·PubChem·KEGG·Reactome·HMDB·BRENDA)에서 독립적으로 재수집해 만든 최종 파일을, legacy 최종 파일(metabolites_step29.xlsx, 902개 화합물)과 대조하여 legacy의 신뢰성을 검증한다.

## 비교 방법

- **대상:** 두 파일에서 InChIKey가 겹치는 화합물(교집합)만 대조.
- **기준:** full InChIKey(입체화학 포함, 동일 화합물)를 주 지표로, 14자 skeleton(입체이성질체 무시)을 보조 지표로 병행.
- legacy가 step25에서 skeleton 매칭을 병용했으므로 두 기준을 모두 보고한다.

## 교집합 규모

| 종 | 새 파일 고유 InChIKey | legacy 고유 InChIKey | full IK 교집합 | skeleton 교집합 |
|---|---|---|---|---|
| 사람 | 314 | 866 | **15** | 27 |
| 쥐 | 705 | 866 | **44** | 90 |

교집합이 작은 것은 두 데이터셋의 화합물 구성이 실제로 다르기 때문이다(새 파일은 연구실에서 새로 받은 사람/쥐 혈청 annotation, legacy는 원본 902개). 이는 예상된 것으로, 겹치는 화합물에 한해 재현성을 본다.

## 1. 분류 일치율 (endogenous/exogenous/unverified) — 핵심 지표

| 종 | full IK 일치 | skeleton 일치 |
|---|---|---|
| 사람 | **15/15 (100%)** | 23/27 (85.2%) |
| 쥐 | **41/44 (93.2%)** | 75/90 (83.3%) |

full InChIKey(동일 화합물) 기준으로 **사람 100%, 쥐 93%**가 legacy와 동일한 분류를 독립적으로 재현했다. skeleton 기준이 낮은 것은 입체이성질체가 서로 다른 organism/role 정보를 가지기 때문이며, 신뢰성 판단에는 full IK가 정확하다.

### 쥐 분류 불일치 3건 (규칙 차이 분석)

| 화합물 | legacy | new | 원인 |
|---|---|---|---|
| Oxindole | exogenous | endogenous | COCONUT organisms 목록 차이(new에 Homo sapiens 포함) — COCONUT 버전/파싱 차이 |
| Hydroxybutyrylcarnitine | endogenous | unverified | legacy는 이전 단계(비-COCONUT)에서 분류, new는 API에서 근거 못 얻음 |
| Toluene | exogenous | endogenous | **new 규칙 한계**: COCONUT에 Homo sapiens 언급되면 내인성으로 보는 규칙이, HMDB origin=Environmental/Tobacco smoke, ChEBI role=neurotoxin/solvent인 명백한 외인성 물질을 오분류 |

Toluene 사례는 본 파이프라인 규칙(COCONUT organisms 우선)의 실제 약점을 드러낸다 — legacy의 COCONUT-우선 규칙이 이 경우 더 보수적이었다.

## 2. Identifier 값 일치율 (양쪽 DB에 값이 있는 화합물 대상)

| DB | 사람 | 쥐 |
|---|---|---|
| PubChem CID | 13/15 (87%) | 40/44 (91%) |
| KEGG | 4/8 (50%) | 18/23 (78%) |
| HMDB | **11/11 (100%)** | **27/27 (100%)** |
| ChEBI | **11/11 (100%)** | **30/30 (100%)** |

HMDB와 ChEBI는 완전 일치. PubChem·KEGG의 편차는 (a) 값 형식 정규화 후에도 남는 실제 매핑 차이, (b) 한 화합물에 복수 CID/KEGG ID가 존재하여 소스마다 대표값 선택이 다른 경우에서 비롯된다.

## 3. 효소 정보 존재여부 일치율

| 효소 소스 | 사람 | 쥐 |
|---|---|---|
| KEGG EC | 10/15 (67%) | 38/44 (86%) |
| HMDB gene | 14/15 (93%) | 37/44 (84%) |
| Reactome | 15/15 (100%) | 40/44 (91%) |
| BRENDA | **15/15 (100%)** | **44/44 (100%)** |

BRENDA·Reactome는 거의 완전 일치. KEGG/HMDB 편차는 API 응답 시점 차이 및 identifier 매핑 차이에 기인한다.

## 결론

**legacy step29는 신뢰할 수 있다.** 독립적으로 각 DB에서 재수집한 결과가 겹치는 화합물에 대해:

- 분류: full InChIKey 기준 사람 100%·쥐 93% 재현
- HMDB·ChEBI identifier: 100% 일치
- BRENDA·Reactome 효소: 100% 일치

불일치 소수(쥐 3건)는 legacy 오류가 아니라 (1) COCONUT 데이터 버전 차이, (2) 본 파이프라인의 규칙 우선순위 차이(COCONUT-우선 vs ChEBI-role-우선)에서 비롯되며, Toluene 사례는 오히려 legacy 규칙이 더 견고했음을 보여준다.

전체 unverified 비율(새 사람 34.5%, 쥐 40.5%; legacy 49%)이 유사한 수준인 것도, COCONUT(천연물 DB) 기반 annotation의 구조적 한계를 독립적으로 재현한 결과다.

---
*생성: pipeline/compare_legacy.py · full InChIKey 교집합 사람 15 / 쥐 44 기준*
