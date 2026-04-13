# step8.py - Resolve unresolved metabolites using PubChem (with URL encoding)
# Reference: 02_fill_cid_to_excel.py (same logic, but with quote() added)
# Target: 288 unresolved rows from metabolites_dropDuplicates.xlsx

import requests                 # URL로 데이터 가져오기(API 호출)
from urllib.parse import quote  # 이름의 특수문자/공백을 URL이 읽을 수 있게 변환

import pandas as pd             # 엑셀 읽기/저장

df = pd.read_excel("metabolites_dropDuplicates.xlsx")

df_unresolved = df[df['PubChem'].isna()]

# 중복 제거 후 수치 출력
# print(f"Unresolved: {len(df_unresolved)}")

# print(f"PubChem + KEGG + HMDB: {len(df[df['KEGG'].notna() & df['HMDB'].notna() & df['PubChem'].notna()])}")
# print(f"PubChem + KEGG only: {len(df[df['KEGG'].notna() & df['HMDB'].isna() & df['PubChem'].notna()])}")
# print(f"PubChem + HMDB only: {len(df[df['KEGG'].isna() & df['HMDB'].notna() & df['PubChem'].notna()])}")
# print(f"PubChem only: {len(df[df['KEGG'].isna() & df['HMDB'].isna() & df['PubChem'].notna()])}")
# print(f"Unresolved: {len(df[df['PubChem'].isna()])}")
# print(f"Total: {len(df)}")

def get_cid(name):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(name)}/cids/JSON"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["IdentifierList"]["CID"][0]
    else:
        return None

# test_name = df_unresolved.iloc[0]['QualitativeResults']
# print(f"Testing: {test_name}")
# print(f"CID: {get_cid(test_name)}")

# name = df.iloc[12]['QualitativeResults']  # 엑셀 14번째 행 (0부터 시작이라 13)
# print(repr(name))

test_name = df_unresolved.iloc[0]['QualitativeResults'].lower()
print(f"Testing: {test_name}")
print(f"CID: {get_cid(test_name)}")