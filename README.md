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
| `compound_origins` | 23,278 | one per (compound, origin fact) | inchikey, source, origin_label, origin_category, origin_level, + provenance |
| `compound_classification` | 1,721 | one row per compound | inchikey, drug_food, classification, classification_basis, conflict_flag, conflicting_sources, source_verdicts, + ruleset provenance |
| `compound_enzymes` | 6,592 | one per (compound, EC) | inchikey, ec, source, + provenance |
| `compound_species` | 1,930 | one per (compound, dataset) | inchikey, species ∈ {human_serum, mouse_serum, mouse_feces}, cnp_id |

**Classification is v4 (2026-07-27 advisor meeting): priority rules dropped — the column now lists each DB's verdict in parallel** (e.g. `ChEBI:exogenous; HMDB:endogenous; COCONUT:endogenous`) instead of forcing one label, because each DB measures a different axis (ChEBI=produced / HMDB=detected / COCONUT=isolated-from). Evidence counts are therefore non-exclusive: **has-endogenous-evidence 290 / has-exogenous-evidence 816 / unverified 784**; **169** compounds carry an endo↔exo conflict, **58** are MMMDB-confirmed endogenous. A **`drug_food`** flag (drug = DrugBank/DrugCentral present, food = FooDB present) sits before `classification` as a display-only 1st-pass filter — rows are never dropped (FooDB presence is a *detection* axis and includes many endogenous compounds). DB-support level (structure-consensus proxy, not spectral MSI): **L2 667 / L3 1,054**.

External-id coverage by source: COCONUT 2,446 · PubChem 1,636 · EPA CompTox 681 · ChEBI 655 · ChEMBL 464 · HMDB 390 · KEGG 261 · FooDB 254 · RCSB PDB 242 · PDBe 240 · Wikipedia 213 · BindingDB 208 · DrugBank 193 · LIPID MAPS 87 · DrugCentral 72 · Guide to Pharmacology 44 · SwissLipids 6. (Most are UniChem cross-links already returned during identifier collection — stored, not re-fetched.)

### Pipeline (`pipeline/`, switch with `SPECIES=human|mouse_serum|mouse_feces`)

Code is species-agnostic; the dataset is selected by `config.get_paths(species)`. Paths are portable — `config.BASE` defaults to the repo root and is overridable via `METABO_BASE` / `METABO_WORK`.

0. **`00_make_seeds.py`** — extract CNP/PEP ids + compound name from each original xlsx → `{species}_seed.csv` (dup ids dropped).
0b. **`00b_resolve_pep.py`** — resolve peptide (`PEP…`) entries to structures: PubChem name search → RDKit `MolFromSequence` fallback. Recovery 100% (human 1/1, mouse_serum 10/10, mouse_feces 49/49).
1. **`01_coconut_join.py`** — join seed CNP ids against the local COCONUT CSV (738,827 rows, streamed): exact full-id match → base-id match with deterministic lowest-version selection (stereo ambiguity flagged) → PEP merge → PubChem name-search fallback for unmatched. **100% InChIKey coverage** on all three datasets. → `interim/{species}/{species}_step2_coconut.parquet`.
2. **`collect_identifiers.py`** — parallel identifier collection keyed on unique InChIKeys (1,721): UniChem `POST /unichem/api/v1/compounds` (all cross-links), ChEBI (roles), PubChem PUG REST (CID). Provenance-logged.
3. **`build_hmdb_index.py`** — stream the 6.1 GB HMDB XML with `iterparse`, extracting ontology source / protein / biospecimen for target InChIKeys.
4. **`04_classify_run.py`** + **`classify.py`** — endogenous/exogenous with per-source verdicts. **`classify_row_v4()`** (current) drops the priority rules entirely: it reuses each DB's independent verdict but **lists them in parallel** (`ChEBI:…; HMDB:…; COCONUT:…; MMMDB:…`) rather than forcing one label — different DBs measure different axes, so collapsing them mangles the axis. `conflict_flag` / `conflicting_sources` still flag endo↔exo disagreement. Earlier `classify_row()` / `_v2()` / `_v3()` are **kept frozen** for back-compat and before/after audit (we stack rule versions, never overwrite them).
5. **`collect_enzymes.py`** — KEGG `link/enzyme` EC + Reactome catalyst mapping. **`collect_brenda.py`** — BRENDA SOAP (zeep), name → EC; auth `sha256(password)`, ≤ 1 req/sec.
6. **`normalize.py`** — assemble the 6 long-format normalized tables; recompute classification with `classify_row_v4` (parallel per-DB verdicts) + the `drug_food` display flag, assign the DB-support level (`db_support_level`/`db_support_evidence`; structure-consensus proxy, not spectral MSI), merge UniChem cross-links and MMMDB tissue origins. Explicit row sort: endogenous-evidence-first → compound_name → inchikey.
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

