"""
1단계: COCONUT 로컬 조인 — 시드 CNP id → 구조(InChIKey/SMILES/InChI/formula/organisms).

README가 설명하나 코드로 남아있지 않던 단계의 복원본.
data/reference/coconut_complete.csv (738,827행)를 청크 스트리밍으로 읽어
시드의 CNP id에 구조·분류·organism 정보를 붙인다.

조인 정책 (COCONUT identifier에도 버전 접미사가 있음: CNP0145332.1):
  1) full-id 정확 매칭 우선  (seed.cnp_id == coconut.identifier)
  2) 없으면 base_id 매칭 + 최저 버전 선택 (결정론적)
     - 같은 base_id에 InChIKey 스켈레톤이 다른 여러 버전이 있으면
       ambiguous_stereo=True 로 표시(투명성).
  match_type ∈ {full_id, base_id, pep_resolved, unmatched}

PEP 펩타이드(id_type==PEP)는 COCONUT에 없으므로 00b_resolve_pep.py가 만든
{species}_pep_resolved.csv (PubChem/RDKit 구조)로 보강한다.

출력: WORK/interim/{species}/{species}_step2_coconut.parquet
  provenance: source, source_version(COCONUT 스냅샷 날짜), retrieved_at

사용:
    python pipeline/01_coconut_join.py            # 세 종 전부
    python pipeline/01_coconut_join.py human      # 한 종만
"""
import sys
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

CHUNK = 100_000
VER_RE = re.compile(r"\.(\d+)$")

_PUBCHEM = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}"
            "/property/InChIKey,CanonicalSMILES,MolecularFormula/JSON")


def pubchem_by_name(name: str) -> dict | None:
    """COCONUT 미매칭 CNP의 폴백 — 화합물명으로 PubChem 조회."""
    try:
        r = requests.get(_PUBCHEM.format(name=requests.utils.quote(str(name))), timeout=20)
        if r.status_code == 200:
            p = r.json()["PropertyTable"]["Properties"][0]
            if "InChIKey" in p:
                return {"inchikey": p["InChIKey"],
                        "smiles": p.get("CanonicalSMILES") or p.get("ConnectivitySMILES"),
                        "formula": p.get("MolecularFormula")}
    except Exception:
        pass
    return None

# COCONUT에서 가져올 컬럼 → 표준 컬럼명
COCONUT_USE = [
    "identifier", "canonical_smiles", "standard_inchi", "standard_inchi_key",
    "molecular_weight", "molecular_formula", "np_classifier_pathway",
    "np_classifier_superclass", "np_classifier_class", "chemical_class", "organisms",
]
RENAME = {
    "identifier": "coconut_id",
    "canonical_smiles": "smiles",
    "standard_inchi": "inchi",
    "standard_inchi_key": "inchikey",
    "molecular_weight": "mol_weight",
    "molecular_formula": "formula",
}


def strip_version(x: str) -> str:
    return VER_RE.sub("", str(x))


def version_num(x: str) -> int:
    m = VER_RE.search(str(x))
    return int(m.group(1)) if m else -1


def load_coconut_subset(base_ids: set, full_ids: set) -> pd.DataFrame:
    """base_id가 시드에 포함된 COCONUT 행만 청크 스트리밍으로 수집."""
    keep = []
    for chunk in pd.read_csv(C.COCONUT_CSV, usecols=COCONUT_USE, chunksize=CHUNK,
                             dtype=str, low_memory=False):
        chunk = chunk.copy()
        chunk["base_id"] = chunk["identifier"].map(strip_version)
        sel = chunk[chunk["base_id"].isin(base_ids)]
        if len(sel):
            keep.append(sel)
    if not keep:
        return pd.DataFrame(columns=COCONUT_USE + ["base_id"])
    return pd.concat(keep, ignore_index=True)


