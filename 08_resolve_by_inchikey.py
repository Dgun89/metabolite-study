# step8.py - Resolve unresolved metabolites using PubChem (with URL encoding)
# Reference: 02_fill_cid_to_excel.py (same logic, but with quote() added)
# Target: 288 unresolved rows from metabolites_dropDuplicates.xlsx

# step8.py - Resolve unresolved metabolites via COCONUT API → InChIKey → PubChem CID

import requests
import pandas as pd

from dotenv import load_dotenv
import os

load_dotenv()

# ─────────────────────────────
# 1. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel("metabolites_dropDuplicates.xlsx")

if 'InChIKey' not in df.columns:
    df.insert(1, 'InChIKey', None)  # Database ID 바로 옆에 삽입

df_unresolved = df[df['PubChem'].isna()]
total = len(df_unresolved)
print(f"Unresolved: {total}")

# ─────────────────────────────
# 2. COCONUT 로그인
# ─────────────────────────────
login_url = "https://coconut.naturalproducts.net/api/auth/login"
credentials = {
    "email": os.getenv("COCONUT_EMAIL"),
    "password": os.getenv("COCONUT_PASSWORD")
}

response = requests.post(login_url, json=credentials)
token = response.json()["access_token"]
print("COCONUT login: OK")

# ─────────────────────────────
# 3. 함수 정의
# ─────────────────────────────
def get_inchikey(cnp_id):
    url = "https://coconut.naturalproducts.net/api/molecules/search"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "search": {
            "filters": [
                {"field": "identifier", "operator": "=", "value": cnp_id}
            ]
        }
    }
    res = requests.post(url, json=body, headers=headers)
    if res.status_code == 200 and res.json()['data']:
        return res.json()['data'][0]['standard_inchi_key']
    return None

def get_cid(inchikey):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{inchikey}/cids/JSON"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json()["IdentifierList"]["CID"][0]
    return None

# ─────────────────────────────
# 4. 루프 실행 (테스트: 5개)
# ─────────────────────────────
for i, idx in enumerate(list(df_unresolved.index)[:256], start=1):
    cnp_id = df.at[idx, 'Database ID']
    print(f"\n[{i}/{total}] Processing {cnp_id}...")

    inchikey = get_inchikey(cnp_id)
    if inchikey is None:
        print(f"  → InChIKey not found, skipping")
        continue
    print(f"  → InChIKey: {inchikey}")

    cid = get_cid(inchikey)
    if cid is None:
        print(f"  → CID not found, skipping")
        continue
    print(f"  → CID: {cid}")

    df.at[idx, 'InChIKey'] = inchikey
    df.at[idx, 'PubChem'] = cid

# ─────────────────────────────
# 5. 엑셀 저장
# ─────────────────────────────
df.to_excel("metabolites_step8.xlsx", index=False)
print("\nDone. Saved.")