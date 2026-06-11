# 15_fill_kegg_hmdb_mw.py
# Target: rows with InChIKey but missing KEGG or HMDB in metabolites_step14.xlsx

import requests
import pandas as pd
import time

df = pd.read_excel("metabolites_step14.xlsx")
target = df[df['InChIKey'].notna() & (df['KEGG'].isna() | df['HMDB'].isna())]
total = len(target)
print(f"Target: {total} rows")

def get_kegg_hmdb_mw(inchikey):
    url = f"https://www.metabolomicsworkbench.org/rest/compound/inchi_key/{inchikey}/all"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get('kegg_id'), data.get('hmdb_id')
    except:
        pass
    return None, None

for count, idx in enumerate(target.index, start=1):
    inchikey = df.at[idx, 'InChIKey']
    print(f"[{count}/{total}] {df.at[idx, 'QualitativeResults']} → ", end="")
    kegg, hmdb = get_kegg_hmdb_mw(inchikey)
    if kegg and pd.isna(df.at[idx, 'KEGG']):
        df.at[idx, 'KEGG'] = kegg
    if hmdb and pd.isna(df.at[idx, 'HMDB']):
        df.at[idx, 'HMDB'] = hmdb
    print(f"KEGG: {kegg} HMDB: {hmdb}")
    time.sleep(0.3)

df.to_excel("metabolites_step15.xlsx", index=False)
print("Saved!")