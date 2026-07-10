"""
8단계: legacy step29 신뢰성 비교 (공통 InChIKey 교집합).

새로 각 DB에서 독립 수집한 종별 최종 파일(final/{species}_final.xlsx)을
legacy 최종 파일(metabolites_step29.xlsx)과 대조하여 legacy 신뢰성 검증.
- 공통 InChIKey(full + skeleton) 교집합 추출
- classification / identifier / enzyme 일치율 계산
결과: final/comparison_report.md + interim/step8_legacy_comparison.png
"""
import re, glob
from pathlib import Path
import pandas as pd

pat = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

def find_legacy():
    for p in ["legacy/etc/metabolites_step29.xlsx", "legacy/data/metabolites_step29.xlsx",
              "legacy/final/metabolites_step29.xlsx"]:
        fp = Path("/home/dgun89/repos/metabolite-study") / p
        if fp.exists():
            return str(fp)
    hits = glob.glob("/home/dgun89/repos/metabolite-study/**/*step29*.xlsx", recursive=True)
    return hits[0] if hits else None

def clean_ik(series):
    return series.map(lambda x: str(x).strip().upper() if pd.notna(x) else "")

def has_val(x):
    return pd.notna(x) and str(x).strip() != "" and str(x).strip().lower() != "nan"

def norm_id(x):
    """float 문자열 '16176.0' -> '16176', 'CHEBI:16176' -> '16176'."""
    if not has_val(x):
        return None
    s = str(x).strip().upper().replace("CHEBI:", "")
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except ValueError:
        pass
    return s

def load_valid(path, sheet=0):
    df = pd.read_excel(path, sheet_name=sheet)
    df["ik"] = clean_ik(df["InChIKey"])
    df = df[df["ik"].map(lambda x: bool(pat.match(x)))].copy()
    return df

def compare(new_df, leg_df, key="ik"):
    if key == "sk":
        new_df = new_df.assign(sk=new_df["ik"].str[:14])
        leg_df = leg_df.assign(sk=leg_df["ik"].str[:14])
    nu = new_df.drop_duplicates(key).set_index(key)
    lu = leg_df.drop_duplicates(key).set_index(key)
    common = sorted(set(nu.index) & set(lu.index))
    n = len(common)
    cls = sum(str(nu.loc[s, "classification"]).strip().lower()
              == str(lu.loc[s, "classification"]).strip().lower() for s in common)
    ids = {}
    for c in ["PubChem", "KEGG", "HMDB", "ChEBI"]:
        both = va = 0
        for s in common:
            nv, lv = norm_id(nu.loc[s, c]), norm_id(lu.loc[s, c])
            if nv and lv:
                both += 1
                va += (nv == lv)
        ids[c] = (both, va)
    enz = {}
    for c in ["kegg_enzymes", "hmdb_enzymes", "reactome_catalysts", "brenda_enzymes"]:
        enz[c] = sum(has_val(nu.loc[s, c]) == has_val(lu.loc[s, c]) for s in common)
    return dict(n=n, cls=cls, ids=ids, enz=enz)

if __name__ == "__main__":
    lp = find_legacy()
    assert lp, "legacy step29 xlsx not found under legacy/{etc,data,final}/"
    leg = load_valid(lp)
    for sp in ["human", "mouse"]:
        new = load_valid(f"final/{sp}_final.xlsx", sheet="Sheet1")
        for key, name in [("ik", "full"), ("sk", "skeleton")]:
            r = compare(new, leg, key)
            print(f"{sp} {name}: n={r['n']} cls={r['cls']}/{r['n']} "
                  f"ids={r['ids']} enz={r['enz']}")
