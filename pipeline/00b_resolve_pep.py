"""
0b단계: PEP(펩타이드) id의 구조 복원 — 세 종 모두.

원본 시드에는 CNP(COCONUT)가 아니라 PEP(펩타이드 DB) id가 섞여 있다
(human 1, mouse 10, legacy 49). COCONUT 조인으로는 InChIKey/SMILES를 얻을 수 없고
원본에도 구조 정보가 없으므로, 화합물명(예: "Asparaginyl-Valine",
"Val-Asp-Ala-Lys")으로부터 구조를 복원한다.

전략(2단계):
  1) PubChem 이름 검색 (dipeptide 계열은 명명형이 등록돼 있음)
  2) 실패 시 RDKit MolFromSequence — 3-letter 서열을 L-펩타이드로 빌드
     (tetrapeptide 등 PubChem 미등록 케이스)

입력: data/{species}/raw/{species}_seed.csv 의 id_type==PEP 행
출력: data/{species}/raw/{species}_pep_resolved.csv
  컬럼: cnp_id, compound_name, inchikey, smiles, formula, resolved,
        source, source_version, retrieved_at

사용:
    python pipeline/00b_resolve_pep.py           # 세 종 전부
    python pipeline/00b_resolve_pep.py legacy    # 한 종만
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

THREE_TO_ONE = {
    'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q',
    'Glu': 'E', 'Gly': 'G', 'His': 'H', 'Ile': 'I', 'Leu': 'L', 'Lys': 'K',
    'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W',
    'Tyr': 'Y', 'Val': 'V',
}
PUBCHEM_PROP = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}"
    "/property/InChIKey,CanonicalSMILES,MolecularFormula/JSON"
)


def pubchem_name(name: str) -> dict | None:
    url = PUBCHEM_PROP.format(name=requests.utils.quote(name))
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()["PropertyTable"]["Properties"][0]
    except Exception:
        pass
    return None


def rdkit_sequence(name: str) -> dict | None:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    try:
        one = "".join(THREE_TO_ONE[p] for p in name.split("-"))
    except KeyError:
        return None
    m = Chem.MolFromSequence(one)   # linear L-peptide, free termini
    if m is None:
        return None
    return {
        "InChIKey": Chem.MolToInchiKey(m),
        "CanonicalSMILES": Chem.MolToSmiles(m),
        "MolecularFormula": rdMolDescriptors.CalcMolFormula(m),
        "_rdkit": Chem.rdBase.rdkitVersion,
    }


def resolve_pep(species: str) -> pd.DataFrame:
    seed = pd.read_csv(C.RAW_SEEDS[species])
    pep = seed[seed["id_type"] == "PEP"][["cnp_id", "compound_name"]].reset_index(drop=True)
    dest = C.BASE / "data" / species / "raw" / f"{species}_pep_resolved.csv"
    if len(pep) == 0:
        # 빈 테이블도 저장(다운스트림이 존재를 가정)
        cols = ["cnp_id", "compound_name", "inchikey", "smiles", "formula",
                "resolved", "source", "source_version", "retrieved_at"]
        pd.DataFrame(columns=cols).to_csv(dest, index=False)
        print(f"{species}: PEP 0개 → 빈 {dest.relative_to(C.BASE)}")
        return pd.DataFrame(columns=cols)

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for _, r in pep.iterrows():
        pid, nm = r["cnp_id"], str(r["compound_name"]).strip()
        p = pubchem_name(nm)
        if p and "InChIKey" in p:
            src, ver = "PubChem", "PubChem-name-search"
        else:
            p = rdkit_sequence(nm)
            src = "RDKit" if p else None
            ver = ("RDKit-MolFromSequence-" + p["_rdkit"]) if p else None
        rows.append({
            "cnp_id": pid, "compound_name": nm,
            "inchikey": p.get("InChIKey") if p else None,
            "smiles": p.get("CanonicalSMILES") if p else None,
            "formula": p.get("MolecularFormula") if p else None,
            "resolved": bool(p),
            "source": src, "source_version": ver, "retrieved_at": now,
        })
        time.sleep(0.22)

    out = pd.DataFrame(rows)
    out.to_csv(dest, index=False)
    print(f"{species}: PEP resolved {out.resolved.sum()}/{len(out)} "
          f"(PubChem {(out.source == 'PubChem').sum()}, RDKit {(out.source == 'RDKit').sum()}) "
          f"→ {dest.relative_to(C.BASE)}")
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or list(C.SPECIES)
    for sp in targets:
        resolve_pep(sp)