Per-dataset and combined workbooks, InChIKey-first column layout, headers color-grouped by category (Basic Identifiers / Dataset Membership / External DB IDs / **Drug / Food** / Classification / Classification Sources / Classification Metadata / DB Support / Classification Conflicts / Enzyme Information). The External DB ID headers (COCONUT, PubChem, KEGG, HMDB, ChEBI, DrugBank, FooDB, LIPID MAPS) are clickable links to each database's homepage. A dedicated **Classification Rules** sheet documents the **v4 method** — each DB's verdict is listed in parallel (no priority ordering), what axis each DB reads (ChEBI=produced / HMDB=detected / COCONUT=isolated-from / MMMDB=tissue-measured), and how `conflict_flag`/`conflicting_sources` are derived.

Export filenames carry a `yymmdd` creation-date stamp (no `-`), e.g. `combined_260728.xlsx`, because the export is a view that is regenerated on every run — it is **not** a frozen "final". Row counts below are for the 2026-07-28 snapshot.

- `human_serum_yymmdd.xlsx` — 316 rows
- `mouse_serum_yymmdd.xlsx` — 715 rows
- `mouse_feces_yymmdd.xlsx` — 899 rows
- `combined_yymmdd.xlsx` — 1,721 unique InChIKeys, with a `datasets` column recording which dataset(s) each compound comes from.

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

- **2026-07-28** — portability + drug/food column cleanup:
  - **UTF-8 pinned** on all `read_text`/`write_text` calls across the pipeline — `Path.read_text()` defaults to the OS locale (cp1252 on Windows) and raised `UnicodeDecodeError` on UTF-8 JSON caches. Now runs on Windows.
  - **export filenames** changed from `{name}_final.xlsx` to a `yymmdd` creation stamp (`combined_260728.xlsx`) — the export is regenerated every run, not a frozen "final". `compare_legacy.py` now globs the latest date-stamped snapshot.
  - pipeline input caches (`.work/interim/*.json`, `*_step4_classified.parquet`) **force-tracked in git** as pinned reproduction inputs, so a clone can run `normalize.py` + `export_view.py` without re-running collection.
  - **`DrugCentral` column added** to the export — it was cited as drug/food evidence but had no column, so the cited source could not be audited (72 compounds carry a DrugCentral ID).
  - **`drug_food_basis` removed** — the `DrugBank`/`DrugCentral`/`FooDB` ID columns now show the evidence directly, making the packed `drug:DB1,DB2; food:DB3` string redundant. `drug_food` (the verdict) is kept.

- **2026-07-27** — advisor-meeting schema changes (human/mouse scope):
  - renamed dataset key `human` → `human_serum` (`config.SPECIES`, seed/source maps, comparison target). `data/human/` raw folder name kept per the raw-preservation rule; only the label changed.
  - added a **`drug_food`** display flag (+ `drug_food_basis`) before `classification`: drug = DrugBank/DrugCentral present, food = FooDB present. 1st-pass filter marker only — no rows dropped (363 flagged: food 164 / drug 109 / drug+food 90).
  - **classification v4** — dropped the priority rules. The column now lists each DB's verdict in parallel (`ChEBI:…; HMDB:…; COCONUT:…; MMMDB:…`) instead of forcing one label. `classify_row_v1..v3` kept frozen in `classify.py`; v3 outputs archived at `data/normalized/_v3_frozen_20260727/` for before/after audit. Summary counts became non-exclusive evidence tallies + a conflict row. Classification Rules sheet rewritten to describe the v4 method.

