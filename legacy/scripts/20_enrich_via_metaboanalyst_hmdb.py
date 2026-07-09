# ────────────────────────────────────────────────────────
# 1. Test PubChem → KEGG extraction
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd

# df = pd.read_excel("metabolites_step19.xlsx")

# # KEGG 없고 PubChem 있는 첫 번째 행
# target = df[df['KEGG'].isna() & df['PubChem'].notna()].iloc[0]
# cid = int(target['PubChem'])
# print(f"테스트 화합물: {target['QualitativeResults']} (CID: {cid})")

# resp = requests.get(
#     f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON",
#     params={"heading": "KEGG"}
# )
# print(resp.status_code)
# import json
# print(json.dumps(resp.json(), indent=2)[:1000])

# ────────────────────────────────────────────────────────
# 2. Test PubChem xrefs → KEGG
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd

# df = pd.read_excel("metabolites_step19.xlsx")

# target = df[df['KEGG'].isna() & df['PubChem'].notna()].iloc[0]
# cid = int(target['PubChem'])
# print(f"테스트 화합물: {target['QualitativeResults']} (CID: {cid})")

# resp = requests.get(
#     f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/xrefs/RegistryID/JSON"
# )
# print(resp.status_code)
# import json
# print(json.dumps(resp.json(), indent=2)[:1000])

# ────────────────────────────────────────────────────────
# 3. 검증: KEGG ID 있는 화합물로 테스트 (Kynurenic acid, CID 3845)
# ────────────────────────────────────────────────────────
# import requests
# import re

# resp = requests.get(
#     "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/3845/xrefs/RegistryID/JSON"
# )
# ids = resp.json()['InformationList']['Information'][0]['RegistryID']

# # KEGG ID 패턴: C##### 또는 D#####
# kegg_ids = [x for x in ids if re.match(r'^[CD]\d{5}$', x)]
# print(f"전체 RegistryID: {len(ids)}개")
# print(f"KEGG ID 해당: {kegg_ids}")

# ────────────────────────────────────────────────────────
# 4. 샘플 테스트 (앞 10개)
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd
# import re
# import time

# df = pd.read_excel("metabolites_step19.xlsx")
# targets = df[df['KEGG'].isna() & df['PubChem'].notna()].head(10)

# for _, row in targets.iterrows():
#     cid = int(row['PubChem'])
#     resp = requests.get(
#         f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/xrefs/RegistryID/JSON"
#     )
#     if resp.status_code == 200:
#         ids = resp.json()['InformationList']['Information'][0]['RegistryID']
#         kegg_ids = [x for x in ids if re.match(r'^[CD]\d{5}$', x)]
#         print(f"{row['QualitativeResults'][:40]} → {kegg_ids if kegg_ids else '없음'}")
#     time.sleep(0.2)

# ────────────────────────────────────────────────────────
# 5. 20_fill_kegg_from_pubchem.py
# ────────────────────────────────────────────────────────
# import requests
# import pandas as pd
# import re
# import time

# INPUT_FILE  = "metabolites_step19.xlsx"
# OUTPUT_FILE = "metabolites_step20.xlsx"

# df = pd.read_excel(INPUT_FILE)
# targets = df[df['KEGG'].isna() & df['PubChem'].notna()]
# print(f"대상: {len(targets)}개")

# found = 0
# for idx, row in targets.iterrows():
#     cid = int(row['PubChem'])
#     try:
#         resp = requests.get(
#             f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/xrefs/RegistryID/JSON",
#             timeout=30
#         )
#         if resp.status_code == 200:
#             ids = resp.json()['InformationList']['Information'][0]['RegistryID']
#             kegg_ids = [x for x in ids if re.match(r'^C\d{5}$', x)]
#             if kegg_ids:
#                 df.at[idx, 'KEGG'] = kegg_ids[0]
#                 found += 1
#                 print(f"✅ {row['QualitativeResults'][:40]} → {kegg_ids[0]}")
#     except Exception as e:
#         print(f"  [error] {e}")
#     time.sleep(0.5)

