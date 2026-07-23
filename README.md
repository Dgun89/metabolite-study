# metabolite-study

> InChIKey-normalized compound database and endogenous/exogenous classification for metabolite data (human, mouse serum, mouse feces).
> InChIKey 정규화 화합물 데이터베이스 및 내인성/외인성(endogenous/exogenous) 분류 프로젝트 (사람·쥐 혈청·쥐 분변).

**Language / 언어: [English](#english) · [한국어](#한국어)**

## Related repositories / 관련 저장소

- [DarkMet](https://github.com/dgun89/DarkMet) — classifies the *unverified* (dark metabolome) compounds this project surfaces, predicting origin from structure (SMILES) alone. / 이 프로젝트가 드러낸 미검증(dark metabolome) 화합물을 구조(SMILES)만으로 기원 예측·분류.
- [lipidomics-ai-agent](https://github.com/dgun89/lipidomics-ai-agent) — reuses the DB built here for RAG/GraphRAG experiments on grounding and identifier reliability. / 여기서 구축한 DB를 RAG/GraphRAG 실험에 재사용.

---

## English

### What this is

Three metabolite datasets — **human** serum, **mouse_serum**, and **mouse_feces** (the last is the dataset previously called *legacy*: rat/mouse feces, まうすのふん) — are collected from public databases and assembled into a single **InChIKey-normalized** relational schema. Every compound is keyed on its full 27-character **InChIKey** (structure identity), not on a COCONUT CNP id. Multi-valued facts (external DB ids, tissue origins, enzymes, per-source classification verdicts) are stored **long-format**, one row per fact, each carrying provenance (`source`, `source_version`, `retrieved_at`).

The whole pipeline is **rebuilt from the original source files** — no legacy data is reused — so an independent reproduction serves as a reliability audit of the earlier hand-curated DB.

### Normalized schema (6 tables, `data/normalized/*.parquet`)

Primary key throughout is `inchikey` (full 27-char); `inchikey14` (14-char skeleton) is a secondary join axis for stereoisomer-collapsed matching.

| Table | Rows | Grain | Key columns |
|---|---|---|---|
| `compounds` | 1,721 | one per unique InChIKey | inchikey, inchikey14, smiles, inchi, formula, compound_name, db_support_level, db_support_evidence, mmmdb_detected, mmmdb_n_tissues |
| `compound_external_ids` | 8,092 | one per (compound, DB, id) | inchikey, source, external_id, + provenance |
| `compound_origins` | 23,278 | one per (compound, origin fact) | inchikey, source, origin_label, + provenance |
| `compound_classification` | 1,721 | one verdict per compound | inchikey, classification, classification_basis, conflict_flag, conflicting_sources, source_verdicts, + ruleset provenance |
| `compound_enzymes` | 6,592 | one per (compound, EC) | inchikey, ec, source, + provenance |
| `compound_species` | 1,930 | one per (compound, dataset) | inchikey, species ∈ {human, mouse_serum, mouse_feces}, cnp_id |

Classification distribution: **endogenous 290 / exogenous 647 / unverified 784**; **169** compounds carry a source conflict, **58** are MMMDB-confirmed endogenous. DB-support level (structure-consensus proxy, not spectral MSI): **L2 667 / L3 1,054**.

External-id coverage by source: COCONUT 2,446 · PubChem 1,636 · EPA CompTox 681 · ChEBI 655 · ChEMBL 464 · HMDB 390 · KEGG 261 · FooDB 254 · RCSB PDB 242 · PDBe 240 · Wikipedia 213 · BindingDB 208 · DrugBank 193 · LIPID MAPS 87 · DrugCentral 72 · Guide to Pharmacology 44 · SwissLipids 6. (Most are UniChem cross-links already returned during identifier collection — stored, not re-fetched.)

### Pipeline (`pipeline/`, switch with `SPECIES=human|mouse_serum|mouse_feces`)

Code is species-agnostic; the dataset is selected by `config.get_paths(species)`. Paths are portable — `config.BASE` defaults to the repo root and is overridable via `METABO_BASE` / `METABO_WORK`.

0. **`00_make_seeds.py`** — extract CNP/PEP ids + compound name from each original xlsx → `{species}_seed.csv` (dup ids dropped).
0b. **`00b_resolve_pep.py`** — resolve peptide (`PEP…`) entries to structures: PubChem name search → RDKit `MolFromSequence` fallback. Recovery 100% (human 1/1, mouse_serum 10/10, mouse_feces 49/49).
1. **`01_coconut_join.py`** — join seed CNP ids against the local COCONUT CSV (738,827 rows, streamed): exact full-id match → base-id match with deterministic lowest-version selection (stereo ambiguity flagged) → PEP merge → PubChem name-search fallback for unmatched. **100% InChIKey coverage** on all three datasets. → `interim/{species}/{species}_step2_coconut.parquet`.
2. **`collect_identifiers.py`** — parallel identifier collection keyed on unique InChIKeys (1,721): UniChem `POST /unichem/api/v1/compounds` (all cross-links), ChEBI (roles), PubChem PUG REST (CID). Provenance-logged.
3. **`build_hmdb_index.py`** — stream the 6.1 GB HMDB XML with `iterparse`, extracting ontology source / protein / biospecimen for target InChIKeys.
4. **`04_classify_run.py`** + **`classify.py`** — rule-based endogenous/exogenous with per-source verdicts. `classify_row_v3()` adds an **E0** rule (MMMDB tissue detection → endogenous, highest priority) on top of v2's ChEBI/HMDB/COCONUT rules, and emits `conflict_flag` / `conflicting_sources` when sources disagree. Legacy `classify_row()` / `classify_row_v2()` retained for back-compat.
5. **`collect_enzymes.py`** — KEGG `link/enzyme` EC + Reactome catalyst mapping. **`collect_brenda.py`** — BRENDA SOAP (zeep), name → EC; auth `sha256(password)`, ≤ 1 req/sec.
6. **`normalize.py`** — assemble the 6 long-format normalized tables; recompute classification with `classify_row_v3`, assign the DB-support level (`db_support_level`/`db_support_evidence`; structure-consensus proxy, not spectral MSI), merge UniChem cross-links and MMMDB tissue origins. Explicit row sort: classification (endo→exo→unverified) → compound_name → inchikey.
7. **`export_view.py`** — build the wide human-readable view and write the 4-sheet xlsx (Data / Legend / Summary / Classification Rules) via `format_excel.py`, with color-grouped column headers and clickable DB-homepage links on the External DB ID headers (COCONUT…LIPID MAPS).
8. **`compare_legacy.py`** — reliability comparison against the original step29 DB on the common InChIKey intersection.

### Reproducing the deterministic stages (normalize → export)

The collection stages (COCONUT join, UniChem/HMDB/BRENDA) need large reference files and network access, so their outputs are cached under `.work/interim/` (gitignored). The **deterministic** downstream — `04_classify_run.py → normalize.py → export_view.py` — can be re-run from those caches alone, with no network:

```bash
export PYTHONPATH=.
python pipeline/04_classify_run.py   # optional: re-derive classification from step2 + caches
python pipeline/normalize.py         # rebuild data/normalized/*.parquet
python pipeline/export_view.py        # rebuild data/export/*.xlsx
python verify_reproduction.py         # compare against REPRODUCE_reference_fingerprints.json
```

`verify_reproduction.py` compares row counts and a sort-invariant SHA-256 of each normalized table against the committed baseline (`REPRODUCE_reference_fingerprints.json`), so a match confirms byte-identical **data** regardless of xlsx formatting/timestamps. The cache bundle needed to seed `.work/interim/` is distributed out-of-band (not in git).

### Exports (`data/export/*.xlsx`)

Per-dataset and combined workbooks, InChIKey-first column layout, headers color-grouped by category (Basic Identifiers / Dataset Membership / External DB IDs / Classification / Classification Sources / Classification Metadata / DB Support / Classification Conflicts / Enzyme Information). The External DB ID headers (COCONUT, PubChem, KEGG, HMDB, ChEBI, DrugBank, FooDB, LIPID MAPS) are clickable links to each database's homepage. A dedicated **Classification Rules** sheet documents the endogenous-dominant priority order (E0>E1>E2>E3>X1>X2>X3>U) and how `conflict_flag`/`conflicting_sources` are derived.

- `human_final.xlsx` — 316 rows
- `mouse_serum_final.xlsx` — 715 rows
- `mouse_feces_final.xlsx` — 899 rows
- `combined_final.xlsx` — 1,721 unique InChIKeys, with a `datasets` column recording which dataset(s) each compound comes from.

Combined dataset membership: mouse_feces only 795 · mouse_serum only 533 · human only 199 · human+mouse_serum 90 · mouse_feces+mouse_serum 77 · all three 15 · human+mouse_feces 12. (Per-dataset row counts are below the seed counts because same-structure entries merge on InChIKey — by design.)

### Legacy reliability comparison

Reproduced `mouse_feces` vs the original hand-curated step29 DB (`legacy/etc/metabolites_step29.xlsx`), on the common InChIKey intersection:

- **classification agreement**: full-IK **468/489 (95.7%)**, skeleton **787/861 (91.4%)**
- **PubChem CID agreement**: full-IK **441/479 (92.1%)**
- human full-IK 18/18 (100%), mouse_serum full-IK 48/54 (88.9%)

Key finding — the full-IK intersection (489) is much smaller than the skeleton intersection (861) not because of error but because of **improved stereochemistry**: for 373 compounds the baseline carried a flat (`…-UHFFFAOYSA-…`) InChIKey while the reproduction recovered the stereo-defined key from COCONUT's `standard_inchi_key`. The new pipeline restores stereochemistry the legacy DB had lost. See `data/export/comparison_report.md` and `legacy_comparison.png`.

### MMMDB bridge + DB-support level (all datasets)

MMMDB (Mouse Multiple Tissue Metabolome Database; Sugimoto et al., *NAR* 2012; CE-TOFMS, 11 tissues) is used as endogenous ground truth. A local reference (`data/mouse_serum/reference/mmmdb_reference.parquet`, 296 compounds) is matched by InChIKey / skeleton / KEGG; detection in real mouse tissue drives the E0 endogenous rule. Because tissue detection is structure-level evidence of mammalian endogeneity, it applies across all three datasets (58 compounds matched).

`db_support_level` (columns `db_support_level` / `db_support_evidence`) is a **structure-consensus proxy, not a spectral MSI grade** — it counts how many independent databases support each structure: L2 = InChIKey with ≥2 independent DB IDs, L3 = InChIKey with ≤1, L4 = formula-only (no InChIKey), L5 = unknown. It deliberately does **not** claim a true MSI Level 1 (authentic-standard confirmation), which non-target data cannot support. (Earlier drafts named these columns `msi_level`/`msi_evidence`; renamed to avoid overstating a spectral standard.)

### Notes on the answered questions (2026-07-22)

- **Primary key is InChIKey.** The `COCONUT` column (formerly "Database ID" / `coconut_ids`) is a display/reference column only, placed in the External DB IDs block alongside PubChem/KEGG/ChEBI; all joins, merges, and sorting use InChIKey.
- **The `COCONUT` column may list two CNP ids** (`CNP…; CNP…`) when two COCONUT versions collapse to one InChIKey — 11 such rows in combined. This is not a duplicate column.
- **Row order** is explicit: classification → compound_name → InChIKey.
- **"N"** is not a column — earlier report notation `n=489` meant *number of common compounds*, not a spreadsheet column.
- **Dataset renaming**: `mouse` → `mouse_serum`, `legacy` → `mouse_feces` (the feces sample).

### Data handling principles

- `raw/` is preserved as-is, never modified.
- `interim/` (under `.work/`) holds regenerable intermediate parquet checkpoints.
- `data/normalized/` (6 parquet) and `data/export/` (xlsx) are the analysis/sharing outputs.
- Code is dataset-agnostic; switch via `SPECIES`.

### Project structure

```
metabolite-study/
├─ data/
│  ├─ reference/            reference downloads (COCONUT CSV, HMDB XML)
│  ├─ human/                human serum (raw → interim)
│  ├─ mouse_serum/          mouse serum (raw → interim; + reference/mmmdb_reference.parquet)
│  ├─ mouse_feces/          mouse feces, formerly "legacy" (raw)
│  ├─ normalized/           6 long-format normalized tables (parquet)
│  └─ export/               final xlsx + reliability report/figure
├─ pipeline/                InChIKey-normalized pipeline (shared code, switch by SPECIES)
│  ├─ config.py             portable paths & constants (METABO_BASE/METABO_WORK)
│  ├─ 00_make_seeds.py      seed extraction from original xlsx
│  ├─ 00b_resolve_pep.py    peptide → structure resolution
│  ├─ 01_coconut_join.py    COCONUT local join → InChIKey (100% coverage)
│  ├─ collect_identifiers.py  UniChem/ChEBI/PubChem cross-collection
│  ├─ build_hmdb_index.py   HMDB XML streaming index
│  ├─ classify.py           rule-based classification (v1/v2/v3) + DB-support level
│  ├─ 04_classify_run.py    classification runner
│  ├─ collect_enzymes.py    KEGG EC + Reactome catalyst
│  ├─ collect_brenda.py     BRENDA SOAP enzyme (EC)
│  ├─ normalize.py          assemble 6 normalized tables
│  ├─ export_view.py        normalized → 4-sheet xlsx
│  ├─ compare_legacy.py     reliability comparison vs legacy step29
│  └─ mmmdb/                MMMDB reference build + curation
├─ scripts/                 preprocessing (HTML extraction, overlap, dedup)
├─ legacy/                  original pipeline (step1–29) + step29 baseline
├─ format_excel.py          Excel 4-sheet color-grouped formatting + header links
└─ validate.py              data validation
```

### Progress log

- **2026-07-22** — InChIKey normalization refactor:
  - primary key COCONUT CNP id → **InChIKey**; 6 long-format normalized tables with per-row provenance
  - COCONUT join 100% InChIKey coverage (human 316 / mouse_serum 717 / mouse_feces 902 seeds)
  - identifier collection over 1,721 unique InChIKeys (0 errors); UniChem cross-links stored (external_ids 8,092)
  - classification with per-source conflict flags: endo 290 / exo 647 / unverified 784, 169 conflicts, 58 MMMDB-endogenous
  - DB-support level L2 667 / L3 1,054 (renamed from msi_level); MMMDB applied across all datasets
  - datasets renamed mouse→mouse_serum, legacy→mouse_feces
  - legacy reliability (reproduced mouse_feces vs step29): classification 95.7% full-IK, PubChem CID 92.1%; stereochemistry recovered for 373 compounds
  - exports: human 316 / mouse_serum 715 / mouse_feces 899 / combined 1,721, color-grouped headers, dataset-membership column
  - fixed a build_wide index-alignment bug (exposed by the new explicit sort) that had corrupted aggregated columns
  - post-review cleanup: dropped the dead `coconut_match_key` column (constant `"InChIKey"`); renamed `msi_level`/`msi_evidence` → `db_support_level`/`db_support_evidence` (structure-consensus proxy, not spectral MSI); renamed `coconut_ids` → `COCONUT` and moved it into the External DB IDs block; added clickable DB-homepage links on the External DB ID headers; added a **Classification Rules** sheet; fixed a `(inchikey, species)` duplication in compound_species (CNP-version rows collapsed → 1,935→1,930)

### Legacy

`legacy/` is the original COCONUT-based step1–29 pipeline and the `metabolites_step29.xlsx` baseline used for the reliability check. See `legacy/README.md`.

---

## 한국어

### 개요

세 대사체 데이터셋 — **human**(사람 혈청), **mouse_serum**(쥐 혈청), **mouse_feces**(쥐 분변, まうすのふん — 이전에 *legacy*로 부르던 데이터셋) — 을 공개 DB에서 수집해 하나의 **InChIKey 정규화** 관계형 스키마로 조립한다. 모든 화합물은 COCONUT CNP id가 아니라 27자 **InChIKey**(구조 동일성)를 기본키로 한다. 다중값 정보(외부 DB id, 조직 기원, 효소, 소스별 분류 판정)는 **long-format**으로 사실 하나당 한 행씩 저장하며 각 행에 provenance(`source`, `source_version`, `retrieved_at`)를 붙인다.

전체 파이프라인은 **원본 파일에서 처음부터 재구축**한다 — legacy 데이터를 재사용하지 않으므로, 독립적 재현이 기존 수기 큐레이션 DB에 대한 신뢰성 감사가 된다.

### 정규화 스키마 (6개 테이블, `data/normalized/*.parquet`)

기본키는 전부 `inchikey`(27자); `inchikey14`(14자 골격)는 입체이성질체 병합 매칭용 보조 축.

| 테이블 | 행수 | 단위 | 주요 컬럼 |
|---|---|---|---|
| `compounds` | 1,721 | 고유 InChIKey 1개 | inchikey, inchikey14, smiles, inchi, formula, compound_name, db_support_level, db_support_evidence, mmmdb_detected, mmmdb_n_tissues |
| `compound_external_ids` | 8,092 | (화합물, DB, id) 1개 | inchikey, source, external_id, + provenance |
| `compound_origins` | 23,278 | (화합물, 기원 사실) 1개 | inchikey, source, origin_label, + provenance |
| `compound_classification` | 1,721 | 화합물당 판정 1개 | inchikey, classification, classification_basis, conflict_flag, conflicting_sources, source_verdicts, + ruleset provenance |
| `compound_enzymes` | 6,592 | (화합물, EC) 1개 | inchikey, ec, source, + provenance |
| `compound_species` | 1,930 | (화합물, 데이터셋) 1개 | inchikey, species ∈ {human, mouse_serum, mouse_feces}, cnp_id |

분류 분포: **endogenous 290 / exogenous 647 / unverified 784**; **169**개 화합물에 소스 충돌, **58**개 MMMDB 확인 내인성. DB 지지 등급(구조 합의 프록시, 분광 MSI 아님): **L2 667 / L3 1,054**.

소스별 외부 id 커버리지: COCONUT 2,446 · PubChem 1,636 · EPA CompTox 681 · ChEBI 655 · ChEMBL 464 · HMDB 390 · KEGG 261 · FooDB 254 · RCSB PDB 242 · PDBe 240 · Wikipedia 213 · BindingDB 208 · DrugBank 193 · LIPID MAPS 87 · DrugCentral 72 · Guide to Pharmacology 44 · SwissLipids 6. (대부분 identifier 수집 시 UniChem이 이미 반환한 교차링크 — 재수집 없이 저장.)

### 파이프라인 (`pipeline/`, `SPECIES=human|mouse_serum|mouse_feces` 전환)

코드는 데이터셋 무관, `config.get_paths(species)`로 선택. 경로는 이식 가능 — `config.BASE`는 레포 루트가 기본이고 `METABO_BASE` / `METABO_WORK`로 오버라이드.

0. **`00_make_seeds.py`** — 원본 xlsx에서 CNP/PEP id + 화합물명 추출 → `{species}_seed.csv`(중복 id 제거).
0b. **`00b_resolve_pep.py`** — 펩타이드(`PEP…`) 항목 구조 복원: PubChem 이름검색 → RDKit `MolFromSequence` fallback. 복원율 100%(human 1/1, mouse_serum 10/10, mouse_feces 49/49).
1. **`01_coconut_join.py`** — seed CNP id를 로컬 COCONUT CSV(738,827행, 스트리밍)와 조인: full-id 정확매칭 → base-id 매칭+최저버전 결정론적 선택(입체 애매 시 플래그) → PEP 병합 → 미매칭은 PubChem 이름검색 fallback. **3종 모두 100% InChIKey 커버리지.** → `interim/{species}/{species}_step2_coconut.parquet`.
2. **`collect_identifiers.py`** — 고유 InChIKey(1,721) 기준 병렬 수집: UniChem `POST /unichem/api/v1/compounds`(전체 교차링크), ChEBI(roles), PubChem PUG REST(CID). Provenance 기록.
3. **`build_hmdb_index.py`** — 6.1GB HMDB XML을 `iterparse` 스트리밍, 대상 InChIKey의 ontology source/protein/biospecimen 추출.
4. **`04_classify_run.py`** + **`classify.py`** — 소스별 판정 규칙 기반 내인성/외인성. `classify_row_v3()`는 v2의 ChEBI/HMDB/COCONUT 규칙 위에 **E0**(MMMDB 조직 검출→내인성, 최우선)를 추가하고, 소스 불일치 시 `conflict_flag` / `conflicting_sources`를 기록. 기존 `classify_row()` / `classify_row_v2()`는 하위호환 유지.
5. **`collect_enzymes.py`** — KEGG `link/enzyme` EC + Reactome catalyst. **`collect_brenda.py`** — BRENDA SOAP(zeep), 이름 → EC; 인증 `sha256(password)`, ≤ 1 req/sec.
6. **`normalize.py`** — 6개 long-format 정규화 테이블 조립; `classify_row_v3`로 분류 재계산, DB 지지 등급 부여(`db_support_level`/`db_support_evidence`; 구조 합의 프록시, 분광 MSI 아님), UniChem 교차링크·MMMDB 조직 기원 병합. 명시적 행정렬: 분류(endo→exo→unverified) → compound_name → inchikey.
7. **`export_view.py`** — 넓은 형태 뷰 생성, `format_excel.py`로 4시트 xlsx(Data / Legend / Summary / Classification Rules) 작성, 컬럼 헤더 색상 그룹화 + External DB ID 헤더(COCONUT…LIPID MAPS)에 DB 홈페이지 클릭 링크.
8. **`compare_legacy.py`** — 기존 step29 DB와 공통 InChIKey 교집합에서 신뢰성 대조.

### 결정론적 단계 재현 (normalize → export)

수집 단계(COCONUT 조인, UniChem/HMDB/BRENDA)는 대용량 참조 파일과 네트워크가 필요해 그 산출물을 `.work/interim/`에 캐시로 둔다(gitignore). **결정론적** 하위 단계 — `04_classify_run.py → normalize.py → export_view.py` — 는 그 캐시만으로 네트워크 없이 재실행할 수 있다:

```bash
export PYTHONPATH=.
python pipeline/04_classify_run.py   # (선택) step2 + 캐시로 분류 재산출
python pipeline/normalize.py         # data/normalized/*.parquet 재생성
python pipeline/export_view.py        # data/export/*.xlsx 재생성
python verify_reproduction.py         # REPRODUCE_reference_fingerprints.json 과 대조
```

`verify_reproduction.py`는 각 정규화 테이블의 행수와 정렬 불변 SHA-256을 커밋된 기준선(`REPRODUCE_reference_fingerprints.json`)과 비교하므로, 일치하면 xlsx 서식·타임스탬프와 무관하게 **데이터**가 바이트 단위로 동일함을 확인한다. `.work/interim/`을 채울 캐시 번들은 git이 아닌 별도 경로로 배포한다.

### Export (`data/export/*.xlsx`)

데이터셋별·통합 워크북, InChIKey 맨앞 컬럼 배치, 카테고리별 헤더 색상 그룹(Basic Identifiers / Dataset Membership / External DB IDs / Classification / Classification Sources / Classification Metadata / DB Support / Classification Conflicts / Enzyme Information). External DB ID 헤더(COCONUT, PubChem, KEGG, HMDB, ChEBI, DrugBank, FooDB, LIPID MAPS)는 각 DB 홈페이지로 가는 클릭 링크다. 별도의 **Classification Rules** 시트가 내인성 우세 우선순위(E0>E1>E2>E3>X1>X2>X3>U)와 `conflict_flag`/`conflicting_sources` 산출 방식을 명시한다.

- `human_final.xlsx` — 316행
- `mouse_serum_final.xlsx` — 715행
- `mouse_feces_final.xlsx` — 899행
- `combined_final.xlsx` — 고유 InChIKey 1,721개, 각 화합물의 출처 데이터셋을 `datasets` 컬럼에 기록.

통합본 데이터셋 소속: mouse_feces 단독 795 · mouse_serum 단독 533 · human 단독 199 · human+mouse_serum 90 · mouse_feces+mouse_serum 77 · 3종 전부 15 · human+mouse_feces 12. (데이터셋별 행수가 seed보다 적은 건 동일 구조가 InChIKey로 병합되기 때문 — 설계대로.)

### legacy 신뢰성 대조

재현 `mouse_feces` vs 기존 수기 큐레이션 step29 DB(`legacy/etc/metabolites_step29.xlsx`), 공통 InChIKey 교집합:

- **분류 일치**: full-IK **468/489 (95.7%)**, skeleton **787/861 (91.4%)**
- **PubChem CID 일치**: full-IK **441/479 (92.1%)**
- human full-IK 18/18(100%), mouse_serum full-IK 48/54(88.9%)

핵심 발견 — full-IK 교집합(489)이 skeleton 교집합(861)보다 훨씬 작은 것은 오류가 아니라 **입체화학 개선** 때문이다: 373개 화합물에서 baseline은 평면(`…-UHFFFAOYSA-…`) InChIKey를 가졌던 반면 재현은 COCONUT `standard_inchi_key`로 입체 정의된 키를 복원했다. 새 파이프라인이 legacy DB에서 소실된 입체화학을 복원한 것이다. `data/export/comparison_report.md`와 `legacy_comparison.png` 참고.

### MMMDB 브릿지 + DB 지지 등급 (전 데이터셋)

MMMDB(Mouse Multiple Tissue Metabolome Database; Sugimoto et al., *NAR* 2012; CE-TOFMS, 11조직)를 내인성 ground truth로 사용. 로컬 참조(`data/mouse_serum/reference/mmmdb_reference.parquet`, 296 화합물)를 InChIKey/골격/KEGG로 매칭; 실제 쥐 조직 검출이 E0 내인성 규칙을 구동한다. 조직 검출은 포유류 내인성의 구조 수준 증거이므로 3종 데이터셋 전부에 적용(58개 매칭).

`db_support_level`(컬럼 `db_support_level` / `db_support_evidence`)은 **분광 MSI 등급이 아니라 구조 합의 프록시**다 — 독립 DB가 각 구조를 몇 개나 지지하는지를 센다: L2 = InChIKey 있고 독립 DB ID ≥2, L3 = InChIKey 있고 ≤1, L4 = 이름/질량만(InChIKey 없음), L5 = 미지. 논타겟 데이터가 뒷받침할 수 없는 진정한 MSI Level 1(정제 표준물질 확증)은 **의도적으로 부여하지 않는다**. (초기 버전은 이 컬럼을 `msi_level`/`msi_evidence`로 불렀으나, 분광 표준을 참칭하지 않도록 개명했다.)

### 답변한 질문 메모 (2026-07-22)

- **기본키는 InChIKey.** `COCONUT` 컬럼(이전 "Database ID" / `coconut_ids`)은 표시·참조용일 뿐이며, PubChem/KEGG/ChEBI와 같은 External DB IDs 블록에 배치한다. 모든 조인·병합·정렬은 InChIKey로 한다.
- **`COCONUT` 컬럼에 CNP 2개**(`CNP…; CNP…`)가 들어갈 수 있음 — COCONUT 두 버전이 한 InChIKey로 병합될 때(통합본 11행). 컬럼 중복이 아님.
- **행 순서**는 명시적: 분류 → compound_name → InChIKey.
- **"N"**은 컬럼이 아님 — 이전 리포트의 `n=489` 표기는 *공통 화합물 개수*를 뜻함.
- **데이터셋 개명**: `mouse` → `mouse_serum`, `legacy` → `mouse_feces`(분변 시료).

### 데이터 처리 원칙

- `raw/`는 원본 보존, 수정하지 않음.
- `interim/`(`.work/` 하위)은 재생성 가능한 중간 parquet 체크포인트.
- `data/normalized/`(6 parquet)와 `data/export/`(xlsx)가 분석·공유용 산출물.
- 코드는 데이터셋 무관, `SPECIES`로 전환.

### 프로젝트 구조

```
metabolite-study/
├─ data/
│  ├─ reference/            참조 다운로드 (COCONUT CSV, HMDB XML)
│  ├─ human/                사람 혈청 (raw → interim)
│  ├─ mouse_serum/          쥐 혈청 (raw → interim; + reference/mmmdb_reference.parquet)
│  ├─ mouse_feces/          쥐 분변, 이전 "legacy" (raw)
│  ├─ normalized/           6개 long-format 정규화 테이블 (parquet)
│  └─ export/               최종 xlsx + 신뢰성 리포트/그림
├─ pipeline/                InChIKey 정규화 파이프라인 (공통 코드, SPECIES 전환)
│  ├─ config.py             이식 가능 경로·상수 (METABO_BASE/METABO_WORK)
│  ├─ 00_make_seeds.py      원본 xlsx에서 seed 추출
│  ├─ 00b_resolve_pep.py    펩타이드 → 구조 복원
│  ├─ 01_coconut_join.py    COCONUT 로컬 조인 → InChIKey (100% 커버리지)
│  ├─ collect_identifiers.py  UniChem/ChEBI/PubChem 교차수집
│  ├─ build_hmdb_index.py   HMDB XML 스트리밍 인덱스
│  ├─ classify.py           규칙 기반 분류 (v1/v2/v3) + DB 지지 등급
│  ├─ 04_classify_run.py    분류 실행기
│  ├─ collect_enzymes.py    KEGG EC + Reactome catalyst
│  ├─ collect_brenda.py     BRENDA SOAP 효소(EC)
│  ├─ normalize.py          6개 정규화 테이블 조립
│  ├─ export_view.py        정규화 → 4시트 xlsx
│  ├─ compare_legacy.py     legacy step29 신뢰성 대조
│  └─ mmmdb/                MMMDB 참조 구축 + 큐레이션
├─ scripts/                 전처리 (HTML 추출, 겹침, 중복제거)
├─ legacy/                  기존 파이프라인 (step1~29) + step29 baseline
├─ format_excel.py          엑셀 4시트 색상 그룹 서식 + 헤더 링크
└─ validate.py              데이터 검증
```

### 진행 로그

- **2026-07-22** — InChIKey 정규화 리팩터링:
  - 기본키 COCONUT CNP id → **InChIKey**; 행 단위 provenance 포함 6개 long-format 정규화 테이블
  - COCONUT 조인 100% InChIKey 커버리지 (seed human 316 / mouse_serum 717 / mouse_feces 902)
  - 고유 InChIKey 1,721개 identifier 수집(오류 0); UniChem 교차링크 저장(external_ids 8,092)
  - 소스별 충돌 플래그 포함 분류: endo 290 / exo 647 / unverified 784, 충돌 169, MMMDB 내인성 58
  - DB 지지 등급 L2 667 / L3 1,054 (msi_level에서 개명); MMMDB 전 데이터셋 적용
  - 데이터셋 개명 mouse→mouse_serum, legacy→mouse_feces
  - legacy 신뢰성(재현 mouse_feces vs step29): 분류 full-IK 95.7%, PubChem CID 92.1%; 373개 화합물 입체화학 복원
  - export: human 316 / mouse_serum 715 / mouse_feces 899 / 통합 1,721, 헤더 색상 그룹, 데이터셋 소속 컬럼
  - 명시적 정렬 도입으로 드러난 build_wide 인덱스 정렬 버그(aggregated 컬럼 손상) 수정
  - 리뷰 후 정리: 죽은 `coconut_match_key` 컬럼(상수 `"InChIKey"`) 삭제; `msi_level`/`msi_evidence` → `db_support_level`/`db_support_evidence` 개명(분광 MSI 아닌 구조 합의 프록시); `coconut_ids` → `COCONUT` 개명 후 External DB IDs 블록으로 이동; External DB ID 헤더에 DB 홈페이지 클릭 링크 추가; **Classification Rules** 시트 추가; compound_species의 `(inchikey, species)` 중복 수정(CNP 버전 행 병합 → 1,935→1,930)

### 기존 작업 (legacy)

`legacy/`는 원래 COCONUT 기반 step1~29 파이프라인과 신뢰성 검증용 `metabolites_step29.xlsx` baseline. 상세는 `legacy/README.md`.
