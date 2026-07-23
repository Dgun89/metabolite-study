# HMDB `hmdb_metabolites.xml` — 구조 & 온톨로지 가이드

전체 파일(6.1 GB, 217,920 `<metabolite>` 레코드)을 스트리밍으로 한 번 완주해서 뽑은 실측 스키마입니다. HMDB 버전 **5.0**, 네임스페이스 `http://www.hmdb.ca`.

> 이 파일은 통째로 메모리에 올릴 수 없습니다(6 GB). 항상 `lxml.etree.iterparse(..., tag="{http://www.hmdb.ca}metabolite")` + `elem.clear()`로 레코드 단위 스트리밍하세요. 전체 스캔은 이 머신에서 약 3분 20초 걸립니다.

## 1. 최상위 형태

```
<hmdb xmlns="http://www.hmdb.ca">
  <metabolite> … </metabolite>   ← 217,920개, 순차 나열
  <metabolite> … </metabolite>
  ...
</hmdb>
```

각 `<metabolite>`는 **174개**의 서로 다른 요소 경로를 가질 수 있습니다. 크게 세 부류:

1. **스칼라 메타데이터** (레코드당 1개, 텍스트값) — 식별자, 물성, 이름
2. **반복 블록** (레코드당 N개) — synonyms, pathways, protein_associations, concentrations, spectra …
3. **온톨로지/분류 트리** — `taxonomy`(ChemOnt 화학분류) + `ontology`(4-root 계층)

## 2. 스칼라 메타데이터 (depth-2, 레코드당 1개)

`text_fill%` = 217,920개 중 그 필드가 **비어있지 않은** 비율. 100%면 항상 채워짐, 낮으면 sparse.

| 필드 | 채움율 | 예시 |
|---|---|---|
| `accession` | 100% | HMDB0000001 (기본 HMDB id) |
| `name` | 100% | 1-Methylhistidine |
| `chemical_formula` | 100% | C7H11N3O2 |
| `inchi` / `inchikey` | 100% | InChIKey=BRMWTNUJHUMWMS-LURJTMIESA-N |
| `smiles` | 100% | CN1C=NC(C[C@H](N)C(O)=O)=C1 |
| `average_molecular_weight` / `monisotopic_molecular_weight` | 100% | 169.1811 / 169.085… |
| `iupac_name` / `traditional_iupac` | 99.5% | (2S)-2-amino-3-… |
| `status` | 100% | quantified / detected / expected / predicted |
| `description` | 92.8% | 서술형 텍스트 |
| `state` | 43.9% | Solid / Liquid / Gas |
| **교차참조 식별자** | | |
| `pubchem_compound_id` | 47.9% | 92105 |
| `foodb_id` | 34.2% | FDB093588 |
| `chemspider_id` | 14.4% | 83153 |
| `cas_registry_number` | 7.2% | 332-80-9 |
| `chebi_id` | 6.3% | 50599 |
| `wikipedia_id` | 3.2% | Methylhistidine |
| `knapsack_id` | 3.7% | C00052105 |
| `kegg_id` | 3.1% | C01152 |
| `drugbank_id` | 1.5% | DB04151 |
| `biocyc_id` | 1.2% | CPD-313 |
| `vmh_id` / `metlin_id` / `bigg_id` / `pdb_id` / `phenol_explorer_compound_id` | <1% | |

> **핵심**: `inchikey`는 100% 채워지는데 `kegg_id`·`chebi_id` 등 외부 id는 대부분 3~50%만 채워집니다. InChIKey를 조인 키로 쓰는 이 프로젝트의 결정이 스키마상 옳습니다 — 다른 어떤 축보다 커버리지가 높습니다.

## 3. 반복 블록 (레코드당 여러 개)

`max/record`는 한 레코드에서 관측된 최대 반복 수.

