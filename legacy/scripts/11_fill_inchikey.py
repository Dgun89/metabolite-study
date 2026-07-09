# 11_fill_inchikey.py
# Target: rows with PubChem CID but missing InChIKey in metabolites_step10_ver4.xlsx

import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

# ─────────────────────────────
# 1. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel("metabolites_step10_ver4.xlsx")

target = df[df['InChIKey'].isna() & df['PubChem'].notna()]
total = len(target)
print(f"Target: {total} rows")

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

# ─────────────────────────────
# 4. 루프 실행
# ─────────────────────────────
for i, idx in enumerate(target.index, start=1):
    cnp_id = df.at[idx, 'Database ID']
    print(f"\n[{i}/{total}] Processing {cnp_id}...")

    inchikey = get_inchikey(cnp_id)
    if inchikey is None:
        print(f"  → InChIKey not found, skipping")
        continue

    df.at[idx, 'InChIKey'] = inchikey
    print(f"  → InChIKey: {inchikey}")

# ─────────────────────────────
# 5. 엑셀 저장
# ─────────────────────────────
df.to_excel("metabolites_step11.xlsx", index=False)
print("\nDone. Saved.")