# metabolite-study

> Compound annotation and endogenous/exogenous classification for metabolite data (human and mouse serum).
> 대사체 데이터의 화합물 주석(annotation) 및 내인성/외인성(endogenous/exogenous) 분류 프로젝트.

**Language / 언어: [English](#english) · [한국어](#한국어)**

## Related repositories / 관련 저장소

- [DarkMet](https://github.com/dgun89/DarkMet) — classifies the *unverified* (dark metabolome) compounds this project surfaces, predicting origin from structure (SMILES) alone. / 이 프로젝트가 드러낸 미검증(dark metabolome) 화합물을 구조(SMILES)만으로 기원 예측·분류.
- [lipidomics-ai-agent](https://github.com/dgun89/lipidomics-ai-agent) — reuses the DB built here (902 compounds, 3,491 enzyme relations) for RAG/GraphRAG experiments on grounding and identifier reliability. / 여기서 구축한 DB(902개 화합물, 3,491개 효소 관계)를 RAG/GraphRAG 실험에 재사용.

---

## English

### Project structure

```
metabolite-study/
├─ data/                    working data (human · mouse)
│  ├─ reference/            reference downloads (full COCONUT CSV, HMDB XML, etc.)
│  ├─ human/                human serum (raw → interim → final)
│  └─ mouse/                mouse serum (raw → interim → final)
├─ pipeline/                DB-from-scratch pipeline (shared code, switch by SPECIES)
│  ├─ config.py             paths & constants (get_paths(species))
│  ├─ collect_identifiers.py  InChIKey-based identifier cross-collection (UniChem/ChEBI/PubChem)
│  ├─ build_hmdb_index.py   local HMDB XML streaming index
│  ├─ classify.py           rule-based endogenous/exogenous classification
│  ├─ collect_enzymes.py    KEGG EC + Reactome catalyst collection
│  ├─ collect_brenda.py     BRENDA SOAP enzyme (EC) collection
│  ├─ assemble.py           per-species final file assembly (3 sheets)
│  ├─ compare_legacy.py     reliability comparison against legacy step29
│  └─ mmmdb/                MMMDB bridge + MSI confidence curation (mouse)
├─ scripts/                 preprocessing (HTML extraction, species-overlap check, dedup, etc.)
├─ docs/                    curation report + effect figure
├─ legacy/                  original pipeline (step1–29, COCONUT 902-compound DB)
├─ format_excel.py          Excel 3-sheet (Data/Legend/Summary) formatting tool
└─ validate.py              data validation tool
```

### Current work — direct DB collection for new human/mouse files + legacy reliability check

For newly received human/mouse serum metabolites (COCONUT-annotated), the pipeline accesses each database directly — the same way as the legacy pipeline — to build the final files, then compares them against the legacy final file (step29) to validate the legacy's reliability.

Core principle: do **not** reuse legacy data. Collect from each database directly, so an independent reproduction verifies reliability.

#### Pipeline (`pipeline/`, switch with `SPECIES=human|mouse`)

1. **COCONUT local join** — join the source xlsx CNP ids (base id, version suffix stripped) against the full COCONUT CSV (738,827 rows) → SMILES / InChIKey / InChI / formula / organisms / np_classifier. Match rate: human 453/455 (99.6%), mouse 868/878 (98.9%). Zero API calls.
2. **Identifier cross-collection** — parallel collection keyed on unique InChIKeys (914):
   - UniChem `POST /unichem/api/v1/compounds` → HMDB id
   - ChEBI `es_search` + compound detail → chebi_id, roles, KEGG/HMDB accession
   - PubChem PUG REST → CID (fallback)
   - Coverage: PubChem 97%, ChEBI 40%, HMDB 26%, KEGG 16%
3. **HMDB local index** — stream the 6.1 GB XML with `iterparse`, extracting only target InChIKeys (221): ontology Source (Endogenous/Food/Plant…), protein gene_name, biospecimen.
4. **Endogenous/exogenous classification (rule-based)** — priority: ChEBI role `human metabolite` → HMDB source Endogenous → COCONUT organisms *Homo sapiens* → (exogenous) HMDB food/drug/plant, ChEBI roles without human, non-human organisms → (unverified) no basis. Each row records its `classification_basis`.
5. **Enzyme collection** — KEGG `link/enzyme/cpd:{id}` EC, Reactome mapping → catalystActivity, HMDB gene.
6. **BRENDA enzyme collection** — SOAP (zeep), compound name → `getLigandStructureIdByCompoundName` → `getSubstrate` → EC. Auth `sha256(password)`, rate ≤ 1 req/sec.
7. **Per-species final assembly** — `format_excel.py` builds the Data/Legend/Summary 3-sheet workbook.
8. **Legacy step29 comparison** — on the common InChIKey intersection, cross-check classification, identifiers, and enzymes.

Each species' result: `data/{species}/final/{species}_final.xlsx`.

#### MMMDB bridge + MSI confidence curation (`pipeline/mmmdb/`, mouse)

Non-target annotations carry species bias: human-centric databases (HMDB, ChEBI) mislabel mouse metabolites, and every feature needs a stated confidence. Two curation stages address this on the mouse result.

- **Stage 3.5 — MMMDB bridge.** Cross-reference against MMMDB (Mouse Multiple Tissue Metabolome Database; Sugimoto et al., *NAR* 2012; CE-TOFMS, 11 tissues, 219 metabolites). Build a local reference table (296 compounds; name → KEGG → InChIKey resolution, matchable 228), then match mouse rows by priority full InChIKey → InChIKey14 skeleton → KEGG → ChEBI. A new **E0** rule (highest priority) reclassifies compounds detected in real mouse tissues as endogenous; original labels are preserved and every change is logged. Result: **53/878 matched (6.0%)**, **12 reclassified** (exogenous→endogenous 10, unverified→endogenous 2), endogenous 181 → 193. Corrects mouse amino acids (Valine, Isoleucine, Phenylalanine…), Pantothenate, and others wrongly flagged exogenous by human criteria.
- **Stage 4.5 — MSI confidence grade.** Auto-assign per-compound annotation confidence from independent multi-database evidence: **L2** probable (structure + ≥2 independent DB IDs), **L3** tentative (structure, ≤1 DB), **L4** formula only, **L5** unknown. L1 is not assigned (non-target). Result: **L2 255 / L3 613 / L5 10** (L5 = peptide fragments with no identifier).
- **Legacy step30 comparison.** Against the newer legacy output: full-InChIKey agreement 52/56 (92.9%), skeleton agreement 95/114 (83.3%); MMMDB corrects 4 compounds that legacy still mislabels.

Output: `mouse_final_curated.xlsx` (878 × 27, 3-sheet layout preserved), `data/mouse/reference/mmmdb_reference.parquet`, and `docs/` (report + figure). See `docs/mmmdb_curation_report.md`.

### Data handling principles

- `raw/` is preserved as-is, never modified.
- `interim/` holds intermediate outputs, regenerable at any time (parquet checkpoints).
- `final/` holds analysis/sharing outputs (3-sheet xlsx).
- Code is species-agnostic (human/mouse); switch via the `SPECIES` setting.

### Progress log

- **2026-07-08** — received new human/mouse files from the lab (COCONUT annotation).
- **2026-07-10** — pipeline steps 1–7 complete:
  - human 455 (endo 104 / exo 194 / unverified 157), enzyme info 129 (28.4%)
  - mouse 878 (endo 181 / exo 341 / unverified 356), enzyme info 218 (24.8%)
  - parallel identifier collection over 914 InChIKeys (0 errors), BRENDA EC matches 172 (by name)
- **2026-07-10** — step 8, legacy step29 reliability comparison (common InChIKey intersection):
  - full InChIKey intersection: human 15 / mouse 44
  - classification agreement: human 15/15 (100%), mouse 41/44 (93.2%)
  - HMDB & ChEBI identifiers 100% match; BRENDA & Reactome enzymes 100% match
  - the 3 mouse mismatches are COCONUT version differences / rule-priority differences (for Toluene, legacy is more robust)
  - Conclusion: legacy step29 reliability verified
- **2026-07-17** — mouse MMMDB bridge + MSI confidence curation (`pipeline/mmmdb/`):
  - MMMDB local reference built from 44 archived tissue CSVs (296 compounds, 228 matchable via name→KEGG→InChIKey)
  - cross-reference 53/878 (6.0%); E0 reclassification 12 (exo→endo 10, unverified→endo 2), endogenous 181 → 193
  - MSI grades assigned: L2 255 / L3 613 / L5 10
  - legacy step30 comparison: full InChIKey 52/56 (92.9%), skeleton 95/114 (83.3%); MMMDB corrects 4 legacy mislabels
  - output `mouse_final_curated.xlsx` (878 × 27, 3-sheet), see `docs/mmmdb_curation_report.md`
- **2026-07-17** — human/mouse species-overlap check (`scripts/02_find_species_overlap.py`):
  - match human vs mouse final files by InChIKey (full + 14-char skeleton), same rule as `compare_legacy.py`
  - valid InChIKeys: human 453 / mouse 868; full-InChIKey common (same compound) **105** (human 23.2%, mouse 12.1%), skeleton-only 0
  - classification agreement on the 105 shared compounds: **105/105 (100%)** — endogenous/exogenous/unverified fully consistent across species
  - output `overlap_human_mouse.csv`
- **2026-07-17** — deduplicate final files (`scripts/03_deduplicate_final.py`):
  - the latest final files carried repeated compounds (fully-identical rows sharing the same `Database ID`)
  - remove duplicates by `Database ID` (keep first); 3-sheet layout preserved, Summary counts recomputed
  - human 455 → **316** (removed 139); mouse 878 → **717** (removed 161)
  - InChIKey collisions with distinct `Database ID` (stereoisomers, e.g. DL-Threonine/Threonine, Leucine/DL-Leucine) are kept, not removed
  - output `{species}_final_dedup.xlsx` (original files untouched)

### Legacy

`legacy/` is the COCONUT-based 902-compound DB pipeline (step1–29). Final classification: endogenous 143, exogenous 319, unverified 440. See `legacy/README.md` for details.

---

## 한국어

### 프로젝트 구조

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
│   ├─ compare_legacy.py        legacy step29 신뢰성 비교
│   └─ mmmdb/                   MMMDB 브릿지 + MSI 신뢰도 큐레이션 (쥐)
├─ scripts/               HTML 추출·종간 겹침 확인·중복 제거 등 전처리 코드
├─ docs/                  큐레이션 리포트 + 효과 그림
├─ legacy/                기존 파이프라인 (step1~29, COCONUT 902 화합물 DB)
├─ format_excel.py        엑셀 3시트(Data/Legend/Summary) 서식 도구
└─ validate.py            데이터 검증 도구
```

### 현재 작업 — 새 사람·쥐 파일의 DB 직접 취합 + legacy 신뢰성 검증

연구실에서 새로 받은 사람/쥐 혈청 대사체(COCONUT으로 주석된 화합물)에 대해, legacy 파이프라인과 동일한 방식으로 **각 DB에 직접 접근**하여 최종 파일을 만들고, legacy 최종 파일(step29)과 비교하여 legacy의 신뢰성을 확인한다.

핵심 원칙: **legacy 데이터를 재사용하지 않고 각 DB에서 직접 수집** → 독립적 재현으로 신뢰성 검증.

#### 파이프라인 (pipeline/, SPECIES=human|mouse 전환)

1. **COCONUT 로컬 조인** — 원본 xlsx의 CNP id(버전 접미사 제거한 base id)로 COCONUT 전체 CSV(738,827행)와 조인 → SMILES/InChIKey/InChI/formula/organisms/np_classifier. 매칭률 사람 453/455(99.6%), 쥐 868/878(98.9%). **API 0회.**
2. **identifier 교차수집** — 고유 InChIKey(914개) 기준 병렬 수집:
   - UniChem POST `/unichem/api/v1/compounds` → HMDB id
   - ChEBI es_search + compound detail → chebi_id, roles, KEGG/HMDB accession
   - PubChem PUG REST → CID (fallback)
   - 커버리지: PubChem 97%, ChEBI 40%, HMDB 26%, KEGG 16%
3. **HMDB 로컬 인덱스** — 6.1GB XML을 iterparse 스트리밍, 대상 InChIKey만 추출(221개): ontology Source(Endogenous/Food/Plant…), protein gene_name, biospecimen.
4. **내인성/외인성 분류 (규칙 기반)** — 우선순위: ChEBI role 'human metabolite' → HMDB source Endogenous → COCONUT organisms Homo sapiens → (외인성) HMDB food/drug/plant, ChEBI roles만 있고 human 아님, organisms 비인간 → (unverified) 근거 없음. 각 행에 classification_basis 기록.
5. **효소 수집** — KEGG `link/enzyme/cpd:{id}` EC, Reactome mapping→catalystActivity, HMDB gene.
6. **BRENDA 효소 수집** — SOAP(zeep), 화합물명 → getLigandStructureIdByCompoundName → getSubstrate → EC. 인증 sha256(password), rate ≤1 req/sec.
7. **종별 최종 파일 조립** — format_excel.py로 Data/Legend/Summary 3시트 생성.
8. **legacy step29 비교** — 공통 InChIKey 교집합에서 분류·identifier·효소 일치율 대조.

각 종의 결과는 data/{species}/final/{species}_final.xlsx.

#### MMMDB 브릿지 + MSI 신뢰도 큐레이션 (`pipeline/mmmdb/`, 쥐)

논타겟 어노테이션은 종 편향을 갖는다. 인간 중심 DB(HMDB, ChEBI)는 쥐 대사체를 오분류하고, 모든 피처에는 신뢰도가 명시되어야 한다. 쥐 결과에 두 큐레이션 단계를 적용한다.

- **Stage 3.5 — MMMDB 브릿지.** MMMDB(Mouse Multiple Tissue Metabolome Database; Sugimoto et al., *NAR* 2012; CE-TOFMS, 11조직, 219 대사체)와 교차참조. 로컬 참조 테이블(296 화합물; 이름 → KEGG → InChIKey 해석, 매칭 가능 228)을 만들고, 우선순위 full InChIKey → InChIKey14 골격 → KEGG → ChEBI로 쥐 행을 매칭한다. 신규 **E0** 규칙(최우선)은 실제 쥐 조직에서 검출된 화합물을 내인성으로 재분류하며, 원본 분류는 보존하고 변경 이력을 기록한다. 결과: **53/878 매칭(6.0%)**, **12개 재분류**(외인성→내인성 10, unverified→내인성 2), 내인성 181 → 193. 인간 기준으로 외인성 오분류된 쥐 아미노산(Valine, Isoleucine, Phenylalanine…), Pantothenate 등을 교정.
- **Stage 4.5 — MSI 신뢰도 등급.** 독립 다중 DB 근거로 화합물별 어노테이션 신뢰도를 자동 부여: **L2** probable(구조 + 독립 DB ID ≥2), **L3** tentative(구조, ≤1 DB), **L4** formula, **L5** unknown. L1은 비표적이라 부여하지 않음. 결과: **L2 255 / L3 613 / L5 10** (L5 = 식별자 없는 펩타이드 조각).
- **legacy step30 비교.** 최신 legacy 산출물 대비: full InChIKey 일치 52/56(92.9%), 골격 일치 95/114(83.3%); legacy가 여전히 오분류하는 4개를 MMMDB가 교정.

산출: `mouse_final_curated.xlsx`(878 × 27, 3시트 유지), `data/mouse/reference/mmmdb_reference.parquet`, `docs/`(리포트 + 그림). 상세는 `docs/mmmdb_curation_report.md`.

### 데이터 처리 원칙

- raw/는 원본 보존, 수정하지 않음
- interim/은 중간 산출물, 언제든 재생성 가능 (parquet 체크포인트)
- final/은 분석·공유용 최종 결과 (3시트 xlsx)
- 코드는 종(human/mouse) 무관하게 공통 사용, SPECIES 설정으로 전환

### 진행 로그

- 2026-07-08 연구실에서 새 사람/쥐 파일 수신 (COCONUT annotation).
- 2026-07-10 파이프라인 1~7단계 완료:
  - 사람 455개 (endo 104 / exo 194 / unverified 157), 효소 정보 129개(28.4%)
  - 쥐 878개 (endo 181 / exo 341 / unverified 356), 효소 정보 218개(24.8%)
  - identifier 병렬 수집 914 InChIKey (오류 0), BRENDA EC 매칭 172개(이름 기준)
- 2026-07-10 8단계 legacy step29 신뢰성 비교 완료 (공통 InChIKey 교집합):
  - full InChIKey 교집합 사람 15 / 쥐 44
  - **분류 일치 사람 15/15(100%), 쥐 41/44(93.2%)**
  - HMDB·ChEBI identifier 100% 일치, BRENDA·Reactome 효소 100% 일치
  - 쥐 불일치 3건은 COCONUT 버전차/규칙 우선순위차(Toluene은 legacy가 더 견고)
  - **결론: legacy step29 신뢰성 검증됨**
- 2026-07-17 쥐 MMMDB 브릿지 + MSI 신뢰도 큐레이션 (`pipeline/mmmdb/`):
  - 아카이브된 조직 CSV 44개로 MMMDB 로컬 참조 구축(296 화합물, 이름→KEGG→InChIKey로 228개 매칭 가능)
  - 교차참조 53/878(6.0%); E0 재분류 12개(외인성→내인성 10, unverified→내인성 2), 내인성 181 → 193
  - MSI 등급 부여: **L2 255 / L3 613 / L5 10**
  - legacy step30 비교: full InChIKey 52/56(92.9%), 골격 95/114(83.3%); MMMDB가 legacy 오분류 4건 교정
  - 산출 `mouse_final_curated.xlsx`(878 × 27, 3시트), 상세는 `docs/mmmdb_curation_report.md`
- 2026-07-17 사람/쥐 종간 겹침 확인 (`scripts/02_find_species_overlap.py`):
  - 사람/쥐 최종 파일을 InChIKey(full + 14자 skeleton)로 매칭, `compare_legacy.py`와 동일 규칙
  - 유효 InChIKey 사람 453 / 쥐 868; full InChIKey 완전 일치(동일 화합물) **105건**(사람 23.2%, 쥐 12.1%), skeleton만 일치 0건
  - 겹치는 105건의 분류 일치: **105/105(100%)** — endogenous/exogenous/unverified가 종간 완전 일관
  - 산출 `overlap_human_mouse.csv`
- 2026-07-17 최종 파일 중복 제거 (`scripts/03_deduplicate_final.py`):
  - 최신 최종 파일에 같은 화합물이 반복된 행(같은 `Database ID`의 완전 동일 행)이 남아 있었음
  - `Database ID` 기준으로 중복 제거(첫 행 유지); 3시트 유지, Summary 카운트 재계산
  - 사람 455 → **316**(139행 제거); 쥐 878 → **717**(161행 제거)
  - InChIKey는 같지만 `Database ID`가 다른 입체이성질체(예: DL-Threonine/Threonine, Leucine/DL-Leucine)는 유지(제거 안 함)
  - 산출 `{species}_final_dedup.xlsx` (원본 파일은 그대로 둠)

### 기존 작업 (legacy)

legacy/는 COCONUT 기반 902 화합물 DB 구축 파이프라인(step1~29). 최종 분류: endogenous 143, exogenous 319, unverified 440. 상세는 legacy/README.md 참고.