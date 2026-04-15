# 13_fill_hmdb_unichem.py
# Target: rows with InChIKey but missing HMDB in metabolites_step11.xlsx

import requests
import pandas as pd
import time

# ─────────────────────────────
# 1. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel("metabolites_step11.xlsx")

target = df[df['InChIKey'].notna() & df['HMDB'].isna()]
total = len(target)
print(f"Target: {total} rows")

# ─────────────────────────────
# 2. 함수 정의
# ─────────────────────────────
def get_hmdb_from_unichem(inchikey):
    url = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
    body = {"compound": inchikey, "type": "inchikey"}
    res = requests.post(url, json=body)
    if res.status_code == 200 and res.json()['compounds']:
        sources = res.json()['compounds'][0]['sources']
        for source in sources:
            if source['shortName'] == 'hmdb':
                return source['compoundId']
    return None

# ─────────────────────────────
# 3. 루프 실행
# ─────────────────────────────
for count, idx in enumerate(target.index, start=1):
    inchikey = df.at[idx, 'InChIKey']
    print(f"[{count}/{total}] {df.at[idx, 'QualitativeResults']} → ", end="")

    hmdb = get_hmdb_from_unichem(inchikey)
    if hmdb is None:
        print("HMDB not found, skipping")
        continue

    df.at[idx, 'HMDB'] = hmdb
    print(f"HMDB: {hmdb}")
    time.sleep(0.5)

# ─────────────────────────────
# 4. 저장
# ─────────────────────────────
df.to_excel("metabolites_step13.xlsx", index=False)
print("Saved successfully!")