"""MMMDB cross-reference matching engine.
Match mouse_final rows against mmmdb_reference on identifier keys, priority:
  1. full InChIKey (stereo-exact)   -> basis 'InChIKey'
  2. InChIKey14 (skeleton)          -> basis 'InChIKey14'
  3. KEGG id                        -> basis 'KEGG'
  4. ChEBI id                       -> basis 'ChEBI'
Returns (matched:bool, tissues:str, n_tissues:int, basis:str, mmmdb_name:str)
"""
import pandas as pd, re

def _clean_id(x):
    if pd.isna(x): return None
    s=str(x).strip()
    if s.lower() in ("","nan","none"): return None
    return s

def _chebi_num(x):
    s=_clean_id(x)
    if s is None: return None
    m=re.search(r'(\d+)', s)          # '16176.0' / 'CHEBI:16176' -> '16176'
    return m.group(1) if m else None

def build_indices(ref):
    idx_ik={}; idx_ik14={}; idx_kegg={}; idx_chebi={}
    for _,r in ref.iterrows():
        rec=(r["mmmdb_tissues"], int(r["mmmdb_n_tissues"]), r["mmmdb_name"])
        ik=_clean_id(r.get("InChIKey"))
        if ik: idx_ik.setdefault(ik, rec)
        ik14=_clean_id(r.get("InChIKey14"))
        if ik14: idx_ik14.setdefault(ik14, rec)
        kg=_clean_id(r.get("KEGG"))
        if kg: idx_kegg.setdefault(kg, rec)
        cb=_chebi_num(r.get("ChEBI"))
        if cb: idx_chebi.setdefault(cb, rec)
    return idx_ik, idx_ik14, idx_kegg, idx_chebi

def match_row(row, indices):
    idx_ik, idx_ik14, idx_kegg, idx_chebi = indices
    ik=_clean_id(row.get("InChIKey"))
    if ik and ik in idx_ik:
        t,n,nm=idx_ik[ik]; return True,t,n,"InChIKey",nm
    if ik:
        ik14=ik.split("-")[0]
        if ik14 in idx_ik14:
            t,n,nm=idx_ik14[ik14]; return True,t,n,"InChIKey14",nm
    kg=_clean_id(row.get("KEGG"))
    if kg and kg in idx_kegg:
        t,n,nm=idx_kegg[kg]; return True,t,n,"KEGG",nm
    cb=_chebi_num(row.get("ChEBI"))
    if cb and cb in idx_chebi:
        t,n,nm=idx_chebi[cb]; return True,t,n,"ChEBI",nm
    return False,None,0,None,None