# print(f"\n새로 확보된 KEGG ID: {found}개")
# df.to_excel(OUTPUT_FILE, index=False)
# print(f"저장 완료: {OUTPUT_FILE}")

# ────────────────────────────────────────────────────────
# 6. 19-1 >> 20을 통해 신규 KEGG 7개 확보 
# ────────────────────────────────────────────────────────
# import pandas as pd

# df = pd.read_excel("metabolites_step19-1.xlsx")

# # 아까 확보한 7개 KEGG ID
# new_kegg = {
#     "6-Isopropoxynicotinic acid": "C13680",
#     "4-acetylbenzo[d]oxazol-2(3H)-one": "C11210",
#     "2-Aminoheptanoic acid": "C71385",
#     "Aspartyl-Tyrosine": "C21033",
#     "Leu-Leu": "C10317",
#     "Emmolic acid": "C35140",
#     "3-Methylindene": "C76459",
# }

# for name, kegg_id in new_kegg.items():
#     mask = df['QualitativeResults'] == name
#     if mask.any():
#         df.loc[mask, 'KEGG'] = kegg_id
#         print(f"✅ {name} → {kegg_id}")

# df.to_excel("metabolites_step20.xlsx", index=False)
# print("저장 완료: metabolites_step20.xlsx")

# ────────────────────────────────────────────────────────
# 7. 기존의 HMDB ID 214개로 Pathway 분석하여 커버리지 향상
# ────────────────────────────────────────────────────────
# import pandas as pd

# df = pd.read_excel("metabolites_step20.xlsx")

# target = df[
#     (df['filter_status'] == 'endogenous') &
#     (df['HMDB'].notna())
# ]
# print(f"대상: {len(target)}개")

# target['HMDB'].to_csv("hmdb_ids_for_metaboanalyst.txt", index=False, header=False)
# print("저장 완료")

# ────────────────────────────────────────────────────────
# 8. HMDB로 KEGG, PubChem, smiles 모두 확보하여 기존 데이터와 비교 >> 2개 확보
# ────────────────────────────────────────────────────────
# import pandas as pd

# name_map = pd.read_csv('extraction_HMDB.csv')
# df = pd.read_excel("metabolites_step20.xlsx")

# # KEGG가 새로 생긴 것 확인
# print("=== MetaboAnalyst에서 KEGG ID 있는 것 ===")
# has_kegg = name_map[name_map['KEGG'].notna()]
# print(f"{len(has_kegg)}개")

# # 우리 DB에 KEGG 없는데 MetaboAnalyst엔 있는 것
# merged = df.merge(name_map[['HMDB','KEGG']], on='HMDB', suffixes=('_ours','_meta'))
# new_kegg = merged[merged['KEGG_ours'].isna() & merged['KEGG_meta'].notna()]
# print(f"\n=== 새로 채울 수 있는 KEGG ID: {len(new_kegg)}개 ===")
# print(new_kegg[['QualitativeResults','HMDB','KEGG_meta']].to_string())

# ────────────────────────────────────────────────────────
# 9. 
# ────────────────────────────────────────────────────────
import pandas as pd

df = pd.read_excel("metabolites_step20.xlsx")
name_map = pd.read_csv("extraction_HMDB.csv")

# SMILES 컬럼 추가
df['SMILES'] = ""

for _, row in name_map.iterrows():
    if pd.notna(row['SMILES']) and pd.notna(row['HMDB']):
        mask = df['HMDB'] == row['HMDB']
        if mask.any():
            df.loc[mask, 'SMILES'] = row['SMILES']

filled = df['SMILES'].apply(lambda x: x != "").sum()
print(f"SMILES 채워진 행: {filled} / {len(df)}")

df.to_excel("metabolites_step20.xlsx", index=False)
print("저장 완료")