| 블록 | 컨테이너 → 반복요소 | max/record | 반복요소의 자식 |
|---|---|---|---|
| 동의어 | `synonyms/synonym` | 636 | (텍스트) |
| 예측 물성 | `predicted_properties/property` | — | kind, source, value |
| 실험 물성 | `experimental_properties/property` | — | kind, source, value |
| 경로 | `biological_properties/pathways/pathway` | **47,974** | name, kegg_map_id, smpdb_id |
| 단백질 연관 | `protein_associations/protein` | 1,159 | name, gene_name, uniprot_id, protein_accession, protein_type |
| 정상 농도 | `normal_concentrations/concentration` | — | biospecimen, value, units, subject_age/sex/condition, references |
| 이상 농도 | `abnormal_concentrations/concentration` | — | biospecimen, patient_age/sex/information, references |
| 질병 | `diseases/disease` | — | name, omim_id, references |
| 스펙트럼 | `spectra/spectrum` | — | spectrum_id, type |
| 위치 | `biological_properties/{biospecimen,cellular,tissue}_locations` | — | 텍스트 리스트 |
| 문헌 | `general_references/reference` | — | pubmed_id, reference_text |
| 보조 accession | `secondary_accessions/accession` | — | (이전/병합된 HMDB id) |

## 4. 두 개의 분류 체계 — `taxonomy` vs `ontology`

HMDB는 **완전히 다른 두 분류 트리**를 담고 있습니다. 혼동 주의:

### 4a. `<taxonomy>` — 화학 구조 분류 (ChemOnt / ClassyFire)
분자의 **구조**가 무엇인가. 단일 경로 계층:
```
kingdom      → Organic compounds
super_class  → Organic acids and derivatives
class        → Carboxylic acids and derivatives
sub_class    → Amino acids, peptides, and analogues
direct_parent→ Histidine and derivatives
molecular_framework, alternative_parents[], substituents[], external_descriptors[]
```
스칼라 5단계 + 다중값 리스트. "이 화합물이 화학적으로 어떤 분류인가"에 답할 때 사용.

### 4b. `<ontology>` — 생물학적/기능적 온톨로지 (4-root 계층)
분자가 **무엇을 하는가 / 어디서 오는가**. 재귀 트리 구조:
```
<ontology>
  <root>                       ← 4개 최상위 축
    <term>Disposition</term>
    <definition>…</definition>
    <level>1</level>
    <descendants>
      <descendant>             ← 재귀적으로 최대 6단계
        <term>…</term> <level>2</level> <parent_id>…</parent_id>
        <type>parent|child</type>
        <synonyms><synonym>…</synonym></synonyms>
        <descendants>…</descendants>
      </descendant>
    </descendants>
  </root>
```

**노드 필드**: `term`(라벨), `definition`, `level`(1–6), `parent_id`(숫자 id — 단, `<id>` 요소는 없음. 트리 구조는 중첩으로만 정의됨), `type`(parent/child), `synonyms`.

**4개 root와 커버리지** (217,920개 중):

| root | 커버리지 | 무엇 | 주요 level-2 |
|---|---|---|---|
| **Disposition** | 70% | 물질의 소재·기원·노출경로 | Biological location(69%), Source(69%), Route of exposure(66%) |
| **Role** | 67% | 생물학적/산업적 역할 | Biological role(67%), Industrial application(52%), Environmental role, Indirect biological role |
| **Process** | 67% | 관여 과정 | Naturally occurring process → Biological process(66%), Industrial process |
| **Physiological effect** | 60% | 생리 효과 | Organoleptic effect(41%), Health effect(19%) |

**온톨로지 규모**: 2,009개 고유 term, 2,005개 parent→child 엣지, 최대 깊이 6.

### 4c. `Disposition → Source` 서브트리 — endo/exo는 이분법이 아니다

`build_hmdb_index.py`는 `ontology`에서 `term=="Source"`를 찾아 그 하위 term(Endogenous/Food/…)을 `hmdb_source` 리스트로 뽑습니다. 이 서브트리의 실제 구조를 전수 실측한 결과가 아래이며, **정규화 스키마 설계의 핵심 근거**입니다.

**Source 직속 자식은 6개이고, 서로 부모-자식이 아니라 형제(sibling)입니다** (217,920개 중):

| Source 직속 term | 태깅 화합물 | 하위 계층 |
|---|---:|---|
| Food | 146,742 | (리프) |
| Endogenous | 145,377 | (리프) |
| Biological | 144,377 | Animal / Plant→과·종 / Microbe→속·종 (깊이 4까지) |
| Synthetic | 193 | Personal care product |
| Environmental | 162 | Wastewater / Sludge / Tobacco smoke 등 |
| **Exogenous** | **6** | (리프) |

