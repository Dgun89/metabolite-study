# ────────────────────────────────────────────────────────
# 1. Test InChIKey → SMILES via PubChem
# ────────────────────────────────────────────────────────
# import requests

# inchikey = "HCZHHEIFKROPDY-UHFFFAOYSA-N"  # Kynurenic acid
# resp = requests.get(
#     f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{inchikey}/property/IsomericSMILES/JSON"
# )
# print(resp.status_code)
# print(resp.json())
### 결과 이상 없음 ###

# ────────────────────────────────────────────────────────
# 2. 22_fill_smiles_pubchem.py
# ────────────────────────────────────────────────────────
import requests
import pandas as pd
import time

INPUT_FILE  = "metabolites_step21.xlsx"
OUTPUT_FILE = "metabolites_step22.xlsx"

df = pd.read_excel(INPUT_FILE)

# SMILES 없고 PubChem 있는 행
targets = df[df['SMILES'].isna() & df['PubChem'].notna()]
print(f"대상: {len(targets)}개")

BATCH_SIZE = 100
cids = [int(x) for x in targets['PubChem'].tolist()]
batches = [cids[i:i+BATCH_SIZE] for i in range(0, len(cids), BATCH_SIZE)]

smiles_map = {}  # {CID: SMILES}

for i, batch in enumerate(batches):
    cids_str = ",".join(map(str, batch))
    try:
        resp = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids_str}/property/IsomericSMILES/JSON",
            timeout=30
        )
        if resp.status_code == 200:
            for prop in resp.json()['PropertyTable']['Properties']:
                smiles_map[prop['CID']] = prop.get('IsomericSMILES', prop.get('SMILES', ''))
        print(f"배치 [{i+1}/{len(batches)}] 완료 → 누적: {len(smiles_map)}개")
    except Exception as e:
        print(f"배치 [{i+1}] 오류: {e}")
    time.sleep(0.5)

# 업데이트
for idx, row in targets.iterrows():
    cid = int(row['PubChem'])
    if cid in smiles_map:
        df.at[idx, 'SMILES'] = smiles_map[cid]

filled = df['SMILES'].notna().sum()
print(f"\nSMILES 채워진 행: {filled} / {len(df)}")

df.to_excel(OUTPUT_FILE, index=False)
print(f"저장 완료: {OUTPUT_FILE}")

from format_excel import apply_format
apply_format(OUTPUT_FILE)