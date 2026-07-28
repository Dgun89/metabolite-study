"""
0단계: 원본 annotation 파일 → 표준 시드 CSV.

세 세트(human/mouse/legacy)의 원본은 모두 "CNP id 목록"이 시작점이다.
원본에는 같은 화합물(같은 full CNP id)이 여러 LC 피처 행으로 반복돼 있으므로,
여기서 full CNP id 기준 중복을 제거(첫 행 유지)해 "고유 화합물" 시드를 만든다.

중복 제거 정책(기존 03_deduplicate_final.py 승계):
  - full CNP id(버전 접미사 .0/.1 포함) 기준, 첫 행 유지.
  - 입체이성질체(같은 base id, 다른 접미사)는 다른 화합물로 유지.
  - 구조가 실제로 같은지(InChIKey)는 이후 normalize 단계에서 한 번 더 병합.

시드 컬럼(공통): cnp_id, base_id, compound_name
  - cnp_id      : 원본 그대로의 full CNP id (예: CNP0243745.0)
  - base_id     : 버전 접미사 제거 (예: CNP0243745) — COCONUT 조인 폴백용
  - compound_name : 원본 annotation / QualitativeResults

raw 원칙: 원본 파일은 수정하지 않는다. 시드는 원본에서 컬럼만 뽑은 파생물이며
data/{species}/raw/{species}_seed.csv 에 저장한다(시드도 raw로 취급, 재추출 가능).

사용:
    python pipeline/00_make_seeds.py           # 세 종 전부
    python pipeline/00_make_seeds.py human     # 한 종만
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

# 원본 파일별 (CNP id 컬럼, 화합물명 컬럼)
SOURCE_COLS = {
    "human_serum": ("id", "annotation"),
    "mouse_serum": ("id", "annotation"),
    "mouse_feces": ("Database ID", "QualitativeResults"),
}


def strip_version(cnp: str) -> str:
    """CNP0243745.0 -> CNP0243745 (버전 접미사 제거)."""
    s = str(cnp).strip()
    if "." in s:
        head, tail = s.rsplit(".", 1)
        if tail.isdigit():
            return head
    return s


def make_seed(species: str) -> pd.DataFrame:
    raw = C.RAW_SOURCES[species]
    id_col, name_col = SOURCE_COLS[species]
    df = pd.read_excel(raw, sheet_name=0)
    n_raw = len(df)

    out = pd.DataFrame({
        "cnp_id": df[id_col].astype(str).str.strip(),
        "compound_name": df[name_col].astype(str).str.strip(),
    })
    # 빈 CNP id 제거
    # id_type: CNP(COCONUT) 또는 PEP(펩타이드 DB, legacy에만 존재).
    out["id_type"] = out["cnp_id"].str.upper().str[:3]
    out = out[out["id_type"].isin(["CNP", "PEP"])].copy()
    n_valid = len(out)
    # full id 기준 중복 제거(첫 행 유지)
    out = out.drop_duplicates("cnp_id", keep="first").reset_index(drop=True)
    out.insert(1, "base_id", out["cnp_id"].map(strip_version))
    # 최종 컬럼 순서
    out = out[["cnp_id", "base_id", "compound_name", "id_type"]]

    seed_path = C.RAW_SEEDS[species]
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(seed_path, index=False)
    n_cnp = (out.id_type == "CNP").sum()
    n_pep = (out.id_type == "PEP").sum()
    print(f"{species}: raw {n_raw}행 | 유효 {n_valid} | 고유 {len(out)} "
          f"(중복 {n_valid - len(out)} 제거) | CNP {n_cnp} PEP {n_pep} "
          f"→ {seed_path.relative_to(C.BASE)}")
    if n_pep:
        print(f"  주: PEP(펩타이드) {n_pep}개는 COCONUT 미매칭 → 01_coconut_join.py가 "
              f"{species}_pep_resolved.csv(PubChem 이름검색 + RDKit 서열)로 구조 보강.")
    return out


if __name__ == "__main__":
    targets = sys.argv[1:] or list(C.SPECIES)
    for sp in targets:
        make_seed(sp)
