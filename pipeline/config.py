"""
공통 파이프라인 설정 — SPECIES 전환으로 human/mouse/legacy 처리.

경로 이식성:
    BASE : 저장소 루트. 기본값은 이 파일 위치(pipeline/)의 부모.
           환경변수 METABO_BASE 로 오버라이드.
    WORK : 재생성 가능한 중간·최종 산출물 작업 디렉터리(gitignore).
           기본값 BASE/".work". 환경변수 METABO_WORK 로 오버라이드.

사용법:
    from pipeline.config import get_paths
    P = get_paths("human_serum")   # "mouse_serum" | "mouse_feces"
"""
import os
from pathlib import Path

# --- 이식 가능한 경로 (하드코딩 제거) ---
# 기본 BASE = 저장소 루트 = 이 파일(pipeline/config.py)의 상위 디렉터리.
BASE = Path(os.environ.get("METABO_BASE", Path(__file__).resolve().parent.parent))
# WORK = 재생성 가능한 산출물 디렉터리. 기본은 BASE/.work (gitignore 대상).
WORK = Path(os.environ.get("METABO_WORK", BASE / ".work"))

REF = BASE / "data" / "reference"
COCONUT_CSV = REF / "coconut_complete.csv"
HMDB_XML = REF / "hmdb_metabolites.xml"
# HMDB 'Disposition > Source' 서브트리 계층 맵(build_source_hierarchy.py 생성).
# normalize.py가 HMDB 기원 라벨을 6개 최상위 버킷으로 roll-up 주석할 때 참조.
HMDB_SOURCE_HIERARCHY = REF / "hmdb_source_hierarchy.json"

# 본체(정규화 테이블)와 export(xlsx 뷰) — 저장소 tree 안(gitignore로 데이터는 제외).
NORMALIZED_DIR = BASE / "data" / "normalized"
EXPORT_DIR = BASE / "data" / "export"

# 데이터셋(시료 유래):
#   human_serum : 사람 혈청 (기존 "human" — 2026-07-27 회의 결정으로 개명)
#   mouse_serum : 쥐 혈청 (기존 "mouse")
#   mouse_feces : 쥐 분변 (기존 "legacy" — step29로 정리된 902 화합물 세트)
# 주의: 시료 폴더(data/human/)는 raw 보존 원칙에 따라 이름 유지. 종 키만 human_serum.
#   osaka(1)    : 오사카대 제공 pooled 표적 패널 (2026-07-31 수령, 771행).
#                 다른 데이터셋과 달리 진입 키가 CNP id가 아니라 HMDB accession이다.
#                 라벨에 (n)을 붙인 이유: 같은 제공처에서 추가 파일을 받을 수 있어
#                 수령 차수를 데이터셋 축에 남긴다 — 다음 파일은 "osaka(2)".
#                 주의: 괄호는 정규식 메타문자다. datasets 컬럼을 필터할 때는
#                 리터럴 문자열 비교(str.contains(..., regex=False))를 쓸 것.
SPECIES = ("human_serum", "mouse_serum", "mouse_feces", "osaka(1)")

# 파일시스템·식별자로 안전한 데이터셋 슬러그(괄호 제거). 경로/파일명에 쓴다.
DATASET_SLUG = {
    "human_serum": "human_serum",
    "mouse_serum": "mouse_serum",
    "mouse_feces": "mouse_feces",
    "osaka(1)":    "osaka1",
}


def dataset_slug(species: str) -> str:
    """데이터셋 라벨 → 경로/파일명 안전 슬러그. 미등록 라벨은 비영숫자를 _로 치환."""
    import re as _re
    return DATASET_SLUG.get(species) or _re.sub(r"[^0-9A-Za-z]+", "_", species).strip("_")

# 각 데이터셋의 시드(원본에서 CNP/PEP id + 이름만 추출한 표준 시드 CSV).
RAW_SEEDS = {
    "human_serum": BASE / "data" / "human"       / "raw" / "human_seed.csv",
    "mouse_serum": BASE / "data" / "mouse_serum" / "raw" / "mouse_serum_seed.csv",
    "mouse_feces": BASE / "data" / "mouse_feces" / "raw" / "mouse_feces_seed.csv",
    # osaka(1)은 수령 차수별 폴더(data/osaka/{수령일}/)에 원본과 시드를 함께 둔다.
    "osaka(1)":    BASE / "data" / "osaka" / "0731" / "osaka1_seed.csv",
}

