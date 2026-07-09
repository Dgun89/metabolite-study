import requests
import pandas as pd
import time

##### 1. Test KEGG enzyme API #####
# resp = requests.get("https://rest.kegg.jp/link/enzyme/cpd:C00022")
# print(resp.status_code)
# print(resp.text)

##### 2. Extract enzymes kegg #####
INPUT_FILE = "metabolites_step16.xlsx"
OUTPUT_FILE = "metabolites_step17.xlsx"

def get_kegg_enzyme(kegg_id: str) -> str:
    kegg_id = str(kegg_id).strip().replace("cpd:", "")
    url = f"https://rest.kegg.jp/link/enzyme/cpd:{kegg_id}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200 or not res.text.strip():
            return ""
        enzymes = []
        for line in res.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) == 2:
                enzymes.append(parts[1].strip())
        return ";".join(enzymes)
    except Exception as e:
        print(f"  [error] {kegg_id}: {e}")
        return ""
    
df = pd.read_excel(INPUT_FILE)
print(f"입력 행 수: {len(df)}")

kegg_has = df['KEGG'].notna().sum()
print(f"KEGG ID 보유: {kegg_has}행")

results = []

for count, (idx, row) in enumerate(df.iterrows(), start=1):
    kegg_id = row['KEGG']
    if pd.isna(kegg_id) or kegg_id == "":
        results.append("")
        print(f"[{count}/{len(df)}] {row['QualitativeResults']} -> KEGG ID 없음")
        continue

    enzymes = get_kegg_enzyme(str(kegg_id))
    ec_count = len(enzymes.split(";")) if enzymes else 0
    results.append(enzymes)
    print(f"[{count}/{len(df)}] {row['QualitativeResults']} -> {ec_count}개 효소")
    time.sleep(0.3)

df['kegg_enzymes'] = results
has_enzyme = df['kegg_enzymes'].apply(lambda x: x != "")
print(f"\n효소 정보 있는 행: {has_enzyme.sum()} / {len(df)}")

df.to_excel(OUTPUT_FILE, index=False)
print(f"저장 완료: {OUTPUT_FILE}")