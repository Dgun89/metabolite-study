"""
6단계(본체): 정규화 테이블 생성 — assemble.py를 대체하는 정규화 파트.

step4(분류결과, 종별) + 공유 캐시(identifier/hmdb/enzyme/brenda)를 InChIKey 축으로
병합해 docs/schema_design.md의 6개 long-format 테이블을 만든다. 세 종을 함께 처리하며,
같은 InChIKey는 자동으로 한 화합물로 병합된다(compounds PK=inchikey).

출력 (data/normalized/*.parquet):
  compounds                (PK inchikey)              화합물 마스터
  compound_external_ids    (long)                     외부 식별자 (CNP/KEGG/HMDB/ChEBI/PubChem)
  compound_origins         (long)                     DB별 원본 기원 라벨(다중 보존)
  compound_classification  (1행/inchikey)             최종 판정 + conflict
  compound_enzymes         (long)                     효소 관계 (KEGG/Reactome/HMDB/BRENDA)
  compound_species         (long)                     inchikey ↔ species 관측 매핑

전 테이블 provenance 컬럼(source, source_version, retrieved_at) 포함.

사용:
    python pipeline/normalize.py
"""
import sys
import re
import json
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C
from pipeline.classify import classify_row_v2, classify_row_v3, assign_msi

ORG_SPLIT = re.compile(r"[;|]")

# UniChem이 이미 반환한 교차링크 중 external_ids에 함께 저장할 소스
# (KEGG/HMDB/ChEBI/PubChem/COCONUT는 별도 EXT_SPEC에서 처리하므로 제외).
# key = identifier_cache의 unichem dict 키, value = 저장할 소스 라벨.
UNICHEM_EXT = {
    "drugbank":    "DrugBank",
    "chembl":      "ChEMBL",
    "foodb":       "FooDB",
    "lipidmaps":   "LIPID MAPS",
    "swisslipids": "SwissLipids",
    "drugcentral": "DrugCentral",
    "gtopdb":      "Guide to Pharmacology",
    "bindingdb":   "BindingDB",
    "rcsb_pdb":    "RCSB PDB",
    "pdbe":        "PDBe",
    "wikipedia":   "Wikipedia",
    "comptox":     "EPA CompTox",
}

# MSI 등급 계산에 독립 증거로 계수할 DB 소스(compound_external_ids의 source 값 기준).
MSI_DB_SOURCES = {"HMDB", "KEGG", "ChEBI", "PubChem"}


def _load_json(name: str) -> dict:
    p = C.WORK / "interim" / name
    return json.loads(p.read_text()) if p.exists() else {}


def _aslist(val) -> list:
    """numpy array / list / None / scalar를 안전하게 리스트로."""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    if hasattr(val, "tolist"):          # numpy array
        return list(val.tolist())
    if isinstance(val, float) and pd.isna(val):
        return []
    return [val]


def _split_organisms(val) -> list:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return []
    return [o.strip() for o in ORG_SPLIT.split(s) if o.strip()]


