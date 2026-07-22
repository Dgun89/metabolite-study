"""
HMDB 6.1GB XML을 한 번 스트리밍하여 InChIKey -> {source(endo/exo), genes, accession} 인덱스 구축.
우리 InChIKey 집합에 해당하는 레코드만 저장.
"""
import sys, json
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

HMDB_XML = C.HMDB_XML
OUT = C.WORK / "interim" / "hmdb_index.json"
NS = "{http://www.hmdb.ca}"


def tag(e):
    return e.tag.replace(NS, "")


def parse_metabolite(elem):
    """<metabolite> 요소 -> dict"""
    rec = {"accession": None, "inchikey": None, "kegg_id": None, "chebi_id": None,
           "hmdb_source": [], "genes": [], "proteins": [], "biospecimens": []}
    # 직접 자식만 (secondary_accessions 안의 accession 제외 위해 첫 accession만)
    for child in elem:
        t = tag(child)
        if t == "accession" and rec["accession"] is None:
            rec["accession"] = child.text
        elif t == "inchikey":
            rec["inchikey"] = child.text
        elif t == "kegg_id":
            rec["kegg_id"] = child.text
        elif t == "chebi_id":
            rec["chebi_id"] = child.text
        elif t == "ontology":
            # Disposition > Source > term(Endogenous/Exogenous/...) 추출
            rec["hmdb_source"] = extract_sources(child)
        elif t == "protein_associations":
            for prot in child:
                name = gene = uni = None
                for pc in prot:
                    pt = tag(pc)
                    if pt == "name": name = pc.text
                    elif pt == "gene_name": gene = pc.text
                    elif pt == "uniprot_id": uni = pc.text
                if gene:
                    rec["genes"].append(gene)
                if name:
                    rec["proteins"].append({"name": name, "gene": gene, "uniprot": uni})
    # biospecimen_locations는 biological_properties 아래 중첩 → iter로 탐색
    bl = elem.find(f"{NS}biological_properties/{NS}biospecimen_locations")
    if bl is not None:
        rec["biospecimens"] = [b.text for b in bl if b.text]
    return rec


def extract_sources(ontology_elem):
    """ontology 트리에서 parent 'Source' 아래 term 텍스트 수집 (Endogenous 등)."""
    sources = []
    # 재귀: term 텍스트가 'Source'인 노드를 찾고 그 하위 descendant의 term 수집
    for term_el in ontology_elem.iter(f"{NS}term"):
        if term_el.text == "Source":
            # 형제/부모 구조: Source term은 <term> 안, 그 컨테이너의 descendants에서 term 수집
            parent = term_el.getparent()  # <term_root> 컨테이너
            if parent is not None:
                for sub in parent.iter(f"{NS}term"):
                    if sub.text and sub.text != "Source":
                        sources.append(sub.text)
    return sorted(set(sources))


def main(target_inchikeys):
    targets = set(target_inchikeys)
    index = {}
    n_seen = 0
    ctx = etree.iterparse(str(HMDB_XML), events=("end",), tag=f"{NS}metabolite")
    for _, elem in ctx:
        n_seen += 1
        # inchikey 먼저 싸게 확인
        ik_el = elem.find(f"{NS}inchikey")
        ik = ik_el.text if ik_el is not None else None
        if ik and ik in targets:
            rec = parse_metabolite(elem)
            rec["source"] = "HMDB"
            rec["source_version"] = C.hmdb_version()
            rec["retrieved_at"] = C.now_iso()
            index[ik] = rec
        # 메모리 정리
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
        if n_seen % 50000 == 0:
            print(f"  scanned {n_seen} metabolites, matched {len(index)}", flush=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False))
    print(f"완료. 스캔 {n_seen} | 매칭 {len(index)} → {OUT.name}", flush=True)
    return index


if __name__ == "__main__":
    # 세 종(human/mouse/legacy) step2의 고유 InChIKey에 해당하는 HMDB 레코드만 인덱싱.
    iks = C.all_inchikeys()
    main(iks)
