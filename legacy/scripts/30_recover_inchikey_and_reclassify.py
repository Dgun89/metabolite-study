"""
30_recover_inchikey_and_reclassify.py

step29 -> step30: InChIKey가 비어있던 행을 로컬 COCONUT + RDKit으로 복구하고,
COCONUT organism 정보로 unverified 중 비-인간 유래를 exogenous로 재분류.

- InChIKey 없는 행 36개 중 CNP 27개를 COCONUT canonical_smiles로 조회
- RDKit MolToInchiKey로 InChIKey 계산 (ChEBI/HMDB/PubChem 조회는 0건 -> DB 미등재)
- COCONUT organisms가 있고 non-human이면 exogenous (step30 basis 기록)

결과: metabolites_step30.xlsx (Data/Legend/Summary 3시트)
      InChIKey 866 -> 893, unverified 440 -> 438
"""
import sys
import pandas as pd
from rdkit import Chem
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")

REPO = "/home/dgun89/repos/metabolite-study"
COCONUT = f"{REPO}/data/reference/coconut_complete.csv"
STEP29 = f"{REPO}/legacy/etc/metabolites_step29.xlsx"
OUT = "metabolites_step30.xlsx"

def main():
    s29 = pd.read_excel(STEP29, sheet_name="Sheet1")
    s30 = s29.copy()
    s30["base_id"] = s30["Database ID"].astype(str).str.split(".").str[0]

    # InChIKey 없는 CNP 행의 base id
    need = s30[s30["InChIKey"].isna() & s30["base_id"].str.startswith("CNP")]["base_id"]
    cnp_ids = set(need)

    # COCONUT 스트리밍 조회: SMILES + organisms
    smi_map, org_map = {}, {}
    for chunk in pd.read_csv(COCONUT, chunksize=100000, low_memory=False):
        cols = {c.lower(): c for c in chunk.columns}
        idc, smc, orgc = cols["identifier"], cols["canonical_smiles"], cols["organisms"]
        chunk["base"] = chunk[idc].astype(str).str.split(".").str[0]
        for _, r in chunk[chunk["base"].isin(cnp_ids)].iterrows():
            smi_map[r["base"]] = r[smc]
            org_map[r["base"]] = r[orgc]

    # SMILES -> InChIKey, organism 기반 재분류
    fill = recls = 0
    for i, row in s30.iterrows():
        b = row["base_id"]
        if b in smi_map and pd.isna(row["InChIKey"]):
            smi = smi_map[b]
            if isinstance(smi, str) and smi.strip():
                m = Chem.MolFromSmiles(smi)
                if m:
                    s30.at[i, "InChIKey"] = Chem.MolToInchiKey(m)
                    s30.at[i, "SMILES"] = smi
                    fill += 1
        org = org_map.get(b)
        if (isinstance(org, str) and org.strip() and org.strip().lower() != "nan"
                and str(row["classification"]).strip().lower() == "unverified"
                and "homo sapiens" not in org.lower()):
            s30.at[i, "classification"] = "exogenous"
            s30.at[i, "coconut_organisms"] = org
            s30.at[i, "classification_basis"] = f"COCONUT organism: {org} (step30)"
            recls += 1

    s30 = s30.drop(columns=["base_id"])
    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        s30.to_excel(w, sheet_name="Sheet1", index=False)
    sys.path.insert(0, REPO)
    from format_excel import apply_format
    apply_format(OUT)
    print(f"InChIKey 복구 {fill}, 재분류 {recls} -> {OUT}")

if __name__ == "__main__":
    main()