- **2026-07-23** — HMDB Source subtree + origin categorization:
  - profiled the full 6.1 GB `hmdb_metabolites.xml` (217,920 records) by streaming parse — see `docs/HMDB_structure_guide.md`
  - established that HMDB `Disposition > Source` is **not** an endo/exo dichotomy: 6 sibling labels (Food 146,742 / Endogenous 145,377 / Biological 144,377 / Synthetic 193 / Environmental 162 / **Exogenous 6**); 93% of source-tagged compounds carry 3 labels at once (Biological & Endogenous & Food, 139,977)
  - new `pipeline/build_source_hierarchy.py` → `data/reference/hmdb_source_hierarchy.json` (457-term roll-up map, term → one of 6 top buckets + tree level)
  - `normalize.py` now annotates each `compound_origins` row with `origin_category` (6-bucket roll-up) and `origin_level` (tree depth); backward-compatible (added columns only)
  - `export_view.py` adds a `hmdb_origin_category` summary column (buckets only, distinct from the species-level `hmdb_origin`)
  - reproduction baseline: `compound_origins` fingerprint updated for the new columns (other tables untouched)
  - **known issue**: `compounds` fingerprint DIFFERs against the committed baseline even on a clean checkout (predates this change; `.work/interim/` cache drifted from the fingerprint-generation state) — to be investigated separately, not masked by regenerating the baseline

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
| `compound_origins` | 23,278 | (화합물, 기원 사실) 1개 | inchikey, source, origin_label, origin_category, origin_level, + provenance |
| `compound_classification` | 1,721 | 화합물당 1행 | inchikey, drug_food, classification, classification_basis, conflict_flag, conflicting_sources, source_verdicts, + ruleset provenance |
| `compound_enzymes` | 6,592 | (화합물, EC) 1개 | inchikey, ec, source, + provenance |
| `compound_species` | 1,930 | (화합물, 데이터셋) 1개 | inchikey, species ∈ {human_serum, mouse_serum, mouse_feces}, cnp_id |

**분류는 v4(2026-07-27 교수님 회의): 우선순위 규칙 폐기 — 컬럼이 이제 각 DB의 판정을 병렬로 나열**한다(예: `ChEBI:exogenous; HMDB:endogenous; COCONUT:endogenous`). 각 DB가 서로 다른 축(ChEBI=만들었나 / HMDB=검출됐나 / COCONUT=분리됐나)을 재므로 하나로 합치지 않는다. 따라서 근거 카운트는 배타적이지 않다: **내인성 근거 포함 290 / 외인성 근거 포함 816 / unverified 784**; **169**개 화합물에 endo↔exo 충돌, **58**개 MMMDB 확인 내인성. classification **앞**에 **`drug_food`** 플래그(drug = DrugBank/DrugCentral 존재, food = FooDB 존재)가 1차 필터 표시로 놓이지만 **행은 지우지 않는다**(FooDB 존재는 *검출* 축이라 내인성 화합물도 다수 포함). DB 지지 등급(구조 합의 프록시, 분광 MSI 아님): **L2 667 / L3 1,054**.

소스별 외부 id 커버리지: COCONUT 2,446 · PubChem 1,636 · EPA CompTox 681 · ChEBI 655 · ChEMBL 464 · HMDB 390 · KEGG 261 · FooDB 254 · RCSB PDB 242 · PDBe 240 · Wikipedia 213 · BindingDB 208 · DrugBank 193 · LIPID MAPS 87 · DrugCentral 72 · Guide to Pharmacology 44 · SwissLipids 6. (대부분 identifier 수집 시 UniChem이 이미 반환한 교차링크 — 재수집 없이 저장.)

### 파이프라인 (`pipeline/`, `SPECIES=human|mouse_serum|mouse_feces` 전환)

코드는 데이터셋 무관, `config.get_paths(species)`로 선택. 경로는 이식 가능 — `config.BASE`는 레포 루트가 기본이고 `METABO_BASE` / `METABO_WORK`로 오버라이드.

