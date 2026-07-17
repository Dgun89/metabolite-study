"""Stage: apply MMMDB species-specific evidence as top-priority rule E0.

E0 (new, highest priority): compound present in MMMDB (detected in real mouse
tissues) -> endogenous, basis 'MMMDB (mouse): detected in N tissue(s)'.
All existing rules (E1/E2/E3/X1/X2/X3/U) retained for non-MMMDB compounds.

Preserves the original 'classification' & 'classification_basis' columns; writes
the MMMDB-aware result into the SAME columns (so final file reflects curation)
but records provenance in:
  classification_original       - pre-MMMDB label
  classification_basis_original - pre-MMMDB basis
  mmmdb_reclassified            - Yes/No (label changed by E0)
"""
import pandas as pd

mouse=pd.read_parquet("mouse_crossref.parquet")

mouse["classification_original"]=mouse["classification"]
mouse["classification_basis_original"]=mouse["classification_basis"]

new_class=[]; new_basis=[]; changed=[]
for _,r in mouse.iterrows():
    if r["mmmdb_match"]=="Yes":
        nt=int(r["mmmdb_n_tissues"])
        cls="endogenous"
        basis=f"MMMDB (mouse): detected in {nt} tissue(s) [{r['mmmdb_match_basis']}]"
        new_class.append(cls); new_basis.append(basis)
        changed.append("Yes" if r["classification_original"]!=cls else "No")
    else:
        new_class.append(r["classification_original"])
        new_basis.append(r["classification_basis_original"])
        changed.append("No")
mouse["classification"]=new_class
mouse["classification_basis"]=new_basis
mouse["mmmdb_reclassified"]=changed

print("=== classification shift (original -> MMMDB-aware) ===")
print("original:", mouse["classification_original"].value_counts().to_dict())
print("MMMDB   :", mouse["classification"].value_counts().to_dict())
print("\nreclassified by E0 (label changed):", (mouse["mmmdb_reclassified"]=="Yes").sum())
print("\nshift transition table:")
print(pd.crosstab(mouse["classification_original"], mouse["classification"]).to_string())

# list the compounds whose label changed
chg=mouse[mouse["mmmdb_reclassified"]=="Yes"]
print(f"\n{len(chg)} compounds reclassified to endogenous by MMMDB:")
print(chg[["compound_name","classification_original","mmmdb_name","mmmdb_n_tissues"]].to_string())

mouse.to_parquet("mouse_reclassified.parquet")
