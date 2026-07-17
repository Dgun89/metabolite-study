import pandas as pd, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_engine as me

ref=pd.read_parquet("mmmdb_reference.parquet")
idx=me.build_indices(ref)
xls=pd.ExcelFile("mouse_final.xlsx")
mouse=pd.read_excel(xls, sheet_name="Sheet1")

res=mouse.apply(lambda r: me.match_row(r, idx), axis=1, result_type="expand")
res.columns=["_m","mmmdb_tissues","_nt","mmmdb_match_basis","mmmdb_name"]
mouse["mmmdb_match"]=res["_m"].map({True:"Yes",False:"No"})
mouse["mmmdb_tissues"]=res["mmmdb_tissues"]
mouse["mmmdb_n_tissues"]=res["_nt"]
mouse["mmmdb_match_basis"]=res["mmmdb_match_basis"]
mouse["mmmdb_name"]=res["mmmdb_name"]

n=(mouse["mmmdb_match"]=="Yes").sum()
print(f"MMMDB matched: {n}/{len(mouse)} ({100*n/len(mouse):.1f}%)")
print("\nmatch basis breakdown:")
print(mouse[mouse.mmmdb_match=="Yes"]["mmmdb_match_basis"].value_counts().to_string())
print("\ntissue-count distribution of matches:")
print(mouse[mouse.mmmdb_match=="Yes"]["mmmdb_n_tissues"].value_counts().sort_index().to_string())

# cross-tab: MMMDB match vs current classification
print("\nMMMDB match x classification:")
print(pd.crosstab(mouse["classification"], mouse["mmmdb_match"]).to_string())

mouse.to_parquet("mouse_crossref.parquet")
print("\nsaved mouse_crossref.parquet, cols added: mmmdb_match, mmmdb_tissues, mmmdb_n_tissues, mmmdb_match_basis, mmmdb_name")