0. **`00_make_seeds.py`** — 원본 xlsx에서 CNP/PEP id + 화합물명 추출 → `{species}_seed.csv`(중복 id 제거).
0b. **`00b_resolve_pep.py`** — 펩타이드(`PEP…`) 항목 구조 복원: PubChem 이름검색 → RDKit `MolFromSequence` fallback. 복원율 100%(human 1/1, mouse_serum 10/10, mouse_feces 49/49).
1. **`01_coconut_join.py`** — seed CNP id를 로컬 COCONUT CSV(738,827행, 스트리밍)와 조인: full-id 정확매칭 → base-id 매칭+최저버전 결정론적 선택(입체 애매 시 플래그) → PEP 병합 → 미매칭은 PubChem 이름검색 fallback. **3종 모두 100% InChIKey 커버리지.** → `interim/{species}/{species}_step2_coconut.parquet`.
2. **`collect_identifiers.py`** — 고유 InChIKey(1,721) 기준 병렬 수집: UniChem `POST /unichem/api/v1/compounds`(전체 교차링크), ChEBI(roles), PubChem PUG REST(CID). Provenance 기록.
3. **`build_hmdb_index.py`** — 6.1GB HMDB XML을 `iterparse` 스트리밍, 대상 InChIKey의 ontology source/protein/biospecimen 추출.
4. **`04_classify_run.py`** + **`classify.py`** — 소스별 판정 기반 내인성/외인성. **`classify_row_v4()`**(현재)는 우선순위 규칙을 완전히 폐기하고 각 DB의 독립 판정을 **병렬로 나열**한다(`ChEBI:…; HMDB:…; COCONUT:…; MMMDB:…`) — DB마다 축이 달라 하나로 합치면 축을 뭉갠다. `conflict_flag` / `conflicting_sources`는 여전히 endo↔exo 불일치를 표시한다. 이전 `classify_row()` / `_v2()` / `_v3()`는 하위호환·전후 비교를 위해 **박제로 보존**(규칙 버전을 덮어쓰지 않고 쌓는다).
5. **`collect_enzymes.py`** — KEGG `link/enzyme` EC + Reactome catalyst. **`collect_brenda.py`** — BRENDA SOAP(zeep), 이름 → EC; 인증 `sha256(password)`, ≤ 1 req/sec.
6. **`normalize.py`** — 6개 long-format 정규화 테이블 조립; `classify_row_v4`(DB별 병렬 판정) + `drug_food` 표시 플래그로 분류 재계산, DB 지지 등급 부여(`db_support_level`/`db_support_evidence`; 구조 합의 프록시, 분광 MSI 아님), UniChem 교차링크·MMMDB 조직 기원 병합. 명시적 행정렬: 내인성 근거 우선 → compound_name → inchikey.
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

데이터셋별·통합 워크북, InChIKey 맨앞 컬럼 배치, 카테고리별 헤더 색상 그룹(Basic Identifiers / Dataset Membership / External DB IDs / **Drug / Food** / Classification / Classification Sources / Classification Metadata / DB Support / Classification Conflicts / Enzyme Information). External DB ID 헤더(COCONUT, PubChem, KEGG, HMDB, ChEBI, DrugBank, FooDB, LIPID MAPS)는 각 DB 홈페이지로 가는 클릭 링크다. 별도의 **Classification Rules** 시트가 **v4 방식**을 명시한다 — 각 DB 판정을 병렬로 나열(우선순위 없음), 각 DB가 읽는 축(ChEBI=만들었나 / HMDB=검출됐나 / COCONUT=분리됐나 / MMMDB=조직실측), `conflict_flag`/`conflicting_sources` 산출 방식.

export 파일명에는 생성일 스탬프 `yymmdd`(`-` 없음)가 붙는다(예: `combined_260728.xlsx`). export는 매 실행마다 재생성되는 뷰이므로 동결본 'final'이 아니기 때문. 아래 행 수는 2026-07-28 스냅샷 기준.

- `human_serum_yymmdd.xlsx` — 316행
- `mouse_serum_yymmdd.xlsx` — 715행
- `mouse_feces_yymmdd.xlsx` — 899행
- `combined_yymmdd.xlsx` — 고유 InChIKey 1,721개, 각 화합물의 출처 데이터셋을 `datasets` 컬럼에 기록.

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

