import pandas as pd, re, json

SUFFIX_SWAPS=[("butyrate","butanoate"),("propionate","propanoate"),
              ("valerate","pentanoate"),("caproate","hexanoate"),
              ("isobutyrate","2-methylpropanoate"),
              ("diphosphate","bisphosphate"),
              ("heptanoate","enanthate"),("laurate","dodecanoate"),
              ("pelargonate","nonanoate"),("undecanoate","hendecanoate"),
              ("sebacate","decanedioate"),("azelate","nonanedioate"),
              ("mucate","galactarate")]

AA3={"ala":"alanine","arg":"arginine","asn":"asparagine","asp":"aspartate",
     "cys":"cysteine","gln":"glutamine","gin":"glutamine","glu":"glutamate",
     "gly":"glycine","his":"histidine","ile":"isoleucine","leu":"leucine",
     "lys":"lysine","met":"methionine","phe":"phenylalanine","pro":"proline",
     "ser":"serine","thr":"threonine","trp":"tryptophan","tyr":"tyrosine",
     "val":"valine"}

def norm(s):
    s=str(s).strip()
    s=re.sub(r'\s+(divalent|monovalent|trivalent|cation|anion)$','',s,flags=re.I)
    s=s.strip().lower()
    s=re.sub(r'[\s\-_]+',' ',s)
    s=re.sub(r'[;,]$','',s)
    return s.strip()

def variants(nm):
    """generate normalized name variants for fuzzy KEGG lookup"""
    base=norm(nm)
    out={base}
    # suffix swaps both directions
    for a,b in SUFFIX_SWAPS:
        if a in base: out.add(base.replace(a,b))
        if b in base: out.add(base.replace(b,a))
    # strip leading stereo/locant prefixes like "l-", "d-", "(s)-"
    out.add(re.sub(r'^(l |d |dl |\(s\) |\(r\) )','',base))
    # amino-acid 3-letter abbreviations -> full name (whole token only)
    if base in AA3: out.add(AA3[base])
    # apply suffix swaps to all current variants (one more pass)
    more=set()
    for v in out:
        for a,b in SUFFIX_SWAPS:
            if a in v: more.add(v.replace(a,b))
            if b in v: more.add(v.replace(b,a))
    out|=more
    return {v.strip() for v in out if v.strip()}

def split_compound_item(name):
    """MMMDB packs ambiguous IDs as 'A and(or) ; B' — return candidate names"""
    parts=re.split(r'\s*and\(or\)\s*;?\s*|\s*;\s*', str(name))
    return [p.strip() for p in parts if p.strip()]

# KEGG name index. Prefer L-form / standard: index the RAW (with L-/D- prefix)
# name first, and only add the stripped form if not already claimed by an L- entry.
kegg_idx={}          # normalized-with-prefix -> cid
kegg_idx_bare={}     # stereo-stripped -> cid, L-form preferred
def base_norm(s):
    s=norm(s)
    return re.sub(r'^(l |d |dl |\(s\) |\(r\) )','',s).strip()
for line in open("kegg_compound_list.tsv"):
    p=line.rstrip("\n").split("\t")
    if len(p)<2: continue
    cid=p[0].replace("cpd:","")
    for syn in p[1].split(";"):
        raw=norm(syn)
        if raw and raw not in kegg_idx: kegg_idx[raw]=cid
        b=base_norm(syn)
        is_L=raw.startswith("l ")
        if b:
            if b not in kegg_idx_bare:
                kegg_idx_bare[b]=cid
            elif is_L:
                kegg_idx_bare[b]=cid   # L-form overrides earlier non-L
# merge bare index under keys not already present
for b,cid in kegg_idx_bare.items():
    kegg_idx.setdefault(b, cid)

agg=pd.read_parquet("mmmdb_agg.parquet")
def resolve(display):
    for cand in split_compound_item(display):
        for v in variants(cand):
            # prefer L-form / standard via bare index, then raw index
            if v in kegg_idx_bare: return kegg_idx_bare[v], cand
            if v in kegg_idx:      return kegg_idx[v], cand
    return None, None

kegg_ids=[]; matched_on=[]
for _,r in agg.iterrows():
    cid,on=resolve(r["name_display"])
    kegg_ids.append(cid); matched_on.append(on)
agg["kegg_id"]=kegg_ids
n=agg["kegg_id"].notna().sum()
print(f"MMMDB->KEGG (with variants+split): {n}/{len(agg)} ({100*n//len(agg)}%)")
still=agg[agg["kegg_id"].isna()]["name_display"].tolist()
print("still unmatched:", len(still))
for s in still: print("   ", s)
agg.to_parquet("mmmdb_agg.parquet")
