import pandas as pd
import requests

##### 1. check the column #####
# df = pd.read_excel("metabolites_step15.xlsx")
# print(df.columns.tolist())
# print(df.head(3))


##### 2. check the api #####
# inchikey = "HCZHHEIFKROPDY-UHFFFAOYSA-N"
# url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
# resp = requests.get(url)
# print(resp.json())

##### 3. test ChEBI roles_classification #####
# chebi_id = "18344"
# url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
# resp = requests.get(url)
# print(resp.json().keys())  # 어떤 필드들이 있는지 먼저 확인

##### 4. test ChEBI roles_classification field #####
# chebi_id = "18344"
# url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
# resp = requests.get(url)
# print(resp.json()['roles_classification'])

##### 5. 16_filter_exogenous.py #####
import time

INPUT_FILE = "metabolites_step15.xlsx"
OUTPUT_FILE = "metabolites_step16.xlsx"

##### 처음 5개만 먼저 돌려보기 #####
# def get_chebi_id(inchikey: str) -> str:
#     url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
#     try:
#         res = requests.get(url, timeout=10)
#         if res.status_code != 200:
#             return ""
#         data = res.json()
#         if not data.get('results'):
#             return ""
#         chebi_id = str(data['results'][0]['_id'])
#         print(f"    found: {chebi_id}")
#         return chebi_id
#     except Exception as e:
#         print(f"    error: {e}")
#         return ""
    
# def get_roles(chebi_id: str) -> list:
#     url=f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
#     try:
#         res = requests.get(url, timeout=10)
#         if res.status_code != 200:
#             return []
#         return [r['name'] for r in res.json().get('roles_classification', [])]
#     except Exception:
#         return []
    
# def classify(inchikey: str) -> str:
#     if pd.isna(inchikey) or inchikey == "":
#         return "unverified"
#     chebi_id = get_chebi_id(inchikey)
#     if not chebi_id:
#         return "unverified"
#     roles = get_roles(chebi_id)
#     if not roles:
#         return "unverified"
#     if "human metabolite" in roles:
#         return "endogenous"
#     return "exogenous"

# df = pd.read_excel(INPUT_FILE)
# print(f"입력 행 수: {len(df)}")

# df_test = df.head(5).copy()
# results = []

# for count, (idx, row) in enumerate(df_test.iterrows(), start=1):
#     inchikey = row['InChIKey']

#     chebi_id = get_chebi_id(inchikey)
#     print(f"  InChIKey: {inchikey}")
#     print(f"  ChEBI ID: {chebi_id}")

#     roles = get_roles(chebi_id) if chebi_id else []
#     print(f"  Roles: {roles}")

#     status = classify(inchikey)
#     results.append(status)
#     print(f"[{count}/5] {row['QualitativeResults']} → {status}\n")
#     time.sleep(0.3)

# df_test['filter_status'] = results
# print(df_test[['QualitativeResults', 'filter_status']])

##### 여기부터는 필수 #####
# def get_chebi_id(inchikey: str) -> str:
#     url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
#     try:
#         res = requests.get(url, timeout=10)
#         if res.status_code != 200:
#             return ""
#         data = res.json()
#         if not data.get('results'):
#             return ""
#         return str(data['results'][0]['_id'])
#     except Exception as e:
#         print(f"  [search error] {e}")
#         return ""

# def get_roles(chebi_id: str) -> list:
#     url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{chebi_id}/"
#     try:
#         res = requests.get(url, timeout=10)
#         if res.status_code != 200:
#             return []
#         return [r['name'] for r in res.json().get('roles_classification', [])]
#     except Exception as e:
#         print(f"  [roles error] {e}")
#         return []

# def classify(inchikey: str) -> str:
#     if pd.isna(inchikey) or inchikey == "":
#         return "unverified"
#     chebi_id = get_chebi_id(inchikey)
#     if not chebi_id:
#         return "unverified"
#     roles = get_roles(chebi_id)
#     if not roles:
#         return "unverified"
#     if "human metabolite" in roles:
#         return "endogenous"
#     return "exogenous"

# # ─────────────────────────────
# # 2. 엑셀 읽기
# # ─────────────────────────────
# df = pd.read_excel(INPUT_FILE)
# print(f"입력 행 수: {len(df)}")

# # ─────────────────────────────
# # 3. 분류 실행
# # ─────────────────────────────
# results = []

# for count, (idx, row) in enumerate(df.iterrows(), start=1):
#     status = classify(row['InChIKey'])
#     results.append(status)
#     print(f"[{count}/{len(df)}] {row['QualitativeResults']} → {status}")
#     time.sleep(0.3)

# # ─────────────────────────────
# # 4. 저장
# # ─────────────────────────────
# df['filter_status'] = results

# print("\n=== 결과 ===")
# print(df['filter_status'].value_counts())

# df_filtered = df[df['filter_status'] != 'exogenous'].copy()
# print(f"\n필터링 후: {len(df_filtered)} / {len(df)}")

# df_filtered.to_excel(OUTPUT_FILE, index=False)
# print(f"저장 완료: {OUTPUT_FILE}")

##### 점검하기 위함 #####
# df = pd.read_excel("metabolites_step16.xlsx")
# print(df.columns.tolist())
# print(df['filter_status'].value_counts())
# print(len(df))

##### 행 합치기 #####
df15 = pd.read_excel("metabolites_step15.xlsx")
df16 = pd.read_excel("metabolites_step16.xlsx")[['Database ID', 'filter_status']]

# step15에 filter_status 병합
df = df15.merge(df16, on='Database ID', how='left')

# 병합 안 된 행(제거됐던 exogenous)은 exogenous로 채우기
df['filter_status'] = df['filter_status'].fillna('exogenous')

print(df['filter_status'].value_counts())
print(len(df))

df.to_excel("metabolites_step16.xlsx", index=False)
print("저장 완료")