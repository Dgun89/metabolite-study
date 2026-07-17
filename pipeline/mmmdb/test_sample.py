import pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_engine as me
ref=pd.read_parquet("mmmdb_reference.parquet")
idx=me.build_indices(ref)
mouse=pd.read_excel("mouse_final.xlsx", sheet_name="Sheet1")
ref_ik14=set(ref["InChIKey14"].dropna())
mouse["ik14"]=mouse["InChIKey"].map(lambda k: str(k).split("-")[0] if pd.notna(k) else None)
likely=mouse[mouse["ik14"].isin(ref_ik14)].head(5)
others=mouse[~mouse["ik14"].isin(ref_ik14)].head(5)
sample=pd.concat([likely,others])
print(f"sample size: {len(sample)} (likely-match {len(likely)} + others {len(others)})\n")
for _,row in sample.iterrows():
    m,t,n,basis,nm=me.match_row(row, idx)
    flag="MATCH" if m else " no  "
    print(f"[{flag}] {str(row['compound_name'])[:33]:33s} | ik={str(row['InChIKey'])[:14]} | "
          f"basis={basis} | mmmdb={nm} | tissues={n}")