def join_species(species: str) -> pd.DataFrame:
    seed = pd.read_csv(C.RAW_SEEDS[species])
    cnp = seed[seed["id_type"] == "CNP"].copy()
    base_ids = set(cnp["base_id"])
    full_ids = set(cnp["cnp_id"])

    print(f"[{species}] COCONUT 스트리밍 조인: CNP {len(cnp)} (base {len(base_ids)}) ...")
    coco = load_coconut_subset(base_ids, full_ids)
    coco["ver"] = coco["identifier"].map(version_num)
    # skeleton (InChIKey 첫 14자)로 stereo 모호성 판정
    coco["ik14"] = coco["standard_inchi_key"].astype(str).str[:14]

    rows = []
    now = datetime.now(timezone.utc).isoformat()
    src_ver = C.coconut_version()
    for _, r in cnp.iterrows():
        cand = coco[coco["base_id"] == r["base_id"]]
        match_type = "unmatched"
        pick = None
        if len(cand):
            exact = cand[cand["identifier"] == r["cnp_id"]]
            if len(exact):
                pick = exact.iloc[0]
                match_type = "full_id"
            else:
                # 최저 버전 선택 (결정론적)
                pick = cand.sort_values("ver").iloc[0]
                match_type = "base_id"
        rec = {
            "cnp_id": r["cnp_id"], "base_id": r["base_id"],
            "compound_name": r["compound_name"], "id_type": "CNP",
            "match_type": match_type,
            "ambiguous_stereo": bool(len(cand) and cand["ik14"].nunique() > 1),
            "n_coconut_versions": int(len(cand)),
        }
        if pick is not None:
            for src, dst in RENAME.items():
                rec[dst] = pick[src]
            for col in ["np_classifier_pathway", "np_classifier_superclass",
                        "np_classifier_class", "chemical_class", "organisms"]:
                rec[col] = pick[col]
        rec["source"] = "COCONUT" if pick is not None else None
        rec["source_version"] = src_ver if pick is not None else None
        rec["retrieved_at"] = now
        rows.append(rec)

    out = pd.DataFrame(rows)

    # COCONUT 미매칭 CNP → PubChem 이름검색 폴백
    unmatched = out[out["match_type"] == "unmatched"]
    if len(unmatched):
        for idx, r in unmatched.iterrows():
            p = pubchem_by_name(r["compound_name"])
            if p:
                out.loc[idx, ["inchikey", "smiles", "formula"]] = [
                    p["inchikey"], p["smiles"], p["formula"]]
                out.loc[idx, "match_type"] = "pubchem_name"
                out.loc[idx, ["source", "source_version", "retrieved_at"]] = [
                    "PubChem", "PubChem-name-search", now]
            time.sleep(0.22)

    # PEP 보강
    pep_path = C.BASE / "data" / species / "raw" / f"{species}_pep_resolved.csv"
    if pep_path.exists():
        pep = pd.read_csv(pep_path)
        if len(pep):
            pep_rows = pep.assign(
                base_id=pep["cnp_id"], id_type="PEP", match_type="pep_resolved",
                ambiguous_stereo=False, n_coconut_versions=0,
                inchi=None, mol_weight=None, coconut_id=None,
                np_classifier_pathway=None, np_classifier_superclass=None,
                np_classifier_class=None, chemical_class=None, organisms=None,
            )[[
                "cnp_id", "base_id", "compound_name", "id_type", "match_type",
                "ambiguous_stereo", "n_coconut_versions", "coconut_id", "smiles",
                "inchi", "inchikey", "mol_weight", "formula",
                "np_classifier_pathway", "np_classifier_superclass",
                "np_classifier_class", "chemical_class", "organisms",
                "source", "source_version", "retrieved_at",
            ]]
            out = pd.concat([out, pep_rows], ignore_index=True)

    dest = C.get_paths(species)["interim"] / f"{species}_step2_coconut.parquet"
    out.to_parquet(dest, index=False)

    n_match = (out["match_type"] != "unmatched").sum()
    n_ik = out["inchikey"].notna().sum()
    print(f"[{species}] {len(out)}행 | 매칭 {n_match} "
          f"(full_id {(out.match_type=='full_id').sum()}, "
          f"base_id {(out.match_type=='base_id').sum()}, "
          f"pubchem {(out.match_type=='pubchem_name').sum()}, "
          f"pep {(out.match_type=='pep_resolved').sum()}, "
          f"unmatched {(out.match_type=='unmatched').sum()}) "
          f"| InChIKey 확보 {n_ik} | stereo 모호 {int(out.ambiguous_stereo.sum())}")
    print(f"        → {dest}")
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or list(C.SPECIES)
    for sp in targets:
        join_species(sp)
