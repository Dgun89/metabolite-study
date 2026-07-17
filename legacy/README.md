# metabolite-study

## Scripts
| File                           | Description                                                        |
|--------------------------------|--------------------------------------------------------------------|
| 01_fetch_pubchem_cid.py        | Fetch PubChem CIDs from compound names via PubChem API             |
| 02_fill_cid_to_excel.py        | Write resolved CIDs into Excel file                                |
| 03_check_resolution_rate.py    | Check empty rows and calculate CID resolution rate (71.6%)         |
| 04_extract_kegg_hmdb.py        | Extract KEGG and HMDB IDs from PubChem PUG View                    |
| 05_check_duplicates.py         | Detect and report duplicate entries in dataset                     |
| 06_coconut_api_test.py         | Test COCONUT API login and compound search                         |
| 07_remove_duplicates.py        | Remove duplicate entries: 1015 → 902 rows                         |
| 08_resolve_by_inchikey.py      | Resolve unresolved metabolites via COCONUT API → InChIKey → PubChem CID |
| 09_check_resolution_rate2.py   | Check resolution rates after InChIKey-based search                 |
| 10_extract_kegg_hmdb2.py       | Extract KEGG and HMDB IDs for newly resolved metabolites via PubChem PUG View |
| 11_fill_inchikey.py            | Fill InChIKey column via COCONUT API                               |
| 12_test_unichem.py             | Test UniChem API for HMDB extraction                               |
| 13_fill_hmdb_unichem.py        | Attempt to fill HMDB via UniChem API (limited results)             |
| 14_fill_kegg_hmdb_chebi.py     | Fill KEGG and HMDB via ChEBI 2.0 REST API                          |
| 15_fill_kegg_hmdb_mw.py        | Fill KEGG and HMDB via Metabolomics Workbench REST API (InChIKey)  |
| 16_filter_exogenous.py         | Classify metabolites as endogenous/exogenous/unverified via ChEBI roles classification |
| 17_extract_enzymes_kegg.py     | Extract enzyme EC numbers for each metabolite via KEGG REST API                       |
| 18_extract_enzymes_reactome.py | Extract catalyst activity information via Reactome ContentService API (ChEBI ID based) |
| 19_fill_hmdb_classification.py | Supplement endogenous/exogenous classification using HMDB XML source data (ChEBI priority) |
| 19-1_fill_hmdb_classification_hmdb_priority.py | Supplement endogenous/exogenous classification using HMDB XML source data (HMDB priority) |
| validate.py                    | Cross-validate compound IDs against MetaboAnalyst mapping results          |
| metabo1.py                     | Extract endogenous metabolites with KEGG IDs for MetaboAnalyst input       |
| 20_enrich_via_metaboanalyst_hmdb.py | Enrich KEGG IDs and add SMILES via MetaboAnalyst compound mapping (HMDB ID input)      |
| validate.py                          | Cross-validate compound IDs against MetaboAnalyst mapping results                     |
| metabo1.py                           | Extract endogenous metabolites with KEGG/HMDB IDs for MetaboAnalyst input             |
| 21_extract_enzymes_hmdb.py     | Extract enzyme gene names from HMDB XML protein_associations field                     |
| 22_fill_smiles_pubchem.py      | Fill SMILES column via PubChem CID batch API (CID-based)                               |
| format_excel.py                | Reusable Excel formatting: color-coded headers and Legend sheet                        |
| 23_fill_inchikey_kegg_hmdb_from_pubchem.py | Fill InChIKey via PubChem CID, then extract KEGG/HMDB via ChEBI for new entries |
| 24_extract_enzymes_brenda.py   | Extract EC numbers from BRENDA SOAP API via compound name lookup          |
| 25_classify_origin_coconut.py  | Classify unverified compounds (endogenous/exogenous) via COCONUT organism (taxonomicRange) data, matched by InChIKey through local full-DB CSV join |
| 26_reclassify_unverified_chebi.py | Re-classify remaining unverified compounds via ChEBI roles API (human metabolite → endogenous) |
| 27_add_chebi_roles.py | Add chebi_roles column via ChEBI API; rename compound_origin → classification, origin_evidence → classification_basis; restructure column groups |
| 28_reclassify_via_kegg_hmdb_chebi.py | Attempt ChEBI ID lookup via KEGG API and UniChem (HMDB→ChEBI) for remaining 11 unverified compounds (0 reclassified) |
| 29_restore_coconut_basis.py | Restore COCONUT-based classification_basis for unverified compounds overwritten during step26-28 ChEBI re-queries |
| 30_recover_inchikey_and_reclassify.py | Recover missing InChIKeys (36 rows) via local COCONUT canonical_smiles + RDKit for 27 CNP compounds (866→893); reclassify 2 unverified→exogenous using COCONUT organism data (440→438) |

