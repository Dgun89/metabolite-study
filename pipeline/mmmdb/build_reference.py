import pandas as pd, glob, re, os, json
# ---- 1. aggregate known compounds across tissues ----
known=sorted(glob.glob("mmmdb_raw/*_known.csv"))
recs=[]
for f in known:
    base=os.path.basename(f)                       # e.g. liver_mouse_1_known.csv
    tissue=base.split("_mouse_")[0]
    mouse=base.split("_mouse_")[1][0]              # 1 or 2
    d=pd.read_csv(f)
    d.columns=[c.strip() for c in d.columns]
    conc_col=[c for c in d.columns if c.lower().startswith("conc")][0]
    for _,r in d.iterrows():
        nm=str(r["Annotation Name"]).strip()
        if not nm or nm.lower()=="nan": continue
        recs.append({"name_raw":nm,"tissue":tissue,"mouse":mouse,
                     "mz":r["m/z"],"conc":r[conc_col]})
raw=pd.DataFrame(recs)

def norm_name(s):
    s=str(s).strip()
    # strip charge/state qualifiers MMMDB appends e.g. "Carnosine divalent", "... cation"
    s=re.sub(r'\s+(divalent|monovalent|trivalent|cation|anion)$','',s,flags=re.I)
    s=s.strip().lower()
    s=re.sub(r'[\s\-_]+',' ',s)
    return s
raw["name_norm"]=raw["name_raw"].map(norm_name)

# per-compound aggregation
agg=(raw.groupby("name_norm")
       .agg(name_display=("name_raw", lambda x: x.value_counts().index[0]),
            tissues=("tissue", lambda x: sorted(set(x))),
            n_detections=("tissue","size"),
            mz_median=("mz","median"))
       .reset_index())
agg["n_tissues"]=agg["tissues"].map(len)
agg["tissues_str"]=agg["tissues"].map(lambda t: ";".join(t))
print("unique normalized compounds:", len(agg))
print("tissue count distribution:", agg["n_tissues"].value_counts().sort_index().to_dict())
agg.to_parquet("mmmdb_agg.parquet")
# save name list for identifier resolution
json.dump(sorted(agg["name_display"].tolist()), open("mmmdb_names.json","w"), ensure_ascii=False)
print(agg[["name_display","n_tissues","tissues_str"]].head(12).to_string())
