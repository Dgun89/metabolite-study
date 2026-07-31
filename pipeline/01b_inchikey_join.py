"""
1b단계: InChIKey 진입 데이터셋의 구조 조인 — 01_coconut_join.py의 자매 스크립트.

01_coconut_join.py는 시드가 CNP id로 들어오는 데이터셋을 다룬다. 거기서 CNP id는
조인 축이 아니라 "InChIKey에 도달하는 수단"이다(COCONUT을 찾아 구조를 얻는 경로).

일부 데이터셋은 그 경로가 이미 끝난 상태로 들어온다 — 예: osaka(1)은 HMDB
accession으로 들어와 hmdb_resolved.json에서 이미 InChIKey로 해석돼 있다.
이때는 COCONUT을 InChIKey(standard_inchi_key)로 직접 조인하면 된다. CNP 경로의
버전 접미사(CNP0145332.1)·base_id 폴백·stereo 모호성 문제가 아예 발생하지 않아
오히려 더 결정론적이다.

조인 정책:
  1) COCONUT standard_inchi_key == 시드 inchikey  → match_type="inchikey_coconut"
     같은 InChIKey에 여러 CNP 엔트리가 있으면 최저 버전 선택(01단계와 동일한
     결정론적 규칙). n_coconut_versions로 다중성을 노출한다.
  2) COCONUT 미수록(천연물 DB이므로 흔함) → match_type="hmdb_only"
     구조·formula는 HMDB 레코드 값을 쓴다. mol_weight는 COCONUT의 평균분자량과
     시드의 exact_mass(단일동위원소질량)가 다른 물리량이므로 채우지 않는다(혼동 방지).
  3) InChIKey 자체가 없는 행 → match_type="unresolved" (normalize가 제외)

출력 컬럼은 01단계 step2와 동일 스키마 + 하류 폴백용 추가 컬럼
(hmdb_id/kegg_id/chebi_id/cas/hmdb_source). 04_classify_run.py는 이 컬럼들을
id_cache·hmdb_index에 값이 없을 때의 폴백으로 사용한다.

출력: WORK/interim/{slug}/{slug}_step2_coconut.parquet
  provenance: source, source_version(COCONUT 스냅샷 + HMDB 릴리스), retrieved_at

사용:
    python pipeline/01b_inchikey_join.py "osaka(1)"
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

CHUNK = 100_000
VER_RE = re.compile(r"\.(\d+)$")

COCONUT_USE = [
    "identifier", "canonical_smiles", "standard_inchi", "standard_inchi_key",
    "molecular_weight", "molecular_formula", "np_classifier_pathway",
    "np_classifier_superclass", "np_classifier_class", "chemical_class", "organisms",
]

# 데이터셋별 HMDB 해석 결과(accession → 구조/식별자). 01b를 쓰는 데이터셋만 등록.
HMDB_RESOLVED = {
    "osaka(1)": C.BASE / "data" / "osaka" / "0731" / "hmdb_resolved.json",
}


def version_num(identifier: str) -> int:
    m = VER_RE.search(str(identifier))
    return int(m.group(1)) if m else -1


def load_coconut_by_inchikey(inchikeys: set) -> pd.DataFrame:
    """standard_inchi_key가 시드에 포함된 COCONUT 행만 청크 스트리밍으로 수집."""
    keep = []
    for chunk in pd.read_csv(C.COCONUT_CSV, usecols=COCONUT_USE, chunksize=CHUNK,
                             dtype=str, low_memory=False):
        sel = chunk[chunk["standard_inchi_key"].isin(inchikeys)]
        if len(sel):
            keep.append(sel)
    if not keep:
        return pd.DataFrame(columns=COCONUT_USE)
    return pd.concat(keep, ignore_index=True)


def _clean(v):
    """빈 문자열·nan·none을 None으로 통일."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    return s


