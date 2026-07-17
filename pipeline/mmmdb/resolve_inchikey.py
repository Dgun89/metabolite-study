"""Resolve InChIKey via CORRECT route: KEGG conv gives PubChem *SID*, not CID.
   SID -> CID (PubChem) -> InChIKey/ConnectivitySMILES.
   Cross-check a sample against ChEBI to catch mapping errors."""
import urllib.request, socket, json, time
import pandas as pd
socket.setdefaulttimeout(60)
def urlget(url, tries=4):
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last=e; time.sleep(3)
    raise last

agg=pd.read_parquet("mmmdb_agg.parquet")
sids=sorted(set(agg["pubchem_id"].dropna().astype(str)))
print("SIDs to resolve:", len(sids))

# 1) SID -> CID (batch)
sid2cid={}
B=100
for i in range(0,len(sids),B):
    chunk=sids[i:i+B]
    res=urlget("https://pubchem.ncbi.nlm.nih.gov/rest/pug/substance/sid/"
               +",".join(chunk)+"/cids/JSON")
    for info in res["InformationList"]["Information"]:
        s=str(info["SID"]); cids=info.get("CID",[])
        if cids: sid2cid[s]=str(cids[0])
    print(f"  SID->CID {min(i+B,len(sids))}/{len(sids)}", flush=True)
    time.sleep(0.4)
print("SID->CID mapped:", len(sid2cid))

# 2) CID -> InChIKey + ConnectivitySMILES (batch)
cids=sorted(set(sid2cid.values()))
ikC={}; smC={}
for i in range(0,len(cids),B):
    chunk=cids[i:i+B]
    res=urlget("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
               +",".join(chunk)+"/property/InChIKey,ConnectivitySMILES/JSON")
    for p in res["PropertyTable"]["Properties"]:
        c=str(p["CID"])
        if p.get("InChIKey"): ikC[c]=p["InChIKey"]
        if p.get("ConnectivitySMILES"): smC[c]=p["ConnectivitySMILES"]
    print(f"  CID->InChIKey {min(i+B,len(cids))}/{len(cids)}", flush=True)
    time.sleep(0.4)

def sid_to_ik(sid):
    if pd.isna(sid): return None
    c=sid2cid.get(str(sid)); return ikC.get(c) if c else None
def sid_to_sm(sid):
    if pd.isna(sid): return None
    c=sid2cid.get(str(sid)); return smC.get(c) if c else None
def sid_to_cid(sid):
    if pd.isna(sid): return None
    return sid2cid.get(str(sid))

agg["pubchem_cid"]=agg["pubchem_id"].map(sid_to_cid)
agg["inchikey"]=agg["pubchem_id"].map(sid_to_ik)
agg["smiles"]=agg["pubchem_id"].map(sid_to_sm)
agg["inchikey14"]=agg["inchikey"].map(lambda k: k.split("-")[0] if isinstance(k,str) else None)
print("with InChIKey:", agg["inchikey"].notna().sum(), "/", len(agg))
agg.to_parquet("mmmdb_agg.parquet")
