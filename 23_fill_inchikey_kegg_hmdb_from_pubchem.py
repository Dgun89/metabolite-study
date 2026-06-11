# ────────────────────────────────────────────────────────
# 23_fill_inchikey_from_pubchem.py
# ────────────────────────────────────────────────────────
import requests
import pandas as pd
import time
from format_excel import apply_format

INPUT_FILE  = "metabolites_step22.xlsx"
OUTPUT_FILE = "metabolites_step23.xlsx"

df = pd.read_excel(INPUT_FILE)

# ─────────────────────────────
# 1. PubChem CID → InChIKey
# ─────────────────────────────
targets = df[df['InChIKey'].isna() & df['PubChem'].notna()]
print(f"InChIKey 대상: {len(targets)}개")

BATCH_SIZE = 100
cids = [int(x) for x in targets['PubChem'].tolist()]
batches = [cids[i:i+BATCH_SIZE] for i in range(0, len(cids), BATCH_SIZE)]
inchikey_map = {}

for i, batch in enumerate(batches):
    cids_str = ",".join(map(str, batch))
    try:
        resp = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids_str}/property/InChIKey/JSON",
            timeout=30
        )
        if resp.status_code == 200:
            for prop in resp.json()['PropertyTable']['Properties']:
                inchikey_map[prop['CID']] = prop['InChIKey']
        print(f"배치 [{i+1}/{len(batches)}] 완료 → 누적: {len(inchikey_map)}개")
    except Exception as e:
        print(f"배치 [{i+1}] 오류: {e}")
    time.sleep(0.5)

for idx, row in targets.iterrows():
    cid = int(row['PubChem'])
    if cid in inchikey_map:
        df.at[idx, 'InChIKey'] = inchikey_map[cid]

print(f"InChIKey 채워진 행: {df['InChIKey'].notna().sum()} / {len(df)}")

# ─────────────────────────────
# 2. 새 InChIKey → ChEBI → KEGG/HMDB
# ─────────────────────────────
def get_chebi_id(inchikey):
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if not data.get('results'):
            return ""
        return str(data['results'][0]['_id'])
    except:
        return ""

def get_kegg_hmdb(chebi_id):
    result = {"kegg": None, "hmdb": None}
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
    try:
        res = requests.get(url, timeout=10)
        xrefs = res.json().get('database_accessions', {}).get('MANUAL_X_REF', [])
        for xref in xrefs:
            if xref['source_name'] == 'KEGG COMPOUND':
                result['kegg'] = xref['accession_number']
            if xref['source_name'] == 'HMDB':
                result['hmdb'] = xref['accession_number']
    except:
        pass
    return result

new_inchikey_targets = df[
    df['InChIKey'].isin(inchikey_map.values()) &
    (df['KEGG'].isna() | df['HMDB'].isna())
]
print(f"\nChEBI 조회 대상: {len(new_inchikey_targets)}개")

kegg_found = hmdb_found = 0

for count, (idx, row) in enumerate(new_inchikey_targets.iterrows(), 1):
    chebi_id = get_chebi_id(row['InChIKey'])
    if not chebi_id:
        print(f"[{count}] {row['compound_name'][:30]} → ChEBI 미발견")
        time.sleep(0.3)
        continue

    ids = get_kegg_hmdb(chebi_id)
    if ids['kegg'] and pd.isna(row['KEGG']):
        df.at[idx, 'KEGG'] = ids['kegg']
        kegg_found += 1
    if ids['hmdb'] and pd.isna(row['HMDB']):
        df.at[idx, 'HMDB'] = ids['hmdb']
        hmdb_found += 1

    print(f"[{count}] {row['compound_name'][:30]} → KEGG: {ids['kegg']} | HMDB: {ids['hmdb']}")
    time.sleep(0.3)

print(f"\n새로 확보 - KEGG: {kegg_found}개 / HMDB: {hmdb_found}개")
print(f"KEGG 총합: {df['KEGG'].notna().sum()} / 902")
print(f"HMDB 총합: {df['HMDB'].notna().sum()} / 902")

df.to_excel(OUTPUT_FILE, index=False)
apply_format(OUTPUT_FILE)
print(f"저장 완료: {OUTPUT_FILE}")

# ────────────────────────────────────────────────────────
# 2. 23_fill_inchikey_from_pubchem.py
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd
# import time
# from format_excel import apply_format

# INPUT_FILE  = "metabolites_step22.xlsx"
# OUTPUT_FILE = "metabolites_step23.xlsx"

# df = pd.read_excel(INPUT_FILE)
# targets = df[df['InChIKey'].isna() & df['PubChem'].notna()]
# print(f"대상: {len(targets)}개")

# BATCH_SIZE = 100
# cids = [int(x) for x in targets['PubChem'].tolist()]
# batches = [cids[i:i+BATCH_SIZE] for i in range(0, len(cids), BATCH_SIZE)]

# inchikey_map = {}  # {CID: InChIKey}

# for i, batch in enumerate(batches):
#     cids_str = ",".join(map(str, batch))
#     try:
#         resp = requests.get(
#             f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids_str}/property/InChIKey/JSON",
#             timeout=30
#         )
#         if resp.status_code == 200:
#             for prop in resp.json()['PropertyTable']['Properties']:
#                 inchikey_map[prop['CID']] = prop['InChIKey']
#         print(f"배치 [{i+1}/{len(batches)}] 완료 → 누적: {len(inchikey_map)}개")
#     except Exception as e:
#         print(f"배치 [{i+1}] 오류: {e}")
#     time.sleep(0.5)

# # 업데이트
# for idx, row in targets.iterrows():
#     cid = int(row['PubChem'])
#     if cid in inchikey_map:
#         df.at[idx, 'InChIKey'] = inchikey_map[cid]
#         print(f"✅ {row['compound_name']} → {inchikey_map[cid]}")

# filled = df['InChIKey'].notna().sum()
# print(f"\nInChIKey 채워진 행: {filled} / {len(df)}")

# df.to_excel(OUTPUT_FILE, index=False)
# apply_format(OUTPUT_FILE)
# print(f"저장 완료: {OUTPUT_FILE}")
### 40개에 대한 InChIKey 업데이트 완료 ###

# ────────────────────────────────────────────────────────
# 1. Test PubChem CID → InChIKey
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd

# df = pd.read_excel("metabolites_step22.xlsx")

# # InChIKey 없고 PubChem 있는 행
# targets = df[df['InChIKey'].isna() & df['PubChem'].notna()]
# print(f"대상: {len(targets)}개")

# # 첫 번째 행 테스트
# row = targets.iloc[0]
# cid = int(row['PubChem'])
# print(f"테스트: {row['compound_name']} (CID: {cid})")

# resp = requests.get(
#     f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/InChIKey/JSON"
# )
# print(resp.status_code)
# print(resp.json())