- **2026-07-28** — 이식성 + drug/food 컬럼 정리:
  - 파이프라인 전체의 `read_text`/`write_text`에 **UTF-8 고정** — `Path.read_text()`가 OS 로케일(Windows는 cp1252) 기본이라 UTF-8 JSON 캐시에서 `UnicodeDecodeError` 발생했음. 이제 Windows에서도 실행됨.
  - **export 파일명**을 `{name}_final.xlsx` → `yymmdd` 생성일 스탬프(`combined_260728.xlsx`)로 변경 — export는 매 실행 재생성되는 뷰라 동결본 'final'이 아니기 때문. `compare_legacy.py`는 최신 날짜 스냅샷을 glob으로 자동 선택.
  - 파이프라인 입력 캐시(`.work/interim/*.json`, `*_step4_classified.parquet`)를 **git에 강제 추적** — clone 후 수집 재실행 없이 `normalize.py` + `export_view.py`만으로 재현 가능.
  - **`DrugCentral` 컬럼 추가** — drug/food 근거로 인용되는데 컬럼이 없어 근거 감사가 불가능했음(72개 화합물에 DrugCentral ID 존재).
  - **`drug_food_basis` 제거** — `DrugBank`/`DrugCentral`/`FooDB` ID 컬럼이 근거를 직접 보여줘서, 뭉친 `drug:DB1,DB2; food:DB3` 문자열이 중복이 됨. 결론인 `drug_food`는 유지.

- **2026-07-27** — 교수님 회의 스키마 변경 (사람/쥐 범위로 축소):
  - 데이터셋 키 `human` → `human_serum` 리네임(`config.SPECIES`, seed/source 맵, 대조 대상). `data/human/` raw 폴더명은 raw 보존 원칙상 유지, 라벨만 변경.
  - classification **앞**에 **`drug_food`** 표시 플래그(+ `drug_food_basis`) 추가: drug = DrugBank/DrugCentral 존재, food = FooDB 존재. 1차 필터 표시일 뿐 행 삭제 없음(363개 표시: food 164 / drug 109 / drug+food 90).
  - **classification v4** — 우선순위 규칙 폐기. 컬럼이 각 DB 판정을 병렬 나열(`ChEBI:…; HMDB:…; COCONUT:…; MMMDB:…`), 단일 라벨 강제 안 함. `classify_row_v1..v3`는 `classify.py`에 박제 보존; v3 산출물은 전후 비교용으로 `data/normalized/_v3_frozen_20260727/`에 보관. Summary 카운트는 배타형 → 근거포함 집계 + conflict 행. Classification Rules 시트도 v4 방식으로 재작성.

- **2026-07-23** — HMDB Source 서브트리 + 기원 카테고리화:
  - 6.1GB `hmdb_metabolites.xml`(217,920 레코드)을 스트리밍 파싱으로 전수 프로파일 — `docs/HMDB_structure_guide.md` 참조
  - HMDB `Disposition > Source`가 endo/exo 이분법이 **아님**을 확정: 형제 라벨 6개(Food 146,742 / Endogenous 145,377 / Biological 144,377 / Synthetic 193 / Environmental 162 / **Exogenous 6**); source 태깅 화합물의 93%가 라벨 3개 동시 보유(Biological & Endogenous & Food, 139,977)
  - 신규 `pipeline/build_source_hierarchy.py` → `data/reference/hmdb_source_hierarchy.json` (457-term roll-up 맵, term → 6개 최상위 버킷 + 트리 레벨)
  - `normalize.py`가 `compound_origins` 각 행에 `origin_category`(6버킷 roll-up)·`origin_level`(트리 깊이) 주석 추가; 하위호환(컬럼 추가만)
  - `export_view.py`에 `hmdb_origin_category` 요약 컬럼 추가(종명까지 뭉친 `hmdb_origin`과 별도로 버킷만)
  - 재현 baseline: 새 컬럼 반영해 `compound_origins` 지문만 갱신(다른 테이블은 손대지 않음)
  - **알려진 이슈**: `compounds` 지문이 clean checkout에서도 baseline과 DIFFER (이번 변경 이전부터 존재; `.work/interim/` 캐시가 지문 생성 당시와 드리프트) — baseline 재생성으로 덮지 않고 별도 조사 예정

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
