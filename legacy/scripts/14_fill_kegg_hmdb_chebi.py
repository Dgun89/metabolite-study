# import requests


# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 1. Test CheBI
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# inchikey = "HCZHHEIFKROPDY-UHFFFAOYSA-N"

# # 1단계: InChIKey → ChEBI ID
# url1 = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
# res1 = requests.get(url1)
# chebi_id = res1.json()['results'][0]['_id']
# print(f"ChEBI ID: {chebi_id}")

# # 2단계: ChEBI ID → KEGG/HMDB
# url2 = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
# res2 = requests.get(url2)
# xrefs = res2.json()['database_accessions'].get('MANUAL_X_REF', [])
# for xref in xrefs:
#     if xref['source_name'] == 'KEGG COMPOUND':
#         print(f"KEGG: {xref['accession_number']}")
#     if xref['source_name'] == 'HMDB':
#         print(f"HMDB: {xref['accession_number']}")

# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2. Test CheBI
# ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 14_fill_kegg_hmdb_chebi.py
# Target: rows with InChIKey but missing KEGG or HMDB in metabolites_step11.xlsx

import requests
import pandas as pd
import time

# ─────────────────────────────
# 1. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel("metabolites_step11.xlsx")

target = df[df['InChIKey'].notna() & (df['KEGG'].isna() | df['HMDB'].isna())]
total = len(target)
print(f"Target: {total} rows")

# ─────────────────────────────
# 2. 함수 정의
# ─────────────────────────────
def get_kegg_hmdb_from_chebi(inchikey):
    result = {"kegg": None, "hmdb": None}

    # Step 1: InChIKey → ChEBI ID
    url1 = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
    try:
        res1 = requests.get(url1, timeout=10)
        if res1.status_code != 200 or not res1.json()['results']:
            return result
        chebi_id = res1.json()['results'][0]['_id']
    except Exception:
        return result

    # Step 2: ChEBI ID → KEGG/HMDB
    url2 = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
    try:
        res2 = requests.get(url2, timeout=10)
        if res2.status_code != 200:
            return result
        xrefs = res2.json()['database_accessions'].get('MANUAL_X_REF', [])
        for xref in xrefs:
            if xref['source_name'] == 'KEGG COMPOUND':
                result['kegg'] = xref['accession_number']
            if xref['source_name'] == 'HMDB':
                result['hmdb'] = xref['accession_number']
    except Exception:
        return result

    return result

# ─────────────────────────────
# 3. 루프 실행
# ─────────────────────────────
for count, idx in enumerate(target.index, start=1):
    inchikey = df.at[idx, 'InChIKey']
    print(f"[{count}/{total}] {df.at[idx, 'QualitativeResults']} → ", end="")

    ids = get_kegg_hmdb_from_chebi(inchikey)

    if ids['kegg'] and pd.isna(df.at[idx, 'KEGG']):
        df.at[idx, 'KEGG'] = ids['kegg']
    if ids['hmdb'] and pd.isna(df.at[idx, 'HMDB']):
        df.at[idx, 'HMDB'] = ids['hmdb']

    print(f"KEGG: {ids['kegg']} HMDB: {ids['hmdb']}")
    time.sleep(0.5)

# ─────────────────────────────
# 4. 저장
# ─────────────────────────────
df.to_excel("metabolites_step14.xlsx", index=False)
print("Saved successfully!")