# 원본 annotation 파일(참고·시드 추출용, raw 원칙에 따라 수정 금지).
RAW_SOURCES = {
    "human_serum": BASE / "data" / "human"       / "raw" / "annotation_output_hito.xlsx",
    "mouse_serum": BASE / "data" / "mouse_serum" / "raw" / "annotation_output_mouse.xlsx",
    "mouse_feces": BASE / "data" / "mouse_feces" / "raw" / "metabolites_completed.xlsx",
    "osaka(1)":    BASE / "data" / "osaka" / "0731" / "osaka_pooled_0731.xlsx",
}

# MMMDB(Mouse Multiple tissue Metabolome DataBase) 참조 — 실제 쥐 조직 검출 근거.
MMMDB_REFERENCE = BASE / "data" / "mouse_serum" / "reference" / "mmmdb_reference.parquet"

# 하위호환: 기존 코드가 RAW_FILES[...]로 원본 annotation 파일을 참조.
RAW_FILES = RAW_SOURCES


def get_paths(species: str) -> dict:
    assert species in SPECIES, f"unknown species: {species!r} (expected one of {SPECIES})"
    # 디렉터리명에는 슬러그를 쓴다: 라벨에 괄호 등 셸 메타문자가 있어도
    # 경로가 안전하도록. 기존 3종은 슬러그==라벨이라 경로가 바뀌지 않는다.
    slug = dataset_slug(species)
    interim = WORK / "interim" / slug
    final = WORK / "final" / slug
    interim.mkdir(parents=True, exist_ok=True)
    final.mkdir(parents=True, exist_ok=True)
    return {
        "species": species,
        "slug": slug,
        "raw": RAW_SOURCES[species],
        "seed": RAW_SEEDS[species],
        "interim": interim,
        "final": final,
        "coconut_csv": COCONUT_CSV,
        "hmdb_xml": HMDB_XML,
        "normalized": NORMALIZED_DIR,
        "export": EXPORT_DIR,
    }


def coconut_version() -> str:
    """COCONUT 스냅샷 버전 태그(provenance용). 파일 mtime 날짜."""
    from datetime import datetime, timezone
    try:
        mt = COCONUT_CSV.stat().st_mtime
        return "COCONUT-snapshot-" + datetime.fromtimestamp(mt, timezone.utc).strftime("%Y%m%d")
    except OSError:
        return "COCONUT-snapshot-unknown"


def hmdb_version() -> str:
    """HMDB XML 버전 태그(provenance용). 파일 mtime 날짜."""
    from datetime import datetime, timezone
    try:
        mt = HMDB_XML.stat().st_mtime
        return "HMDB-local-" + datetime.fromtimestamp(mt, timezone.utc).strftime("%Y%m%d")
    except OSError:
        return "HMDB-local-unknown"


def now_iso() -> str:
    """현재 UTC 시각 ISO8601 (retrieved_at provenance용)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# 외부 소스별 provenance 버전 태그. API가 명시 버전을 주지 않는 경우
# 접근 엔드포인트/방식을 기록하고, retrieved_at(now_iso)이 시점을 담는다.
SOURCE_VERSIONS = {
    "UniChem": "UniChem-REST-v1",
    "ChEBI":   "ChEBI-REST-public",
    "PubChem": "PubChem-PUG-REST",
    "KEGG":    "KEGG-REST",
    "Reactome": "Reactome-ContentService",
    "BRENDA":  "BRENDA-SOAP",
}


def all_inchikeys(species_list=None):
    """주어진 종들의 step2 parquet에서 고유 InChIKey 목록(소문자 컬럼)."""
    import pandas as pd
    species_list = species_list or list(SPECIES)
    frames = []
    for sp in species_list:
        p = get_paths(sp)["interim"] / f"{dataset_slug(sp)}_step2_coconut.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p, columns=["inchikey"]))
    if not frames:
        return []
    s = pd.concat(frames)["inchikey"].dropna()
    return sorted(s[s.astype(str).str.len() > 0].unique())


# 분류 규칙 (legacy 재현)
HUMAN_ORGANISM_KEY = "homo sapiens"
# COCONUT 조인에 쓸 컬럼
COCONUT_COLS = [
    "identifier", "canonical_smiles", "standard_inchi", "standard_inchi_key",
    "molecular_weight", "molecular_formula", "np_classifier_pathway",
    "np_classifier_superclass", "np_classifier_class", "chemical_class", "organisms",
]
