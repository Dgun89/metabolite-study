import requests
import pandas as pd

# ─────────────────────────────
# 1. UniChem API 테스트
# ─────────────────────────────
# inchikey = "MLKPHKBKTKXXAX-UHFFFAOYSA-N"  # 테스트용 InChIKey

# url = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
# body = {
#     "compound": inchikey,
#     "type": "inchikey"
# }

# res = requests.post(url, json=body)
# print(f"Status: {res.status_code}")
# print(f"Response: {res.json()}")
# ─────────────────────────────
# 2. UniChem API 테스트2
# ─────────────────────────────
# df = pd.read_excel("metabolites_step11.xlsx")

# row = df[df['KEGG'].notna() & df['InChIKey'].notna()].iloc[0]
# print(row['InChIKey'])
# print(row['KEGG'])
# print(row['QualitativeResults'])
# ─────────────────────────────
# 3. InChIKey로 UniChem API 테스트3
# ─────────────────────────────
# inchikey = "HCZHHEIFKROPDY-UHFFFAOYSA-N"  # Kynurenic acid

# url = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
# body = {"compound": inchikey, "type": "inchikey"}

# res = requests.post(url, json=body)
# print(f"Status: {res.status_code}")
# print(f"Response: {res.json()}")

# ─────────────────────────────
# 4. HMDB 추출 방법 확인
# ─────────────────────────────
inchikey = "HCZHHEIFKROPDY-UHFFFAOYSA-N"  # Kynurenic acid

url = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
body = {"compound": inchikey, "type": "inchikey"}
res = requests.post(url, json=body)

sources = res.json()['compounds'][0]['sources']
for source in sources:
    if source['shortName'] == 'hmdb':
        print(source['compoundId'])

def get_hmbd_from_unichem(inchikey):
    url = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
    body = {
        "compound": inchikey, 
        "type": "inchikey"
    }
    res = requests.post(url, json=body)
    if res.status_code == 200 and res.json()['compounds']:
        sources = res.json()['compounds'][0]['sources']
        for source in sources:
            if source['shortName'] == 'hmdb':
                return source['compoundId']
    return None