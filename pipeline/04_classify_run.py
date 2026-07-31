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

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C
from pipeline.classify import classify_row_v2


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _s2v(row, col: str):
    """step2 행에서 스칼라 값을 안전하게 꺼낸다(없는 컬럼/NaN → None).

    01b_inchikey_join.py 경로 데이터셋은 step2에 데이터셋 자체 제공 식별자를
    담고 있다. 기존 CNP 경로 step2에는 그 컬럼이 없으므로 None이 되어
    기존 동작에 영향을 주지 않는다.
    """
    v = row.get(col)
    if v is None:
        return None
    if isinstance(v, (list, tuple, np.ndarray, pd.Series)):
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none") else None


def classify_species(species: str) -> pd.DataFrame:
    P = C.get_paths(species)
    interim = P["interim"]
    slug = C.dataset_slug(species)   # 파일명 안전화(라벨의 괄호 등 메타문자 제거)
    step2 = pd.read_parquet(interim / f"{slug}_step2_coconut.parquet")

    id_cache = _load_json(C.WORK / "interim" / "identifier_cache.json")
    hmdb_idx = _load_json(C.WORK / "interim" / "hmdb_index.json")

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for _, r in step2.iterrows():
        ik = r.get("inchikey")
        idc = id_cache.get(ik, {}) if pd.notna(ik) else {}
        hm = hmdb_idx.get(ik, {}) if pd.notna(ik) else {}

        chebi_roles = idc.get("chebi_roles", []) or []
        # HMDB 기원 라벨: hmdb_index(InChIKey 기준 로컬 인덱스) 우선.
        # 없으면 step2가 들고 온 값을 쓴다 — 01b_inchikey_join.py 경로로 들어온
        # 데이터셋은 HMDB 레코드를 accession으로 직접 읽어 step2에 담아두므로,
        # hmdb_index에 없는 화합물도 기원 근거를 잃지 않는다.
        hmdb_source = hm.get("hmdb_source", []) or []
        if len(hmdb_source) == 0:
            # parquet의 list<str> 컬럼은 numpy.ndarray로 돌아온다 —
            # pd.notna()가 배열을 반환하므로 스칼라 판정 전에 시퀀스를 먼저 처리.
            _s2 = r.get("hmdb_source")
            if isinstance(_s2, (list, tuple, np.ndarray, pd.Series)):
                hmdb_source = [str(x) for x in _s2 if x is not None and str(x).strip()]
            elif _s2 is not None and pd.notna(_s2) and str(_s2).strip():
                hmdb_source = [str(_s2)]
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
            # 폴백 순서: id_cache(교차수집) → hmdb_index → step2(데이터셋 자체 제공값).
            # 마지막 단계는 01b 경로 데이터셋용. 기존 CNP 경로 step2에는 해당
            # 컬럼이 없어 .get()이 None을 돌려주므로 동작이 바뀌지 않는다.
            "kegg_id": idc.get("kegg_id") or hm.get("kegg_id") or _s2v(r, "kegg_id"),
            "hmdb_id": idc.get("hmdb_id") or hm.get("accession") or _s2v(r, "hmdb_id"),
            "chebi_id": idc.get("chebi_id") or hm.get("chebi_id") or _s2v(r, "chebi_id"),
            # CAS는 UniChem 교차수집 대상이 아니다 — 제공 데이터셋/HMDB 레코드에서만 온다.
            "cas": _s2v(r, "cas"),
            "cas_origin": _s2v(r, "cas_origin"),
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
    dest = interim / f"{slug}_step4_classified.parquet"
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
