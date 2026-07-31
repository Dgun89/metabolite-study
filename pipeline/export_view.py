"""
7단계: export 뷰 생성 — 정규화 테이블(data/normalized/*.parquet) → 3시트 xlsx.

정규화 long-format 테이블이 원본(source of truth)이고, xlsx는 그 위에서 조인·와이드화한
재생성 가능한 파생 스냅샷이다(docs/schema_design.md §5). format_excel.apply_format을
재사용해 Data/Legend/Summary 3시트 + 그룹 색상·범례를 적용한다.

출력 (data/export/):
  {species}_yymmdd.xlsx  (데이터셋별 뷰, 예: human_serum_260728.xlsx)
  combined_yymmdd.xlsx   (3종 통합 뷰)
  * 파일명의 yymmdd는 생성일 스탬프 — export는 계속 재생성되는 뷰라 'final'이 아님.

새 스키마 표면: conflict_flag / conflicting_sources 컬럼을 뒤에 추가(표시).

사용:
    python pipeline/export_view.py               # 종별 3개 + combined
    python pipeline/export_view.py human         # 한 종만
    python pipeline/export_view.py combined       # 통합 뷰만
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# export 파일명에 붙는 생성일 스탬프 (yymmdd, '-' 없음).
# export는 계속 재생성되는 뷰이므로 'final'이 아니라 '언제 만든 스냅샷'임을 파일명에 명시.
#
# 재현성: 기본값은 '오늘'이지만, 환경변수 METABO_STAMP로 고정할 수 있다.
# 다른 PC(예: Windows)에서 하루 뒤에 돌려도 같은 파일명을 재현해야 하는 경우가 있어서다.
#   Linux/macOS:  METABO_STAMP=260731 python pipeline/export_view.py combined
#   Windows(cmd): set METABO_STAMP=260731 && python pipeline\export_view.py combined
#   Windows(PS):  $env:METABO_STAMP="260731"; python pipeline\export_view.py combined
STAMP = os.environ.get("METABO_STAMP") or datetime.now().strftime("%y%m%d")

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pipeline + format_excel(레포 루트)
from pipeline import config as C

SEMI = "; "


def _load_norm() -> dict:
    t = {}
    for name in ["compounds", "compound_external_ids", "compound_origins",
                 "compound_classification", "compound_enzymes", "compound_species"]:
        p = C.NORMALIZED_DIR / f"{name}.parquet"
        if not p.exists():
            raise SystemExit(f"{p} 없음 — normalize.py 먼저 실행")
        t[name] = pd.read_parquet(p)
    return t


def _agg(df, key, val, where=None):
    """key별로 val 컬럼을 중복 제거·정렬해 세미콜론 결합한 Series."""
    if where is not None:
        df = df[where]
    if len(df) == 0:
        return pd.Series(dtype=str)
    g = (df[[key, val]].dropna(subset=[val])
         .assign(**{val: lambda d: d[val].astype(str)})
         .groupby(key)[val]
         .apply(lambda s: SEMI.join(sorted(set(s)))))
    return g


def build_wide(tables: dict, inchikeys, with_datasets: bool = False) -> pd.DataFrame:
    comp = tables["compounds"]
    ext = tables["compound_external_ids"]
    ori = tables["compound_origins"]
    cls = tables["compound_classification"]
    enz = tables["compound_enzymes"]
    spc = tables["compound_species"]

    iks = list(inchikeys)
    # reset_index 필수: 아래 out은 RangeIndex이고 m()은 base["inchikey"].map(...)
    # 결과를 그대로 대입하므로, base 인덱스가 RangeIndex가 아니면 행이 어긋난다.
    base = comp[comp["inchikey"].isin(iks)].copy().reset_index(drop=True)

    # Database ID: 해당 InChIKey의 CNP id(들). compound_species.cnp_id 우선.
    cnp = _agg(spc[spc["inchikey"].isin(iks)], "inchikey", "cnp_id")

    def ext_val(src):
        return _agg(ext[ext["inchikey"].isin(iks)], "inchikey", "external_id",
                    where=ext[ext["inchikey"].isin(iks)]["source"] == src)

    def ori_val(src):
        sub = ori[ori["inchikey"].isin(iks)]
        return _agg(sub, "inchikey", "origin_label", where=sub["source"] == src)

    def ori_category(src):
        """해당 소스의 origin_category(6버킷 roll-up) 고유값을 모아 반환.
        평평한 origin_label 대신 최상위 버킷만 보여줘 뷰에서 기원 유형을 한눈에.
        """
        sub = ori[ori["inchikey"].isin(iks)]
        if "origin_category" not in sub.columns:
            return _agg(sub.iloc[0:0], "inchikey", "origin_label")
        mask = (sub["source"] == src) & sub["origin_category"].notna()
        return _agg(sub[mask], "inchikey", "origin_category")

    def enz_val(src, col):
        sub = enz[enz["inchikey"].isin(iks)]
        return _agg(sub, "inchikey", col, where=sub["enzyme_source"] == src)

    def m(series):
        return base["inchikey"].map(series).fillna("")

    cls_i = cls.set_index("inchikey")
    comp_i = base.set_index("inchikey")

    out = pd.DataFrame()
    # --- Basic Identifiers: InChIKey를 기본키로 맨 앞에 배치 ---
    out["InChIKey"]      = base["inchikey"].values
    out["compound_name"] = base["compound_name"].values
    out["SMILES"]        = base["smiles"].fillna("").values
    # --- External DB IDs (COCONUT CNP id는 다른 외부 DB 식별자와 동일 성격이므로
    #     이 블록의 맨 앞에 배치: COCONUT이 모든 화합물의 시드 출처 DB) ---
    out["COCONUT"]       = m(cnp)   # (구 "Database ID"/"coconut_ids") 이 InChIKey에 매핑된 COCONUT CNP id(들)
    out["PubChem"]       = m(ext_val("PubChem"))
    out["KEGG"]          = m(ext_val("KEGG"))
    out["HMDB"]          = m(ext_val("HMDB"))
    out["ChEBI"]         = m(ext_val("ChEBI"))
    # CAS는 UniChem 교차조회 대상이 아님 — 기여 데이터셋(osaka(1) 등)이나 HMDB
    # 로컬 레코드에서 온 값이 compound_external_ids에 source='CAS'로 적재된다.
    out["CAS"]           = m(ext_val("CAS"))
    out["DrugBank"]      = m(ext_val("DrugBank"))
    out["DrugCentral"]   = m(ext_val("DrugCentral"))  # drug_food의 근거 DB(감사용) — DrugBank와 함께 drug 판정 소스
    out["FooDB"]         = m(ext_val("FooDB"))
    out["LIPID MAPS"]    = m(ext_val("LIPID MAPS"))
    # --- Drug/Food 신호 (classification 앞 1차 필터 표시, 삭제 아님) ---
    out["drug_food"]            = base["inchikey"].map(cls_i["drug_food"]).fillna("").values
    # --- Classification ---
    out["classification"]       = base["inchikey"].map(cls_i["classification"]).fillna("unverified").values
    out["hmdb_origin"]          = m(ori_val("HMDB"))
    # HMDB 기원을 6개 최상위 버킷으로 roll-up(Endogenous/Food/Biological/…) —
    # 종명까지 뭉친 hmdb_origin과 달리 기원 '유형'을 한눈에 보게 하는 요약 컬럼.
    out["hmdb_origin_category"] = m(ori_category("HMDB"))
    out["coconut_organisms"]    = m(ori_val("COCONUT"))
    out["chebi_roles"]          = m(ori_val("ChEBI"))
    out["classification_basis"] = base["inchikey"].map(cls_i["basis"]).fillna("").values
    # --- DB Support (structure-consensus proxy, not spectral MSI) + MMMDB ---
    out["db_support_level"]    = base["inchikey"].map(comp_i["db_support_level"]).fillna("").values
    out["db_support_evidence"] = base["inchikey"].map(comp_i["db_support_evidence"]).fillna("").values
    out["mmmdb_detected"]   = base["inchikey"].map(comp_i["mmmdb_detected"]).fillna(False).values
    out["mmmdb_tissues"]    = m(ori_val("MMMDB"))
    # --- Enzyme Information ---
    out["kegg_enzymes"]      = m(enz_val("KEGG", "ec_number"))
    out["hmdb_enzymes"]      = m(enz_val("HMDB", "gene_name"))
    out["reactome_catalysts"] = m(enz_val("Reactome", "gene_name"))
    out["brenda_enzymes"]    = m(enz_val("BRENDA", "ec_number"))
    # 통합본: 각 화합물이 어느 데이터셋(human/mouse_serum/mouse_feces)에서 관측됐는지
    if with_datasets:
        ds = _agg(spc[spc["inchikey"].isin(iks)], "inchikey", "species")
        out["datasets"] = m(ds)
    # 새 스키마 표면 (extras → format_excel이 뒤에 배치)
    out["conflict_flag"]        = base["inchikey"].map(cls_i["conflict_flag"]).fillna(False).values
    out["conflicting_sources"]  = base["inchikey"].map(cls_i["conflicting_sources"]).fillna("").values
    return out.reset_index(drop=True)


def export_species(tables: dict, species: str) -> Path | None:
    spc = tables["compound_species"]
    iks = spc[spc["species"] == species]["inchikey"].unique()
    if len(iks) == 0:
        # 이 데이터셋이 정규화 테이블에 없다 — 보통 step4 캐시가 이 PC에 없는 경우다
        # (원본 데이터는 git에 올리지 않으므로 clone에는 3종 캐시만 들어온다).
        # 0행 워크북을 만들면 Summary 시트의 비율 계산이 의미를 잃으므로 건너뛴다.
        print(f"[{species}] 정규화 테이블에 행 없음 — 건너뜀 "
              f"(step4 캐시 미존재로 추정)")
        return None
    df = build_wide(tables, iks)
    C.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    # 파일명에는 슬러그를 쓴다: 라벨 'osaka(1)'의 괄호가 파일명에 새면
    # 셸 글롭·윈도우 경로 처리에서 문제가 된다. 기존 3종은 슬러그=라벨이라 변화 없음.
    dest = C.EXPORT_DIR / f"{C.dataset_slug(species)}_{STAMP}.xlsx"
    df.to_excel(dest, index=False)
    from format_excel import apply_format
    apply_format(str(dest))
    print(f"[{species}] {len(df)}행 → data/export/{dest.name}")
    return dest


def export_combined(tables: dict) -> Path:
    iks = tables["compounds"]["inchikey"].unique()
    df = build_wide(tables, iks, with_datasets=True)
    C.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    dest = C.EXPORT_DIR / f"combined_{STAMP}.xlsx"
    df.to_excel(dest, index=False)
    from format_excel import apply_format
    apply_format(str(dest))
    print(f"[combined] {len(df)}행(고유 InChIKey) → data/export/{dest.name}")
    return dest


if __name__ == "__main__":
    tables = _load_norm()
    args = sys.argv[1:]
    if not args:
        for sp in C.SPECIES:
            export_species(tables, sp)
        export_combined(tables)
    else:
        for a in args:
            if a == "combined":
                export_combined(tables)
            else:
                export_species(tables, a)
