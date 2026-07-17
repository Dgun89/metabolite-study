"""Reliability comparison: MMMDB-curated mouse table vs legacy DarkMet step30.
Match on full InChIKey; assess classification agreement and MMMDB value-add."""
import pandas as pd

leg=pd.read_excel("/home/dgun89/repos/metabolite-study/legacy/etc/metabolites_step30.xlsx", sheet_name="Sheet1")
cur=pd.read_parquet("mouse_msi.parquet")

leg=leg[leg["InChIKey"].notna()].copy()
cur2=cur[cur["InChIKey"].notna()].copy()
leg["ik"]=leg["InChIKey"].astype(str)
cur2["ik"]=cur2["InChIKey"].astype(str)

merged=cur2.merge(leg[["ik","classification","compound_name"]],
                  on="ik", suffixes=("_cur","_leg"), how="inner")
print(f"legacy step30 rows(InChIKey): {len(leg)} | curated rows(InChIKey): {len(cur2)}")
print(f"common compounds (full InChIKey): {len(merged)}")

# classification agreement (curated MMMDB-aware vs legacy)
agree=(merged["classification_cur"]==merged["classification_leg"]).sum()
print(f"\nclassification agreement: {agree}/{len(merged)} ({100*agree/len(merged):.1f}%)")
print("\nagreement crosstab (rows=curated MMMDB-aware, cols=legacy step30):")
print(pd.crosstab(merged["classification_cur"], merged["classification_leg"]).to_string())

# where MMMDB changed the label vs legacy
diff=merged[merged["classification_cur"]!=merged["classification_leg"]]
print(f"\ndisagreements: {len(diff)}")
# among disagreements, how many are MMMDB reclassified?
mmmdb_driven=diff[diff["mmmdb_reclassified"]=="Yes"]
print(f"  of which MMMDB-driven (E0 reclass): {len(mmmdb_driven)}")
print("\nMMMDB-driven differences vs legacy (curation improvements):")
print(mmmdb_driven[["compound_name_cur","classification_leg","classification_cur",
                    "mmmdb_name","mmmdb_n_tissues"]].to_string())

# MSI level distribution among common compounds
print("\nMSI level of common compounds:")
print(merged["msi_level"].value_counts().sort_index().to_string())

merged.to_parquet("legacy_comparison.parquet")
print("\nsaved legacy_comparison.parquet")
