"""
4단계: 분류 실행 — classify.py 규칙을 각 화합물에 적용.

README가 설명하나 코드로 남아있지 않던 단계의 복원본.
step2(COCONUT 조인) + identifier_cache(ChEBI roles/xref) + hmdb_index(source/genes)를
InChIKey로 결합하고 classify_row_v2()를 적용한다.

입력:
  WORK/interim/{species}/{species}_step2_coconut.parquet
  WORK/interim/identifier_cache.json     (InChIKey -> chebi_roles, xref)
  WORK/interim/hmdb_index.json           (InChIKey -> hmdb_source, genes)
출력:
  WORK/interim/{species}/{species}_step4_classified.parquet

step4 스키마(소문자 표준 + 하위호환 별칭):
  cnp_id, base_id, id_type, compound_name, inchikey, inchikey14, smiles, inchi,
  formula, mol_weight, coconut_id, coconut_organisms, match_type,
  np_classifier_pathway/superclass/class, chemical_class,
  kegg_id, hmdb_id, chebi_id, pubchem_cid, chebi_roles(list), chebi_roles_str,
  hmdb_source(list), classification, classification_basis,
  conflict_flag, conflicting_sources, coconut_matched,
  source, source_version, retrieved_at

사용:
    python pipeline/04_classify_run.py            # 세 종 전부
    python pipeline/04_classify_run.py human      # 한 종만
"""
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C
from pipeline.classify import classify_row_v2


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def classify_species(species: str) -> pd.DataFrame:
    P = C.get_paths(species)
    interim = P["interim"]
    step2 = pd.read_parquet(interim / f"{species}_step2_coconut.parquet")

    id_cache = _load_json(C.WORK / "interim" / "identifier_cache.json")
    hmdb_idx = _load_json(C.WORK / "interim" / "hmdb_index.json")

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for _, r in step2.iterrows():
        ik = r.get("inchikey")
        idc = id_cache.get(ik, {}) if pd.notna(ik) else {}
        hm = hmdb_idx.get(ik, {}) if pd.notna(ik) else {}

        chebi_roles = idc.get("chebi_roles", []) or []
        hmdb_source = hm.get("hmdb_source", []) or []
        organisms = r.get("organisms")

        v = classify_row_v2(chebi_roles, hmdb_source, organisms)

        rec = {
            "cnp_id": r["cnp_id"], "base_id": r.get("base_id"),
            "id_type": r.get("id_type"), "compound_name": r["compound_name"],
            "inchikey": ik,
            "inchikey14": (str(ik)[:14] if pd.notna(ik) else None),
            "smiles": r.get("smiles"), "inchi": r.get("inchi"),
            "formula": r.get("formula"), "mol_weight": r.get("mol_weight"),
            "coconut_id": r.get("coconut_id"),
            "coconut_organisms": organisms,
            "match_type": r.get("match_type"),
            "np_classifier_pathway": r.get("np_classifier_pathway"),
            "np_classifier_superclass": r.get("np_classifier_superclass"),
            "np_classifier_class": r.get("np_classifier_class"),
            "chemical_class": r.get("chemical_class"),
            # identifiers (id_cache 우선, 없으면 hmdb/None)
            "kegg_id": idc.get("kegg_id") or hm.get("kegg_id"),
            "hmdb_id": idc.get("hmdb_id") or hm.get("accession"),
            "chebi_id": idc.get("chebi_id") or hm.get("chebi_id"),
            "pubchem_cid": idc.get("pubchem_cid"),
            "chebi_roles": chebi_roles,
            "chebi_roles_str": "; ".join(chebi_roles),
            "hmdb_source": hmdb_source,
            "classification": v["classification"],
            "classification_basis": v["classification_basis"],
            "conflict_flag": v["conflict_flag"],
            "conflicting_sources": v["conflicting_sources"],
            "coconut_matched": r.get("match_type") in ("full_id", "base_id"),
            # provenance: 분류는 규칙 기반 파생물
            "source": "classify.py:classify_row_v2",
            "source_version": "rules-v2",
            "retrieved_at": now,
        }
        rows.append(rec)

    out = pd.DataFrame(rows)
    # list 컬럼은 parquet 저장을 위해 그대로(pyarrow가 list<str> 지원)
    dest = interim / f"{species}_step4_classified.parquet"
    out.to_parquet(dest, index=False)

    vc = out["classification"].value_counts().to_dict()
    n_conf = int(out["conflict_flag"].sum())
    print(f"[{species}] {len(out)}행 | "
          f"endo {vc.get('endogenous',0)} / exo {vc.get('exogenous',0)} / "
          f"unv {vc.get('unverified',0)} | conflict {n_conf} → {dest.name}")
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or list(C.SPECIES)
    for sp in targets:
        classify_species(sp)
