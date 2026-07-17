import pandas as pd, urllib.request, socket, json, time, re
socket.setdefaulttimeout(30)
agg=pd.read_parquet("mmmdb_agg.parquet")
r=agg[agg["name_display"].str.contains("Lactoylglut",na=False)]
print("S-Lactoylglutathione now:")
print(r[["name_display","kegg_id","chebi_id","pubchem_cid","inchikey"]].to_string())
print("  (correct skeleton for S-lactoylglutathione = RGAOLBZBLOODHZ)\n")

def chebi_ik(chebi):
    url="https://www.ebi.ac.uk/webservices/chebi/2.0/test/getCompleteEntity?chebiId=CHEBI:"+str(chebi)
    try:
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req) as rr:
            txt=rr.read().decode('utf-8','replace')
        m=re.search(r'inchiKey.([A-Z]{14}-[A-Z]{10}-[A-Z])', txt)
        return m.group(1) if m else None
    except Exception as e:
        return "ERR"+repr(e)[:40]

sub=agg[agg["chebi_id"].notna() & agg["inchikey"].notna()].sample(8, random_state=1)
agree=0; tot=0
for _,row in sub.iterrows():
    ck=chebi_ik(row["chebi_id"]); pk=row["inchikey"]
    ok = isinstance(ck,str) and ck.split("-")[0]==pk.split("-")[0]
    agree+=ok; tot+=1
    print(f"  {row['name_display'][:26]:26s} pubchem={pk[:14]} chebi={str(ck)[:14]} {'OK' if ok else 'DIFF'}")
    time.sleep(0.3)
print("\nskeleton agreement:", agree, "/", tot)
