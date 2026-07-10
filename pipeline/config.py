"""
공통 파이프라인 설정 — SPECIES 전환으로 human/mouse 처리.

사용법:
    from pipeline.config import get_paths
    P = get_paths("human")   # 또는 "mouse"
"""
from pathlib import Path

BASE = Path("/home/dgun89/repos/metabolite-study")
# 산출물은 저장소가 read-only이므로 workspace에 빌드 후 사용자가 final/로 복사
WORK = Path("/home/dgun89/.claude-science/orgs/b775b206-ef44-477d-b8e7-a47020d337a1/workspaces/b721070f-708d-4613-b6ab-5b485695cf35")

REF = BASE / "data" / "reference"
COCONUT_CSV = REF / "coconut_complete.csv"
HMDB_XML = REF / "hmdb_metabolites.xml"

RAW_FILES = {
    "human": BASE / "data" / "human" / "raw" / "annotation_output_hito.xlsx",
    "mouse": BASE / "data" / "mouse" / "raw" / "annotation_output_mouse.xlsx",
}

def get_paths(species: str) -> dict:
    assert species in ("human", "mouse"), f"unknown species: {species}"
    interim = WORK / "interim" / species
    final = WORK / "final" / species
    interim.mkdir(parents=True, exist_ok=True)
    final.mkdir(parents=True, exist_ok=True)
    return {
        "species": species,
        "raw": RAW_FILES[species],
        "interim": interim,
        "final": final,
        "coconut_csv": COCONUT_CSV,
        "hmdb_xml": HMDB_XML,
    }

# 분류 규칙 (legacy 재현)
HUMAN_ORGANISM_KEY = "homo sapiens"
# COCONUT 조인에 쓸 컬럼
COCONUT_COLS = [
    "identifier", "canonical_smiles", "standard_inchi", "standard_inchi_key",
    "molecular_weight", "molecular_formula", "np_classifier_pathway",
    "np_classifier_superclass", "np_classifier_class", "chemical_class", "organisms",
]