---

## Progress Log

### Day 3
- Removed duplicates: 1015 → 902 rows
- Renamed files to meaningful names
- Analyzed PubChem search failures (case mismatch, exact matching)
- Identified InChIKey-based search as solution

| Category | Count | % |
|----------|-------|---|
| PubChem + KEGG + HMDB | 101 | 11.2% |
| PubChem + KEGG only | 29 | 3.2% |
| PubChem + HMDB only | 79 | 8.8% |
| PubChem only | 437 | 48.4% |
| Unresolved | 256 | 28.4% |
| **Total** | **902** | **100%** |

---

### Day 4
- Built COCONUT API → InChIKey → PubChem CID pipeline (08_resolve_by_inchikey.py)
- Resolved 220 additional metabolites
- Remaining 36 confirmed as unregistered in PubChem
- Attempted KEGG/HMDB extraction for newly resolved metabolites (10_extract_kegg_hmdb2.py)
- Applied .env for API credential security
- File cleanup and reorganization

| Category | Count | % |
|----------|-------|---|
| PubChem + KEGG + HMDB | 101 | 11.2% |
| PubChem + KEGG only | 29 | 3.2% |
| PubChem + HMDB only | 79 | 8.8% |
| PubChem only | 657 | 72.8% |
| Unresolved | 36 | 4.0% |
| **Total** | **902** | **100%** |

### Day 5
- Filled InChIKey for 646 metabolites via COCONUT API (11_fill_inchikey.py)
- Explored UniChem API for HMDB extraction (limited coverage for rare natural products)
- Discovered ChEBI 2.0 REST API endpoints
- Filled KEGG/HMDB via ChEBI API (14_fill_kegg_hmdb_chebi.py)
- Filled KEGG/HMDB via Metabolomics Workbench API using InChIKey (15_fill_kegg_hmdb_mw.py)

| Category | Count | % |
|----------|-------|---|
| PubChem + KEGG + HMDB | 125 | 13.9% |
| PubChem + KEGG only | 20 | 2.2% |
| PubChem + HMDB only | 89 | 9.9% |
| PubChem only | 632 | 70.1% |
| Unresolved | 36 | 4.0% |
| **Total** | **902** | **100%** |
| InChIKey | 826 | 91.6% |

### Day 6(260604)
- Classified 902 metabolites as endogenous/exogenous/unverified using ChEBI 2.0 REST API
- Endpoint: `backend/api/public/es_search` (InChIKey → ChEBI ID) + `compound/{id}` (roles_classification)
- Added `filter_status` column to dataset (no rows removed)

| Category | Count | % |
|----------|-------|---|
| Endogenous | 45 | 5.0% |
| Exogenous | 135 | 15.0% |
| Unverified | 722 | 80.0% |
| **Total** | **902** | **100%** |

Note: High unverified rate reflects the nature of the dataset (COCONUT-based natural products with limited ChEBI coverage)

- Extracted enzyme EC numbers via KEGG REST API (`link/enzyme/cpd:{KEGG_ID}`)
- Stored as semicolon-separated EC numbers in `kegg_enzymes` column

| Category | Count |
|----------|-------|
| KEGG ID available | 145 |
| Enzyme info retrieved | 75 |
| No enzyme info (KEGG unregistered) | 70 |
| No KEGG ID | 757 |

- Extracted catalyst activity names via Reactome ContentService API
- Stored ChEBI ID and catalyst activity names as new columns
- Note: Reactome provides activity names (e.g., 'monooxygenase activity of CYP2W1'), not EC numbers

