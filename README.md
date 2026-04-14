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

| Category | Count | % |
|----------|-------|---|
| PubChem + KEGG + HMDB | 101 | 11.2% |
| PubChem + KEGG only | 29 | 3.2% |
| PubChem + HMDB only | 79 | 8.8% |
| PubChem only | 657 | 72.8% |
| Unresolved | 36 | 4.0% |
| **Total** | **902** | **100%** |