def join_dataset(species: str) -> pd.DataFrame:
    seed = pd.read_csv(C.RAW_SEEDS[species], dtype=str)
    if "inchikey" not in seed.columns:
        raise SystemExit(
            f"[{species}] 시드에 inchikey 컬럼이 없음 — 이 스크립트는 InChIKey가 "
            f"이미 해석된 데이터셋용이다. CNP 진입이면 01_coconut_join.py를 쓸 것.")

    # HMDB 레코드(구조·기원 라벨) — accession 키
    hres = {}
    rp = HMDB_RESOLVED.get(species)
    if rp and rp.exists():
        hres = json.loads(rp.read_text(encoding="utf-8"))
    hres_by_ik = {}
    for rec in hres.values():
        ik = _clean(rec.get("inchikey"))
        if ik and ik not in hres_by_ik:
            hres_by_ik[ik] = rec

    iks = {ik for ik in (_clean(v) for v in seed["inchikey"]) if ik}
    print(f"[{species}] 시드 {len(seed)}행 | InChIKey {len(iks)}개 | "
          f"COCONUT InChIKey 조인 시작 ...", flush=True)
    coco = load_coconut_by_inchikey(iks)
    if len(coco):
        coco["ver"] = coco["identifier"].map(version_num)
    print(f"[{species}] COCONUT 매칭 행 {len(coco)} | "
          f"고유 InChIKey {coco['standard_inchi_key'].nunique() if len(coco) else 0}",
          flush=True)

    now = datetime.now(timezone.utc).isoformat()
    src_ver = f"COCONUT={C.coconut_version()}; HMDB={C.hmdb_version()}"

    rows = []
    for _, r in seed.iterrows():
        ik = _clean(r.get("inchikey"))
        hm = hres_by_ik.get(ik, {}) if ik else {}
        cand = coco[coco["standard_inchi_key"] == ik] if (ik and len(coco)) else coco.iloc[0:0]

        if ik is None:
            match_type = "unresolved"
            pick = None
        elif len(cand):
            # 최저 버전 선택 (01단계와 동일한 결정론적 규칙)
            pick = cand.sort_values("ver").iloc[0]
            match_type = "inchikey_coconut"
        else:
            pick = None
            match_type = "hmdb_only"

        # 구조: COCONUT 우선, 없으면 HMDB 레코드, 없으면 시드
        smiles = _clean(pick["canonical_smiles"]) if pick is not None else None
        smiles = smiles or _clean(hm.get("smiles")) or _clean(r.get("hmdb_smiles"))
        inchi = _clean(pick["standard_inchi"]) if pick is not None else None
        formula = _clean(pick["molecular_formula"]) if pick is not None else None
        formula = formula or _clean(hm.get("formula")) or _clean(r.get("formula"))
        # mol_weight(평균분자량)는 COCONUT만 신뢰. 시드 exact_mass는 다른 물리량이라 쓰지 않음.
        mol_weight = _clean(pick["molecular_weight"]) if pick is not None else None

        rec = {
            # 01단계 step2와 동일 스키마 (cnp_id는 이 경로에 없으므로 None)
            "cnp_id": None,
            "base_id": None,
            "compound_name": _clean(r.get("name")) or _clean(hm.get("name")),
            "id_type": "HMDB",
            "match_type": match_type,
            "ambiguous_stereo": False,   # InChIKey 완전일치 조인이므로 stereo 모호성 없음
            "n_coconut_versions": int(len(cand)),
            "coconut_id": _clean(pick["identifier"]) if pick is not None else None,
            "smiles": smiles,
            "inchi": inchi,
            "inchikey": ik,
            "mol_weight": mol_weight,
            "formula": formula,
            "np_classifier_pathway": _clean(pick["np_classifier_pathway"]) if pick is not None else None,
            "np_classifier_superclass": _clean(pick["np_classifier_superclass"]) if pick is not None else None,
            "np_classifier_class": _clean(pick["np_classifier_class"]) if pick is not None else None,
            "chemical_class": _clean(pick["chemical_class"]) if pick is not None else None,
            "organisms": _clean(pick["organisms"]) if pick is not None else None,
            # --- 하류 폴백용 (04_classify_run이 id_cache/hmdb_index에 없을 때 사용) ---
            "hmdb_id": _clean(r.get("hmdb_id")) or _clean(hm.get("accession")),
            "kegg_id": _clean(r.get("kegg_id")) or _clean(hm.get("kegg_id")),
            "chebi_id": _clean(r.get("hmdb_chebi")) or _clean(hm.get("chebi_id")),
            # CAS: 제공 파일 값 우선, 없으면 HMDB 레코드. 어느 쪽인지 provenance로 남긴다.
            "cas": _clean(r.get("cas")) or _clean(hm.get("cas")) or _clean(r.get("hmdb_cas")),
            "cas_origin": ("contributor" if _clean(r.get("cas")) else
                           ("HMDB" if (_clean(hm.get("cas")) or _clean(r.get("hmdb_cas"))) else None)),
            "hmdb_source": hm.get("hmdb_source") or [],
            "source_row": _clean(r.get("source_row")),
            "source": "01b_inchikey_join.py",
            "source_version": src_ver,
            "retrieved_at": now,
        }
        rows.append(rec)

    out = pd.DataFrame(rows)
    P = C.get_paths(species)
    P["interim"].mkdir(parents=True, exist_ok=True)
    slug = C.dataset_slug(species)
    dest = P["interim"] / f"{slug}_step2_coconut.parquet"
    out.to_parquet(dest, index=False)

    vc = out["match_type"].value_counts().to_dict()
    print(f"[{species}] {len(out)}행 | "
          f"coconut {vc.get('inchikey_coconut', 0)} / "
          f"hmdb_only {vc.get('hmdb_only', 0)} / "
          f"unresolved {vc.get('unresolved', 0)} | "
          f"CAS {out['cas'].notna().sum()} → {dest.name}")
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or [sp for sp in C.SPECIES if sp in HMDB_RESOLVED]
    if not targets:
        raise SystemExit("대상 데이터셋을 지정할 것 (예: 'osaka(1)')")
    for sp in targets:
        join_dataset(sp)
