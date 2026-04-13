# metabolite-study

## Scripts
| File                        |Description                                                 |
|-----------------------------|------------------------------------------------------------|
| 01_fetch_pubchem_cid.py     | Fetch PubChem CIDs from compound names via PubChem API     |
| 02_fill_cid_to_excel.py     | Write resolved CIDs into Excel file                        |
| 03_check_resolution_rate.py | Check empty rows and calculate CID resolution rate (71.6%) |
| 04_extract_kegg_hmdb.py     | Extract KEGG and HMDB IDs from PubChem PUG View            |
| 05_check_duplicates.py      | Detect and report duplicate entries in dataset             |
| 06_coconut_api_test.py      | Test COCONUT API login and compound search                 |