| Category | Count |
|----------|-------|
| ChEBI ID retrieved | 290 / 902 |
| Reactome catalyst retrieved | 28 / 902 |

### Day 7(260605)
- Parsed HMDB XML (hmdb_metabolites.xml) to extract Source field (Endogenous / Food / Drug etc.)
- Two approaches tested depending on DB priority when ChEBI and HMDB conflict

| Category | Previous (ChEBI only) | Approach A (ChEBI priority) | Approach B (HMDB priority) |
|----------|-----------------------|-----------------------------|----------------------------|
| Endogenous | 45 | 88 | 140 |
| Exogenous | 135 | 146 | 94 |
| Unverified | 722 | 668 | 668 |

- 52 compounds show conflicting classification between ChEBI and HMDB
- Awaiting guidance on which approach to adopt

### Day 8
- Explored MetaboAnalyst pathway analysis using 45 endogenous metabolites with KEGG IDs
  - Top pathway: Tryptophan metabolism (p = 0.0017, Impact = 0.213)
- Cross-validated PubChem CIDs against MetaboAnalyst compound mapping (validate.py)
  - Corrected 1 PubChem CID: 3-Methyladenine (135398661 → 1673), documented in corrections.md
- Attempted KEGG ID expansion via PubChem xrefs (721 targets → 7 new KEGG IDs)
- Enriched database via MetaboAnalyst compound mapping using 138 endogenous HMDB IDs
  - Added 2 new KEGG IDs
  - Added SMILES column (137 / 902 filled)

| Item | Before | After |
|------|--------|-------|
| KEGG ID | 145 | 154 |
| SMILES | 0 | 137 |

### Day 9
- Extracted enzyme information from HMDB XML protein_associations field
- Added `hmdb_enzymes` column (gene name based)

| DB | Enzyme coverage |
|----|----------------|
| KEGG only | 32 |
| HMDB only | 18 |
| Reactome only | 7 |
| Combined (any) | 104 / 902 (11.5%) |

- Filled SMILES column via PubChem CID batch API

| Item | Before | After |
|------|--------|-------|
| SMILES | 137 / 902 (15%) | 866 / 902 (96%) |

- Reorganized Excel columns with color-coded headers and Legend sheet
- Created reusable format_excel.py for consistent formatting across future updates

- Filled InChIKey for 40 compounds via PubChem CID batch API (826 → 866 / 902)
- Extracted KEGG/HMDB for newly acquired InChIKeys via ChEBI API
  - KEGG: 0 new (peptides not registered in KEGG)
  - HMDB: 7 new (dipeptides found in HMDB)
- Added Summary sheet to Excel (auto-updated via format_excel.py)

| Item | Before | After |
|------|--------|-------|
| InChIKey | 826 / 902 | 866 / 902 |
| HMDB | 214 / 902 | 221 / 902 |

### Day 10
- Set up BRENDA SOAP API (registered account, zeep library)
- Extracted EC numbers from BRENDA for all 902 compounds (113 / 902 matched)
- Updated Excel Summary sheet with detailed enzyme source breakdown
- Added Source column to Legend sheet

| Item | Before | After |
|------|--------|-------|
| BRENDA enzymes | 0 | 113 / 902 (12.5%) |
| Enzyme coverage (total unique) | 104 / 902 (11.5%) | 144 / 902 (16.0%) |

### Day 11 (260611)
- Improved endogenous/exogenous classification of 668 unverified compounds using COCONUT organism data
- Found COCONUT search API requires auth (401) and stored CNP IDs are stale in COCONUT 2.0 (404)
  → switched to bulk CSV download + local InChIKey join (no API calls)
- Matched against full COCONUT CSV (738,827 rows) by InChIKey (exact + 14-char skeleton), CNP ID fallback
- Rule: taxonomicRange contains Homo sapiens → endogenous; non-human organisms only → exogenous; no organism data → unverified
- Added columns: `coconut_organisms`, `coconut_match_key`, `origin_evidence`
- Added "Origin Evidence" group to Legend + new Summary section; auto-reorder columns by group hierarchy

