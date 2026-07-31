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
from pipeline.classify import classify_row_v2, classify_row_v3, classify_row_v4, assign_msi

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
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _load_source_hierarchy() -> dict:
    """HMDB Source 서브트리 계층 맵 로드.

    반환: term(lower) -> {"category": 최상위버킷, "level": int, "path": str}.
    파일이 없으면 빈 dict(주석 컬럼은 None으로 채워짐 — 하위호환).
    build_source_hierarchy.py로 생성: data/reference/hmdb_source_hierarchy.json.
    """
    p = C.HMDB_SOURCE_HIERARCHY
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8")).get("terms", {})
    return {t.lower(): {"category": v.get("top_bucket"),
                        "level": v.get("level"),
                        "path": v.get("path")}
            for t, v in raw.items()}


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
    src_hier = _load_source_hierarchy()   # HMDB 기원 라벨 → 6버킷 roll-up 주석

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
        # 파일명에는 슬러그를 쓴다(라벨의 괄호 등 메타문자가 경로에 새지 않도록).
        p = C.get_paths(sp)["interim"] / f"{C.dataset_slug(sp)}_step4_classified.parquet"
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
    # CAS 등록번호는 UniChem 교차수집 대상이 아니다 — 제공 데이터셋이 직접 준 값이거나
    # HMDB 레코드에서 읽은 값이다. 어느 쪽인지 행마다 다르므로 EXT_SPEC의 일괄 버전을
    # 쓰지 못하고, step4의 cas_origin에 따라 source_version을 개별로 붙인다.
    for _, r in all_rows.iterrows():
        v = r.get("cas")
        if v is None or not str(v).strip() or str(v).lower() in ("nan", "none"):
            continue
        origin = r.get("cas_origin")
        origin = str(origin) if origin is not None and str(origin).strip() \
            and str(origin).lower() not in ("nan", "none") else "unknown"
        ver = hmdb_ver if origin == "HMDB" else f"dataset:{r.get('species', '?')}"
        ext.append({"inchikey": r["inchikey"], "source": "CAS", "external_id": str(v),
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
    # 각 기원 행에 origin_category(6버킷 roll-up)와 origin_level(트리 깊이)을 주석해
    # 평평한 origin_label을 항해 가능한 계층으로 정리한다. HMDB 기원 라벨은
    # Disposition>Source 서브트리(build_source_hierarchy.py)로 roll-up하고, 그 외
    # 소스는 소스 성격에 맞는 고정 카테고리를 준다:
    #   ChEBI role     -> "ChEBI role"        (구조/역할 온톨로지, Source와 무관)
    #   COCONUT organism-> "Biological (COCONUT)"  (천연물 생물기원)
    #   MMMDB tissue   -> "Endogenous (MMMDB tissue)"  (쥐 조직 실검출 = 내인성 직접근거)
    # HMDB 라벨이 맵에 없으면(신규/희귀 term) category=None, level=None (하위호환).
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
                                "origin_category": "ChEBI role", "origin_level": None,
                                "source_version": C.SOURCE_VERSIONS["ChEBI"], "retrieved_at": now})
        # HMDB source labels — Disposition>Source 계층으로 6버킷 roll-up
        hs = _aslist(hmdb_idx.get(ik, {}).get("hmdb_source")) or _aslist(r.get("hmdb_source"))
        for lab in hs:
            if lab:
                a["hmdb"].add(str(lab))
                hinfo = src_hier.get(str(lab).lower(), {})
                origins.append({"inchikey": ik, "source": "HMDB", "origin_label": str(lab),
                                "origin_category": hinfo.get("category"),
                                "origin_level": hinfo.get("level"),
                                "source_version": hmdb_ver, "retrieved_at": now})
        # COCONUT organisms
        for org in _split_organisms(r.get("coconut_organisms")):
            a["orgs"].add(org)
            origins.append({"inchikey": ik, "source": "COCONUT", "origin_label": org,
                            "origin_category": "Biological (COCONUT)", "origin_level": None,
                            "source_version": coconut_ver, "retrieved_at": now})
    # MMMDB 조직 검출 기원(화합물별 1회, full-InChIKey 매칭)
    for ik in comp["inchikey"]:
        for lab in mmmdb_labels.get(ik, []):
            origins.append({"inchikey": ik, "source": "MMMDB",
                            "origin_label": f"mouse tissue: {lab}",
                            "origin_category": "Endogenous (MMMDB tissue)", "origin_level": None,
                            "source_version": mmmdb_ver, "retrieved_at": now})
    origins_df = pd.DataFrame(origins).drop_duplicates(
        ["inchikey", "source", "origin_label"]).reset_index(drop=True)

    # ---------- Drug/Food 신호(표시 전용, 필터 아님 — 2026-07-27 회의) ----------
    # DrugBank/DrugCentral 존재 → drug, FooDB 존재 → food. 행은 삭제하지 않고
    # 외부 신호를 '표시'만 한다(되돌릴 수 있게). 근거 DB는 별도 컬럼
    # (DrugBank/DrugCentral/FooDB)이 직접 보여주므로 basis 문자열은 두지 않는다.
    # 주의: FooDB '있음'은 detection 축이라 내인성 화합물도 다수 포함 → 표시일 뿐,
    #       이 컬럼만으로 exogenous를 단정하지 않는다(각 DB 축은 classification에서 별도 표기).
    DRUG_SITES = {"DrugBank", "DrugCentral"}
    FOOD_SITES = {"FooDB"}
    ext_by_ik = ext_df.groupby("inchikey")["source"].apply(set).to_dict()
    def _drug_food(ik):
        # 근거 DB는 별도 컬럼(DrugBank/DrugCentral/FooDB)이 직접 보여주므로
        # basis 문자열은 폐기. 여기서는 drug/food 태그(결론)만 만든다.
        srcs = ext_by_ik.get(ik, set())
        tags = []
        if srcs & DRUG_SITES:
            tags.append("drug")
        if srcs & FOOD_SITES:
            tags.append("food")
        return "; ".join(tags)

    # ---------- compound_classification (1행/inchikey, 병합 입력으로 재계산) ----------
    # classify_row_v4 (2026-07-27 회의): 우선순위 규칙 폐기. 각 DB 판정을 그대로 나열
    # ("ChEBI:endogenous; HMDB:endogenous; COCONUT:exogenous; MMMDB:endogenous").
    # v3(단일 라벨)는 classify.py에 박제로 남아있고, 여기서는 v4를 쓴다.
    cls_rows = []
    for ik, a in agg.items():
        v = classify_row_v4(sorted(a["roles"]), sorted(a["hmdb"]),
                            "; ".join(sorted(a["orgs"])),
                            mmmdb_tissues=mmmdb_tissues.get(ik, 0))
        df_tag = _drug_food(ik)
        cls_rows.append({
            "inchikey": ik,
            "drug_food": df_tag,
            "classification": v["classification"],
            "basis": v["classification_basis"],
            "conflict_flag": v["conflict_flag"],
            "conflicting_sources": v["conflicting_sources"],
            "mmmdb_detected": v["mmmdb_detected"],
            "mmmdb_n_tissues": v["mmmdb_n_tissues"],
            "classified_at": now,
            "ruleset_version": "classify.py:rules-v4",
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
    # v4는 classification이 "ChEBI:endogenous; HMDB:exogenous" 나열 문자열이므로
    # 단일 라벨 순위가 아니라 근거 성격으로 정렬한다:
    #   0 endogenous 근거 있음(포함) → 1 exogenous만 → 2 그 외/unverified.
    cls_map = dict(zip(cls_df["inchikey"], cls_df["classification"]))
    def _cls_rank_fn(k):
        s = str(cls_map.get(k, "")).lower()
        if "endogenous" in s:
            return 0
        if "exogenous" in s:
            return 1
        return 2
    comp["_cls_rank"] = comp["inchikey"].map(_cls_rank_fn)
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
