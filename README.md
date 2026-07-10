# metabolite-study

대사체 데이터의 화합물 주석(annotation) 및 내인성/외인성(endogenous/exogenous) 분류 프로젝트.

## 프로젝트 구조

```
metabolite-study/
├─ data/                  작업 데이터 (사람·쥐)
│   ├─ reference/         COCONUT 전체 CSV, HMDB XML 등 참조용 다운로드 파일
│   ├─ human/             사람 혈청 (raw → interim → final)
│   └─ mouse/             쥐 혈청 (raw → interim → final)
├─ pipeline/              DB-legacy 재현 파이프라인 (공통 코드, SPECIES 전환)
│   ├─ config.py          경로·상수 (get_paths(species))
│   ├─ collect_identifiers.py   InChIKey 기반 identifier 교차수집 (UniChem/ChEBI/PubChem)
│   ├─ build_hmdb_index.py      HMDB 로컬 XML 스트리밍 인덱스
│   ├─ classify.py              규칙 기반 내인성/외인성 분류
│   ├─ collect_enzymes.py       KEGG EC + Reactome catalyst 수집
│   ├─ collect_brenda.py        BRENDA SOAP 효소(EC) 수집
│   ├─ assemble.py              종별 최종 파일 조립 (3시트)
│   └─ compare_legacy.py        legacy step29 신뢰성 비교
├─ scripts/               HTML 추출 등 전처리 코드
├─ legacy/                기존 파이프라인 (step1~29, COCONUT 902 화합물 DB)
├─ format_excel.py        엑셀 3시트(Data/Legend/Summary) 서식 도구
└─ validate.py            데이터 검증 도구
```

## 현재 작업 — 새 사람·쥐 파일의 DB 직접 취합 + legacy 신뢰성 검증

교수님으로부터 새로 받은 사람/쥐 혈청 대사체(COCONUT으로 주석된 화합물)에 대해,
legacy 파이프라인과 동일한 방식으로 **각 DB에 직접 접근**하여 최종 파일을 만들고,
legacy 최종 파일(step29)과 비교하여 legacy의 신뢰성을 확인한다.

핵심 원칙: **legacy 데이터를 재사용하지 않고 각 DB에서 직접 수집** → 독립적 재현으로 신뢰성 검증.

### 파이프라인 (pipeline/, SPECIES=human|mouse 전환)

1. **COCONUT 로컬 조인** — 원본 xlsx의 CNP id(버전 접미사 제거한 base id)로
   COCONUT 전체 CSV(738,827행)와 조인 → SMILES/InChIKey/InChI/formula/organisms/np_classifier.
   매칭률 사람 453/455(99.6%), 쥐 868/878(98.9%). **API 0회.**
2. **identifier 교차수집** — 고유 InChIKey(914개) 기준 병렬 수집:
   - UniChem POST `/unichem/api/v1/compounds` → HMDB id
   - ChEBI es_search + compound detail → chebi_id, roles, KEGG/HMDB accession
   - PubChem PUG REST → CID (fallback)
   - 커버리지: PubChem 97%, ChEBI 40%, HMDB 26%, KEGG 16%
3. **HMDB 로컬 인덱스** — 6.1GB XML을 iterparse 스트리밍, 대상 InChIKey만 추출(221개):
   ontology Source(Endogenous/Food/Plant…), protein gene_name, biospecimen.
4. **내인성/외인성 분류 (규칙 기반)** — 우선순위:
   ChEBI role 'human metabolite' → HMDB source Endogenous → COCONUT organisms Homo sapiens
   → (외인성) HMDB food/drug/plant, ChEBI roles만 있고 human 아님, organisms 비인간
   → (unverified) 근거 없음. 각 행에 classification_basis 기록.
5. **효소 수집** — KEGG `link/enzyme/cpd:{id}` EC, Reactome mapping→catalystActivity, HMDB gene.
6. **BRENDA 효소 수집** — SOAP(zeep), 화합물명 → getLigandStructureIdByCompoundName
   → getSubstrate → EC. 인증 sha256(password), rate ≤1 req/sec.
7. **종별 최종 파일 조립** — format_excel.py로 Data/Legend/Summary 3시트 생성.
8. **legacy step29 비교** — 공통 InChIKey 교집합에서 분류·identifier·효소 일치율 대조.

각 종의 결과는 data/{species}/final/{species}_final.xlsx.

## 데이터 처리 원칙

- raw/는 원본 보존, 수정하지 않음
- interim/은 중간 산출물, 언제든 재생성 가능 (parquet 체크포인트)
- final/은 분석·공유용 최종 결과 (3시트 xlsx)
- 코드는 종(human/mouse) 무관하게 공통 사용, SPECIES 설정으로 전환

## 진행 로그

- 2026-07-08 교수님으로부터 새 사람/쥐 파일 수신 (COCONUT annotation).
- 2026-07-10 파이프라인 1~7단계 완료:
  - 사람 455개 (endo 104 / exo 194 / unverified 157), 효소 정보 129개(28.4%)
  - 쥐 878개 (endo 181 / exo 341 / unverified 356), 효소 정보 218개(24.8%)
  - identifier 병렬 수집 914 InChIKey (오류 0), BRENDA EC 매칭 172개(이름 기준)
- 2026-07-10 8단계 legacy step29 신뢰성 비교 완료 (공통 InChIKey 교집합):
  - full InChIKey 교집합 사람 15 / 쥐 44
  - **분류 일치 사람 15/15(100%), 쥐 41/44(93.2%)**
  - HMDB·ChEBI identifier 100% 일치, BRENDA·Reactome 효소 100% 일치
  - 쥐 불일치 3건은 COCONUT 버전차/규칙 우선순위차(Toluene은 legacy가 더 견고)
  - **결론: legacy step29 신뢰성 검증됨** — final/comparison_report.md 참조

## 기존 작업 (legacy)

legacy/는 COCONUT 기반 902 화합물 DB 구축 파이프라인(step1~29).
최종 분류: endogenous 143, exogenous 319, unverified 440. 상세는 legacy/README.md 참고.

## 노트

- RESEARCHNOTE.md — 연구 결정과 근거
- STUDYNOTE.md — 코드 메커니즘