def normalize() -> dict:
    id_cache = _load_json("identifier_cache.json")
    hmdb_idx = _load_json("hmdb_index.json")
    enz_cache = _load_json("enzyme_cache.json")
    brenda = _load_json("brenda_cache.json")

    coconut_ver = C.coconut_version()
    hmdb_ver = C.hmdb_version()
    now = C.now_iso()

    # ---------- MMMDB 참조 (쥐 조직 검출 근거) ----------
    # InChIKey → n_tissues, tissue 라벨 목록. full-InChIKey 매칭만 종특이 확증으로 사용.
    mmmdb_tissues = {}   # inchikey -> int (검출 조직 수)
    mmmdb_labels = {}    # inchikey -> [tissue, ...]
    if C.MMMDB_REFERENCE.exists():
        mref = pd.read_parquet(C.MMMDB_REFERENCE)
        for _, mr in mref.iterrows():
            ik = mr.get("InChIKey")
            if ik is None or (isinstance(ik, float) and pd.isna(ik)) or not str(ik).strip():
                continue
            ik = str(ik)
            n = mr.get("mmmdb_n_tissues")
            mmmdb_tissues[ik] = int(n) if pd.notna(n) else 0
            labs = _split_organisms(mr.get("mmmdb_tissues"))
            mmmdb_labels[ik] = labs
    mmmdb_ver = "MMMDB-reference"

    # 종별 step4 로드
    step4 = {}
    for sp in C.SPECIES:
        p = C.get_paths(sp)["interim"] / f"{sp}_step4_classified.parquet"
        if p.exists():
            step4[sp] = pd.read_parquet(p)
    if not step4:
        raise SystemExit("step4 parquet 없음 — 04_classify_run.py 먼저 실행")

    all_rows = pd.concat(
        [df.assign(species=sp) for sp, df in step4.items()], ignore_index=True)
    all_rows = all_rows[all_rows["inchikey"].notna()].copy()

    # ---------- compounds (PK inchikey) ----------
    comp = (all_rows.sort_values("species")
            .drop_duplicates("inchikey")
            [["inchikey", "inchikey14", "smiles", "inchi", "formula", "compound_name"]]
            .reset_index(drop=True))
    comp["created_at"] = now

    # ---------- compound_species (long) ----------
    # 무결성: (inchikey, species)는 유일해야 한다. 같은 화합물의 CNP id 버전
    # (예: CNP0361197.0 / CNP0361197.1)은 InChIKey 기준 동일 관측이므로,
    # cnp_id를 "; "로 병합해 한 행으로 접는다(다른 provenance 컬럼과 동일 방식).
    _sp = all_rows[["inchikey", "species", "cnp_id"]].copy()
    _sp["cnp_id"] = _sp["cnp_id"].where(_sp["cnp_id"].notna(), None)
    species_rows = (
        _sp.groupby(["inchikey", "species"], sort=False)["cnp_id"]
        .apply(lambda s: "; ".join(sorted({str(x) for x in s if x is not None
                                           and str(x).strip()
                                           and str(x).lower() not in ("nan", "none")})))
        .reset_index()
        .assign(source="pipeline-seed", source_version="seed-v1", retrieved_at=now)
        .reset_index(drop=True))

    # ---------- compound_external_ids (long) ----------
    ext = []
    EXT_SPEC = [
        ("coconut_id", "COCONUT", coconut_ver),
        ("cnp_id",     "COCONUT", coconut_ver),   # 시드 CNP id(버전 포함)
        ("kegg_id",    "KEGG",    C.SOURCE_VERSIONS["KEGG"]),
        ("hmdb_id",    "HMDB",    hmdb_ver),
        ("chebi_id",   "ChEBI",   C.SOURCE_VERSIONS["ChEBI"]),
        ("pubchem_cid", "PubChem", C.SOURCE_VERSIONS["PubChem"]),
    ]
    for _, r in all_rows.iterrows():
        ik = r["inchikey"]
        for col, src, ver in EXT_SPEC:
            v = r.get(col)
            if v is not None and str(v).strip() and str(v).lower() not in ("nan", "none"):
                ext.append({"inchikey": ik, "source": src, "external_id": str(v),
                            "source_version": ver, "retrieved_at": now})
    # UniChem이 이미 반환한 추가 교차링크(DrugBank/FooDB/LIPID MAPS/… — 재수집 없이 저장)
    uc_ver = C.SOURCE_VERSIONS["UniChem"]
    for ik in comp["inchikey"]:
        uc = (id_cache.get(ik, {}) or {}).get("unichem") or {}
        for key, label in UNICHEM_EXT.items():
            v = uc.get(key)
            if v is not None and str(v).strip() and str(v).lower() not in ("nan", "none"):
                ext.append({"inchikey": ik, "source": label, "external_id": str(v),
                            "source_version": uc_ver, "retrieved_at": now})
    ext_df = pd.DataFrame(ext).drop_duplicates(
        ["inchikey", "source", "external_id"]).reset_index(drop=True)

    # ---------- compound_origins (long, 다중 기원 보존) ----------
    origins = []
    # 화합물별 병합 입력 수집(분류 재계산에도 사용)
    agg = {}  # inchikey -> {roles:set, hmdb:set, orgs:set}
    for _, r in all_rows.iterrows():
        ik = r["inchikey"]
        a = agg.setdefault(ik, {"roles": set(), "hmdb": set(), "orgs": set()})
        # ChEBI roles (identifier_cache 우선, step4에도 chebi_roles 존재)
        roles = _aslist(id_cache.get(ik, {}).get("chebi_roles")) or _aslist(r.get("chebi_roles"))
        for role in roles:
            if role:
                a["roles"].add(str(role))
                origins.append({"inchikey": ik, "source": "ChEBI", "origin_label": str(role),
                                "source_version": C.SOURCE_VERSIONS["ChEBI"], "retrieved_at": now})
        # HMDB source labels
        hs = _aslist(hmdb_idx.get(ik, {}).get("hmdb_source")) or _aslist(r.get("hmdb_source"))
        for lab in hs:
            if lab:
                a["hmdb"].add(str(lab))
                origins.append({"inchikey": ik, "source": "HMDB", "origin_label": str(lab),
                                "source_version": hmdb_ver, "retrieved_at": now})
        # COCONUT organisms
        for org in _split_organisms(r.get("coconut_organisms")):
            a["orgs"].add(org)
            origins.append({"inchikey": ik, "source": "COCONUT", "origin_label": org,
                            "source_version": coconut_ver, "retrieved_at": now})
    # MMMDB 조직 검출 기원(화합물별 1회, full-InChIKey 매칭)
    for ik in comp["inchikey"]:
        for lab in mmmdb_labels.get(ik, []):
            origins.append({"inchikey": ik, "source": "MMMDB",
                            "origin_label": f"mouse tissue: {lab}",
                            "source_version": mmmdb_ver, "retrieved_at": now})
    origins_df = pd.DataFrame(origins).drop_duplicates(
        ["inchikey", "source", "origin_label"]).reset_index(drop=True)

    # ---------- compound_classification (1행/inchikey, 병합 입력으로 재계산) ----------
    # classify_row_v3: MMMDB(쥐 조직 검출)를 최우선 endogenous 근거(E0)로 반영.
    cls_rows = []
    for ik, a in agg.items():
        v = classify_row_v3(sorted(a["roles"]), sorted(a["hmdb"]),
                            "; ".join(sorted(a["orgs"])),
                            mmmdb_tissues=mmmdb_tissues.get(ik, 0))
        cls_rows.append({
            "inchikey": ik,
            "classification": v["classification"],
            "basis": v["classification_basis"],
            "conflict_flag": v["conflict_flag"],
            "conflicting_sources": v["conflicting_sources"],
            "mmmdb_detected": v["mmmdb_detected"],
            "mmmdb_n_tissues": v["mmmdb_n_tissues"],
            "classified_at": now,
            "ruleset_version": "classify.py:rules-v3",
        })
    cls_df = pd.DataFrame(cls_rows).reset_index(drop=True)

    # ---------- compound_enzymes (long) ----------
    enz_rows = []
    name_to_ik = {}  # BRENDA는 compound_name 키 → inchikey 역매핑
    for _, r in all_rows.iterrows():
        if pd.notna(r.get("compound_name")):
            name_to_ik.setdefault(str(r["compound_name"]), r["inchikey"])
    for ik in comp["inchikey"]:
        e = enz_cache.get(ik, {})
        ev = e.get("source_version")
        rt = e.get("retrieved_at", now)
        for ec in (e.get("kegg_ec") or []):
            enz_rows.append({"inchikey": ik, "enzyme_source": "KEGG", "ec_number": ec,
                             "gene_name": None, "source_version": C.SOURCE_VERSIONS["KEGG"],
                             "retrieved_at": rt})
        for cat in (e.get("reactome_catalysts") or []):
            enz_rows.append({"inchikey": ik, "enzyme_source": "Reactome", "ec_number": None,
                             "gene_name": cat, "source_version": C.SOURCE_VERSIONS["Reactome"],
                             "retrieved_at": rt})
        h = hmdb_idx.get(ik, {})
        for gene in (h.get("genes") or []):
            enz_rows.append({"inchikey": ik, "enzyme_source": "HMDB", "ec_number": None,
                             "gene_name": gene, "source_version": hmdb_ver,
                             "retrieved_at": h.get("retrieved_at", now)})
    # BRENDA: 이름 기반
    for name, ik in name_to_ik.items():
        b = brenda.get(name, {})
        for ec in (b.get("ec_numbers") or []):
            enz_rows.append({"inchikey": ik, "enzyme_source": "BRENDA", "ec_number": ec,
                             "gene_name": None, "source_version": C.SOURCE_VERSIONS["BRENDA"],
                             "retrieved_at": b.get("retrieved_at", now)})
    enz_df = (pd.DataFrame(enz_rows) if enz_rows else pd.DataFrame(
        columns=["inchikey", "enzyme_source", "ec_number", "gene_name",
                 "source_version", "retrieved_at"]))
    enz_df = enz_df.drop_duplicates(
        ["inchikey", "enzyme_source", "ec_number", "gene_name"]).reset_index(drop=True)

    # ---------- MSI 등급 + MMMDB 플래그를 compounds 마스터에 부여 ----------
    # 독립 DB 증거 수 = external_ids 중 MSI_DB_SOURCES(HMDB/KEGG/ChEBI/PubChem) 고유 소스 수.
    db_count = (ext_df[ext_df["source"].isin(MSI_DB_SOURCES)]
                .groupby("inchikey")["source"].nunique().to_dict())
    msi_level, msi_evi, mm_flag, mm_nt = [], [], [], []
    for ik in comp["inchikey"]:
        n_tis = mmmdb_tissues.get(ik, 0)
        detected = bool(n_tis and n_tis > 0)
        n_db = db_count.get(ik, 0)
        lvl = assign_msi(has_inchikey=True, db_id_count=n_db, mmmdb_detected=detected)
        evi = sorted(set(ext_df.loc[(ext_df.inchikey == ik) &
                     (ext_df.source.isin(MSI_DB_SOURCES)), "source"]))
        if detected:
            evi.append(f"MMMDB({n_tis} tissues, InChIKey)")
        msi_level.append(lvl)
        msi_evi.append("; ".join(["InChIKey"] + evi))
        mm_flag.append(detected)
        mm_nt.append(int(n_tis) if detected else 0)
    comp["mmmdb_detected"] = mm_flag
    comp["mmmdb_n_tissues"] = mm_nt
    # db_support_level: 독립 DB가 이 구조를 지지하는 정도(structure-consensus proxy).
    # 표준 MSI(분광 확증)가 아니라 다중 DB 구조 합의 기반이므로 중립적 이름을 쓴다.
    #   L2 = 독립 DB ID >=2, L3 = <=1 (assign_msi 규칙 유지).
    comp["db_support_level"] = msi_level
    comp["db_support_evidence"] = msi_evi

    # ---------- 명시적 행 정렬 ----------
    # 분류(endogenous→exogenous→unverified) → 화합물명(대소문자 무시) → InChIKey.
    CLS_ORDER = {"endogenous": 0, "exogenous": 1, "unverified": 2}
    cls_map = dict(zip(cls_df["inchikey"], cls_df["classification"]))
    comp["_cls_rank"] = comp["inchikey"].map(lambda k: CLS_ORDER.get(cls_map.get(k), 3))
    comp["_name_key"] = comp["compound_name"].fillna("").astype(str).str.lower()
    comp = (comp.sort_values(["_cls_rank", "_name_key", "inchikey"])
            .drop(columns=["_cls_rank", "_name_key"]).reset_index(drop=True))

    # ---------- 저장 ----------
    C.NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    tables = {
        "compounds": comp,
        "compound_external_ids": ext_df,
        "compound_origins": origins_df,
        "compound_classification": cls_df,
        "compound_enzymes": enz_df,
        "compound_species": species_rows,
    }
    for name, df in tables.items():
        df.to_parquet(C.NORMALIZED_DIR / f"{name}.parquet", index=False)
        print(f"  {name:24s} {len(df):6d}행 → data/normalized/{name}.parquet")

    print(f"\ncompounds 고유 {len(comp)} | "
          f"conflict {int(cls_df['conflict_flag'].sum())} | "
          f"enzymes {len(enz_df)} rows")
    return tables


if __name__ == "__main__":
    normalize()
