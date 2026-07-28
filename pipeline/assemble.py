"""
7단계: 종별 최종 파일 조립. format_excel.py의 GROUPS 컬럼 스키마에 맞춰
step4 분류결과 + 효소 캐시(KEGG/Reactome/HMDB gene/BRENDA)를 결합.
출력: {species}_final.xlsx (Data/Legend/Summary 3시트, apply_format 적용).
"""
import sys, json
from pathlib import Path
import pandas as pd

WORK = Path("/home/dgun89/.claude-science/orgs/b775b206-ef44-477d-b8e7-a47020d337a1/workspaces/b721070f-708d-4613-b6ab-5b485695cf35")
sys.path.insert(0, str(WORK))
sys.path.insert(0, "/home/dgun89/repos/metabolite-study")

def join(vals):
    if not vals: return ""
    return "; ".join(str(v) for v in vals if v)

def assemble(species):
    df = pd.read_parquet(WORK/"interim"/species/f"{species}_step4_classified.parquet")
    enz = json.loads((WORK/"interim"/"enzyme_cache.json").read_text(encoding="utf-8"))
    hmdb = json.loads((WORK/"interim"/"hmdb_index.json").read_text(encoding="utf-8"))
    bpath = WORK/"interim"/"brenda_cache.json"
    brenda = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}

    out = pd.DataFrame()
    out["Database ID"]   = df["id"]
    out["compound_name"] = df["annotation"]
    out["InChIKey"]      = df["InChIKey"]
    out["SMILES"]        = df["SMILES"]
    out["PubChem"]       = df["pubchem_cid"]
    out["KEGG"]          = df["kegg_id"]
    out["HMDB"]          = df["hmdb_id"]
    out["ChEBI"]         = df["chebi_id"]
    out["classification"]= df["classification"]
    # 분류 소스
    out["hmdb_origin"]       = df["InChIKey"].map(lambda ik: join(hmdb.get(ik,{}).get("hmdb_source",[])) if pd.notna(ik) else "")
    out["coconut_organisms"] = df["coconut_organisms"].map(lambda x: x if isinstance(x,str) else (join(x) if isinstance(x,(list,tuple)) else ""))
    out["chebi_roles"]       = df["chebi_roles_str"] if "chebi_roles_str" in df else ""
    # 분류 메타
    out["coconut_match_key"]   = df["coconut_matched"].map(lambda m: "cnp_id" if m else "")
    out["classification_basis"]= df["classification_basis"]
    # 효소
    out["kegg_enzymes"]      = df["InChIKey"].map(lambda ik: join(enz.get(ik,{}).get("kegg_ec",[])) if pd.notna(ik) else "")
    out["hmdb_enzymes"]      = df["InChIKey"].map(lambda ik: join(hmdb.get(ik,{}).get("genes",[])) if pd.notna(ik) else "")
    out["reactome_catalysts"]= df["InChIKey"].map(lambda ik: join(enz.get(ik,{}).get("reactome_catalysts",[])) if pd.notna(ik) else "")
    # BRENDA: annotation 이름 기반
    out["brenda_enzymes"]    = df["annotation"].map(lambda n: join(brenda.get(str(n),{}).get("ec_numbers",[])) if pd.notna(n) else "")

    outpath = WORK/"final"/f"{species}_final.xlsx"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(outpath, index=False)
    # 3시트 포맷 적용
    from format_excel import apply_format
    apply_format(str(outpath))
    return out, outpath

if __name__ == "__main__":
    for sp in ["human","mouse"]:
        out, p = assemble(sp)
        print(f"{sp}: {len(out)}행 → {p.name}")
