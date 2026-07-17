"""Stage 4.5: MSI (Metabolomics Standards Initiative) confidence level auto-assignment.

Non-targeted data: no authentic-standard confirmation is available, so true MSI
Level 1 is NOT assigned (per project study note). Levels are assigned from
independent database cross-evidence:

  L2  probable structure : has InChIKey AND >=2 independent DB IDs cross-confirm
                           (from HMDB / KEGG / ChEBI / MMMDB). MMMDB full-InChIKey
                           match counts as species-specific confirmation.
  L3  tentative          : has InChIKey but <=1 independent DB ID
  L4  molecular formula  : no structural identifier (no InChIKey), name/mass only
  L5  unknown            : no InChIKey and no DB IDs at all

msi_evidence records the supporting keys, e.g. 'InChIKey; HMDB; ChEBI; MMMDB(11 tissues, InChIKey)'.
"""
import pandas as pd

m=pd.read_parquet("mouse_reclassified.parquet")

def has_id(v):
    return pd.notna(v) and str(v).strip().lower() not in ("","nan","none")

def assess(r):
    ev=[]
    ik = has_id(r.get("InChIKey"))
    if ik: ev.append("InChIKey")
    db=0
    for c in ["HMDB","KEGG","ChEBI"]:
        if has_id(r.get(c)):
            ev.append(c); db+=1
    mm = r.get("mmmdb_match")=="Yes"
    if mm:
        db+=1
        ev.append(f"MMMDB({int(r['mmmdb_n_tissues'])} tissues, {r['mmmdb_match_basis']})")
    # level logic
    if ik and db>=2:
        lvl="L2"
    elif ik:
        lvl="L3"
    elif db>=1:
        lvl="L4"   # DB name link but no resolved structure
    else:
        lvl="L5"
    return lvl, "; ".join(ev) if ev else "no evidence"

out=m.apply(assess, axis=1, result_type="expand")
m["msi_level"]=out[0]
m["msi_evidence"]=out[1]

print("=== MSI level distribution ===")
print(m["msi_level"].value_counts().sort_index().to_string())
print("\nMSI level x classification:")
print(pd.crosstab(m["msi_level"], m["classification"]).to_string())
print("\nMSI level for MMMDB-matched compounds:")
print(m[m.mmmdb_match=="Yes"]["msi_level"].value_counts().sort_index().to_string())

m.to_parquet("mouse_msi.parquet")
print("\nsaved mouse_msi.parquet")