| Category | Before (Day7 B) | After (COCONUT) |
|----------|-----------------|-----------------|
| Endogenous | 140 | 143 |
| Exogenous | 94 | 283 |
| Unverified | 668 | 476 |
| **Total** | **902** | **902** |

| Reclassification outcome | Count |
|--------------------------|-------|
| → endogenous (Homo sapiens) | 3 |
| → exogenous (non-human organism) | 189 |
| Unverified: in COCONUT, no organism data | 422 |
| Unverified: not in COCONUT release | 54 |

| Match method (192 reclassified) | Count |
|---------------------------------|-------|
| InChIKey (exact) | 108 |
| InChIKey skeleton (14-char) | 83 |
| CNP ID | 1 |

#### Day 12 (260612)
Step 26: ChEBI roles re-attempt
- Targeted remaining 476 unverified compounds only
- ChEBI ID already available (31) → roles query directly; InChIKey available → ChEBI ID → roles
- Rule: `human metabolite` role → endogenous; other roles → exogenous

| Reclassification | Count |
|---|---|
| → endogenous | 0 |
| → exogenous | 36 |
| Unverified (no ChEBI match / no roles) | 440 |

#### Cumulative classification result

| compound_origin | step24 | step25 | step26 |
|---|---|---|-------|
| endogenous | 140 | 143 | 143 |
| exogenous | 94 | 283 | 319 |
| unverified | 668 | 476 | 440 |

- **Conclusion**: ChEBI, HMDB, COCONUT all exhausted. Remaining 440 unverified compounds have no classification evidence in current public DBs under perspective B (human metabolite DB standard).

#### Step 27: Add chebi_roles column + column restructure
- Added `chebi_roles` column (ChEBI roles API, 326건 조회 → 216건 획득)
- Renamed: `compound_origin` → `classification`, `origin_evidence` → `classification_basis`
- Restructured column groups:
  - Classification: `classification`
  - Classification Sources: `hmdb_origin`, `coconut_organisms`, `chebi_roles`
  - Classification Metadata: `coconut_match_key`, `classification_basis`

#### Step 28: ChEBI ID lookup via KEGG / UniChem
- Targeted 11 unverified compounds with KEGG or HMDB ID but no ChEBI ID
- KEGG → KEGG REST API → ChEBI ID (8건 시도)
- HMDB → UniChem API → ChEBI ID (5건 시도)
- Result: 0 / 11 reclassified → all 11 compounds not registered in ChEBI

#### Final classification result

| compound_origin | step24 | step25 | step26 | step27/28 |
|---|---|---|---|---|
| endogenous | 140 | 143 | 143 | 143 |
| exogenous | 94 | 283 | 319 | 319 |
| unverified | 668 | 476 | 440 | 440 |

**Conclusion**: ChEBI, HMDB, COCONUT, KEGG→ChEBI, HMDB→UniChem→ChEBI 모든 소스 소진. 440건은 현재 공개 DB 기준 분류 근거 없음.

#### Step 29: Restore COCONUT classification_basis
- classification_basis for unverified compounds had been overwritten by ChEBI results in step26-28
- Restored from step25 origin_evidence via Database ID mapping
- Result: COCONUT: no organism data (410) / COCONUT: not in release (30)
- Note: 36 fewer than step25 (422+54=476) because those were reclassified to exogenous by ChEBI in step26

#### Step 30: Recover missing InChIKeys + reclassify (260710)
- 36 rows had no InChIKey (SMILES/PubChem/KEGG/HMDB/ChEBI all empty); 27 CNP + 9 PEP
- Recovered SMILES for all 27 CNP from local COCONUT (canonical_smiles), computed InChIKey via RDKit MolToInchiKey → InChIKey coverage 866 → 893
- ChEBI 0/27, HMDB 0/27: these compounds are not registered in public metabolite DBs (mostly complex/synthetic IUPAC-named structures)
- Reclassified 2 unverified → exogenous using COCONUT organism data (non-human source): unverified 440 → 438, exogenous 319 → 321
- Remaining 24 stay unverified (no signal in any DB); 9 PEP rows not in COCONUT, InChIKey unrecoverable via this route
- Output: etc/metabolites_step30.xlsx (Data/Legend/Summary, 902 rows × 18 cols)
