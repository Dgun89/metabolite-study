##### 1. Test Reactome search API #####
# import requests
# resp = requests.get(
#     "https://reactome.org/ContentService/data/mapping/ChEBI/15361/reactions"
# )
# print(resp.status_code)
# print(resp.text[:500])

##### 2. Test Reactome reaction detail (catalyst check) #####
# import requests

# resp = requests.get(
#     "https://reactome.org/ContentService/data/query/R-HSA-1614614"
# )
# print(resp.status_code)
# import json
# data = resp.json()
# print(json.dumps(data, indent=2)[:2000])

##### 3. Test Reactome reaction keys #####
# import requests

# resp = requests.get(
#     "https://reactome.org/ContentService/data/query/R-HSA-1614614"
# )
# data = resp.json()
# print(data.keys())

##### 4. Test Reactome catalystActivity field #####
# import requests, json

# resp = requests.get(
#     "https://reactome.org/ContentService/data/query/R-HSA-1614614"
# )
# data = resp.json()
# print(json.dumps(data['catalystActivity'], indent=2))

##### 5. extract_enzymes_reactome #####
import requests
import pandas as pd
import time

INPUT_FILE  = "metabolites_step17.xlsx"
OUTPUT_FILE = "metabolites_step18.xlsx"

# ─────────────────────────────
# 1. 함수 정의
# ─────────────────────────────
def get_chebi_id(inchikey: str) -> str:
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return ""
        data = res.json()
        if not data.get('results'):
            return ""
        return str(data['results'][0]['_id'])
    except Exception as e:
        print(f"  [chebi error] {e}")
        return ""

def get_reactome_catalysts(chebi_id: str) -> str:
    # Step 1: 반응 목록 조회
    url = f"https://reactome.org/ContentService/data/mapping/ChEBI/{chebi_id}/reactions"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200 or not res.json():
            return ""
        reactions = res.json()

        # Step 2: 최대 3개 반응에서 catalyst 추출
        catalysts = []
        for rxn in reactions[:3]:
            stId = rxn['stId']
            try:
                r2 = requests.get(
                    f"https://reactome.org/ContentService/data/query/{stId}",
                    timeout=10
                )
                if r2.status_code == 200:
                    for ca in r2.json().get('catalystActivity', []):
                        name = ca.get('displayName', '')
                        if name and name not in catalysts:
                            catalysts.append(name)
                time.sleep(0.2)
            except Exception:
                continue

        return ";".join(catalysts)
    except Exception as e:
        print(f"  [reactome error] {e}")
        return ""

# ─────────────────────────────
# 2. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel(INPUT_FILE)
print(f"입력 행 수: {len(df)}")

# ─────────────────────────────
# 3. ChEBI ID 조회 + Reactome 효소 추출
# ─────────────────────────────
chebi_ids = []
reactome_catalysts = []

for count, (idx, row) in enumerate(df.iterrows(), start=1):
    inchikey = row['InChIKey']

    if pd.isna(inchikey) or inchikey == "":
        chebi_ids.append("")
        reactome_catalysts.append("")
        print(f"[{count}/{len(df)}] {row['QualitativeResults']} → InChIKey 없음")
        continue

    chebi_id = get_chebi_id(str(inchikey))
    chebi_ids.append(chebi_id)
    time.sleep(0.3)

    if not chebi_id:
        reactome_catalysts.append("")
        print(f"[{count}/{len(df)}] {row['QualitativeResults']} → ChEBI 미발견")
        continue

    catalysts = get_reactome_catalysts(chebi_id)
    reactome_catalysts.append(catalysts)
    cat_count = len(catalysts.split(";")) if catalysts else 0
    print(f"[{count}/{len(df)}] {row['QualitativeResults']} → ChEBI:{chebi_id} | {cat_count}개 catalyst")
    time.sleep(0.3)

# ─────────────────────────────
# 4. 저장
# ─────────────────────────────
df['chebi_id'] = chebi_ids
df['reactome_catalysts'] = reactome_catalysts

has_catalyst = df['reactome_catalysts'].apply(lambda x: x != "")
print(f"\nReactome catalyst 있는 행: {has_catalyst.sum()} / {len(df)}")

df.to_excel(OUTPUT_FILE, index=False)
print(f"저장 완료: {OUTPUT_FILE}")