즉 HMDB에서 `Exogenous`는 `Endogenous`의 반대 우산 카테고리가 **아니라**, 나머지 5개 어디에도 안 담긴 잔여 버킷(6개)일 뿐입니다. endo/exo를 대칭 쌍으로 보는 통념과 달리, 이 온톨로지에서 둘은 같은 층위 라벨 6개 중 2개이고 규모가 24,000배 차이납니다.

**결정적 증거 — 상호배타가 아니다**: Source 태깅 화합물 150,804개 중 **140,067개(93%)가 라벨을 3개씩 동시 보유**합니다. 압도적 최빈 조합은 `Biological & Endogenous & Food`(139,977개) — "체내에서 만들어지면서, 음식에도 있고, 생물기원"인 대사 중간체(당·아미노산·지질)입니다. 산술로도: Endogenous(145,377) + Food(146,742) = 292,119 > 총 150,804이므로 최소 141,315개가 두 라벨을 겹쳐 가집니다.

**"endo 단독"의 함정**: Endogenous 라벨 **보유** 화합물은 145,377개(source-tagged의 96.4%)로, `classify.py`의 E2 규칙이 endogenous로 판정하는 근거가 됩니다. 반면 Endogenous **단독**(다른 Source 라벨 없음)은 3,724개(endo-labeled의 2.6%)뿐입니다. 이 둘을 혼동하면 "내인성 화합물이 얼마 안 된다"는 오해가 생기지만, 실제로는 대다수 내인성 대사체가 동시에 식이·생물 기원이기도 한 것이 정상입니다.

> **정규화 스키마에 주는 시사점**: 단일 라벨 `classification`(endo/exo)으로는 이 다중 소속을 표현할 수 없습니다. `normalize.py`는 `hmdb_source` 리스트를 라벨별 1행으로 펼쳐 `compound_origins`(long)에 보존하고, 각 행에 `origin_category`(6버킷 roll-up)와 `origin_level`(트리 깊이)을 주석합니다. 이 roll-up 맵은 `pipeline/build_source_hierarchy.py`가 raw XML에서 생성해 `data/reference/hmdb_source_hierarchy.json`(457 term)에 저장합니다. export 뷰(`export_view.py`)에는 종명까지 뭉친 `hmdb_origin`과 별도로 6버킷 요약 `hmdb_origin_category` 컬럼을 추가했습니다.

## 5. 산출물 (이 분석의 결과)

- `hmdb_schema_map.csv` — 174개 전체 요소 경로 × (출현수, 등장 레코드수, 채움율, 레코드당 최대반복, 예시)
- `hmdb_ontology_edges.csv` — 2,005개 parent→child 엣지 (level, 주석 레코드수)
- `hmdb_ontology_tree.json` — 4-root 중첩 트리 (term/level/n_records/definition/children), 기계 판독용
- `hmdb_ontology_tree.txt` — 사람이 읽는 들여쓰기 트리 (term별 레코드수 포함)
- `hmdb_ontology_sunburst.html` — **인터랙티브 선버스트** (클릭하면 하위 축으로 줌인)
- `hmdb_ontology_overview.png` — 4 root × level-2 커버리지 정적 요약
- `hmdb_source_cooccurrence.png` — Source 6라벨 규모·다중소속(93% 3중 태깅)·조합 3패널
- `source_cooccurrence.json` — Source 라벨 단일/쌍/조합 빈도 실측
- `explore_hmdb.py` — 재실행 가능한 스트리밍 프로파일러
- `pipeline/build_source_hierarchy.py` → `data/reference/hmdb_source_hierarchy.json` — Source 서브트리 계층 맵(term→6버킷, 457 term)

## 6. 재실행

```bash
python explore_hmdb.py          # 전체 스캔 (~3분 20초)
python explore_hmdb.py 8000     # 앞 8000 레코드만 샘플 (~12초)
```
메모리는 상수(레코드 단위 clear). 다른 환경에선 `explore_hmdb.py` 상단 `XML` 경로만 조정하세요.
