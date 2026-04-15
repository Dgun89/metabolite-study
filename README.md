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