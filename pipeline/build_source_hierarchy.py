"""
HMDB 'Disposition > Source' 서브트리의 계층 맵 생성기.

data/reference/hmdb_metabolites.xml(raw)을 스트리밍으로 1회 훑어, Source 노드
아래의 모든 term에 대해 (최상위 버킷, 트리 깊이, 경로)를 뽑아
data/reference/hmdb_source_hierarchy.json 으로 저장한다.

이 맵은 normalize.py가 compound_origins의 HMDB 기원 라벨을 6개 최상위 버킷
(Endogenous / Food / Biological / Synthetic / Environmental / Exogenous)으로
roll-up 주석할 때 참조한다. 즉 평평한 origin_label을 항해 가능한 계층으로 정리.

주의: 이 맵은 metabolite 개수와 무관한 '온톨로지 정의' 자체다(라벨 카운트가 아님).
전체 스캔이지만 term의 부모-자식 정의만 모으므로 결과는 결정적이다.

사용:
    python pipeline/build_source_hierarchy.py
    # 대안(빠름): 이미 만든 온톨로지 트리에서 파생
    python pipeline/build_source_hierarchy.py --from-tree .work/interim/hmdb_ontology_tree.json
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

NS = "{http://www.hmdb.ca}"
SOURCE_TERM = "Source"


def _node_term(desc):
    t = desc.find(NS + "term")
    return t.text if t is not None else None


def _children_container(desc):
    return desc.find(NS + "descendants")


def collect_edges_from_xml(xml_path, progress=50000):
    """XML 스트리밍으로 Source 서브트리의 parent_term -> child_term 엣지 집합 수집."""
    from lxml import etree
    edges = set()          # (parent_term, child_term)
    direct_children = set()  # Source 직속 자식 = 최상위 버킷
    n = 0

    def walk_source(desc_container, parent_term, is_source_root):
        """desc_container = <descendants>; 그 아래 <descendant>들을 순회."""
        if desc_container is None:
            return
        for child in desc_container.findall(NS + "descendant"):
            ct = _node_term(child)
            if not ct:
                continue
            edges.add((parent_term, ct))
            if is_source_root:
                direct_children.add(ct)
            walk_source(_children_container(child), ct, False)

    ctx = etree.iterparse(xml_path, events=("end",), tag=NS + "metabolite")
    for _, el in ctx:
        n += 1
        ont = el.find(NS + "ontology")
        if ont is not None:
            for root in ont.findall(NS + "root"):
                if _node_term(root) != "Disposition":
                    continue
                # Source 노드 찾기
                for desc in root.iter(NS + "descendant"):
                    if _node_term(desc) == SOURCE_TERM:
                        walk_source(_children_container(desc), SOURCE_TERM, True)
                        break
        el.clear()
        while el.getprevious() is not None:
            del el.getparent()[0]
        if n % progress == 0:
            print(f"  scanned {n} | edges {len(edges)}", flush=True)
    del ctx
    print(f"  총 {n} metabolites, Source 엣지 {len(edges)}, 최상위 버킷 {len(direct_children)}")
    return edges, direct_children


def collect_edges_from_tree(tree_path):
    """explore_hmdb.py가 만든 온톨로지 트리 JSON에서 Source 서브트리 엣지 파생(빠름)."""
    tree = json.loads(Path(tree_path).read_text())

    def find(node, target):
        if node["term"] == target:
            return node
        for c in node.get("children", []):
            r = find(c, target)
            if r:
                return r
        return None

    disp = next(r for r in tree["roots"] if r["term"] == "Disposition")
    source = find(disp, SOURCE_TERM)
    edges = set()
    direct_children = {c["term"] for c in source.get("children", [])}

    def walk(node):
        for c in node.get("children", []):
            edges.add((node["term"], c["term"]))
            walk(c)
    walk(source)
    print(f"  트리에서 Source 엣지 {len(edges)}, 최상위 버킷 {len(direct_children)}")
    return edges, direct_children


def build_hierarchy(edges, direct_children):
    """엣지 집합 → term별 {top_bucket, level, path}. Source=level0."""
    from collections import defaultdict, deque
    children_of = defaultdict(list)
    for p, c in edges:
        children_of[p].append(c)

    hierarchy = {}
    # BFS from Source; 직속 자식은 자기 자신이 버킷
    q = deque()
    for b in sorted(direct_children):
        hierarchy[b] = {"top_bucket": b, "level": 1, "path": ["Source", b]}
        q.append(b)
    seen = set(direct_children)
    while q:
        cur = q.popleft()
        bucket = hierarchy[cur]["top_bucket"]
        lvl = hierarchy[cur]["level"]
        path = hierarchy[cur]["path"]
        for ch in children_of.get(cur, []):
            if ch in seen:      # polyhierarchy 사이클/재방문 가드
                continue
            seen.add(ch)
            hierarchy[ch] = {"top_bucket": bucket, "level": lvl + 1, "path": path + [ch]}
            q.append(ch)
    return hierarchy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-tree", default=None,
                    help="온톨로지 트리 JSON에서 파생(전체 XML 재스캔 생략)")
    ap.add_argument("--out", default=None, help="출력 경로(기본 data/reference/hmdb_source_hierarchy.json)")
    args = ap.parse_args()

    if args.from_tree:
        edges, direct = collect_edges_from_tree(args.from_tree)
    else:
        xml = C.REF / "hmdb_metabolites.xml"
        if not xml.exists():
            raise SystemExit(f"HMDB XML 없음: {xml}")
        edges, direct = collect_edges_from_xml(str(xml))

    hierarchy = build_hierarchy(edges, direct)
    out_path = Path(args.out) if args.out else (C.REF / "hmdb_source_hierarchy.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "hmdb_version": C.hmdb_version(),
            "root": "Disposition > Source",
            "top_buckets": sorted(direct),
            "n_terms": len(hierarchy),
            "retrieved_at": C.now_iso(),
            "generated_by": "pipeline/build_source_hierarchy.py",
        },
        "terms": {t: {"top_bucket": v["top_bucket"], "level": v["level"],
                      "path": " > ".join(v["path"])}
                  for t, v in sorted(hierarchy.items())},
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"저장: {out_path} ({len(hierarchy)} terms, 버킷 {sorted(direct)})")


if __name__ == "__main__":
    main()
