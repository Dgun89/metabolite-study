# 10_extract_kegg_hmdb2.py
# Target: rows with PubChem CID but missing KEGG or HMDB in metabolites_step8.xlsx

import pandas as pd
import requests
import time

def get_hmdb_kegg(cid):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    try:
        response = requests.get(url, timeout=10)
    except Exception as e:
        print(f"  → Connection error: {e}")
        return {"hmdb": None, "kegg": None}

    if response.status_code != 200:
        return {"hmdb": None, "kegg": None}

    data = response.json()
    result = {"hmdb": None, "kegg": None}

    sections = data["Record"]["Section"]
    for section in sections:
        if section.get("TOCHeading") == "Names and Identifiers":
            for subsection in section.get("Section", []):
                if subsection.get("TOCHeading") == "Other Identifiers":
                    for subsubsection in subsection.get("Section", []):
                        heading = subsubsection.get("TOCHeading")
                        if heading in ["HMDB ID", "KEGG ID"]:
                            for info in subsubsection.get("Information", []):
                                for val in info.get("Value", {}).get("StringWithMarkup", []):
                                    text = val.get("String")
                                    if heading == "HMDB ID":
                                        result["hmdb"] = text
                                    else:
                                        result["kegg"] = text
    return result

# ─────────────────────────────
# 1. 엑셀 읽기
# ─────────────────────────────
df = pd.read_excel("metabolites_step8.xlsx")

# ─────────────────────────────
# 2. 처리 대상 필터
# ─────────────────────────────
target = df[df['PubChem'].notna() & (df['KEGG'].isna() | df['HMDB'].isna())]
total = len(target)
print(f"Target: {total} rows")

# ─────────────────────────────
# 3. 루프 실행
# ─────────────────────────────
for count, idx in enumerate(target.index, start=1):
    cid = df.at[idx, 'PubChem']
    kegg = df.at[idx, 'KEGG']
    hmdb = df.at[idx, 'HMDB']

    ids = get_hmdb_kegg(str(int(float(cid))))

    if ids["kegg"] and pd.isna(kegg):
        df.at[idx, 'KEGG'] = ids["kegg"]
    if ids["hmdb"] and pd.isna(hmdb):
        df.at[idx, 'HMDB'] = ids["hmdb"]

    print(f"[{count}/{total}] {df.at[idx, 'QualitativeResults']} → KEGG: {ids['kegg']} HMDB: {ids['hmdb']}")
    time.sleep(1)

# ─────────────────────────────
# 4. 저장
# ─────────────────────────────
df.to_excel("metabolites_step10_ver4.xlsx", index=False)
print("Saved successfully!")