"""5b단계: UniProt 단백질 주석 수집 (경로 1 + 경로 2).

경로 1 — HMDB `protein_associations`에 적힌 accession을 해석(종/리뷰상태/EC/단백질명).
경로 2 — 우리 데이터의 EC 번호를 사람·쥐 Swiss-Prot 엔트리로 되묻기.

경로 1 상세:

`build_hmdb_index.py`가 이미 HMDB `protein_associations/protein`에서 `uniprot_id`를
파싱해 `hmdb_index.json`의 `proteins[*].uniprot`에 넣어두는데, 기존 `normalize.py`는
`genes`(유전자명)만 읽고 accession을 버리고 있었다. 이 스크립트는 그 accession들을
모아 UniProt REST로 **단백질 메타데이터(생물종/리뷰상태/EC/단백질명)** 만 해석해
`.work/interim/uniprot_cache.json`에 적재한다.

왜 organism을 하드코딩하지 않는가: HMDB가 사람 중심 DB라 사실상 사람 accession이지만
전부는 아니다 — 예) A0A0K1YW63 = Apis cerana. 종을 가정하지 않고 UniProt에서 읽는다.

경로 2 상세:

EC 번호는 **반응 분류**라 종이 없다 — `1.1.1.1` 하나가 사람 ADH5/ADH1A/…와 쥐 Adh1/Adh5/…
전부를 가리킨다. UniProt 엔트리는 종이 있으므로, EC로 되물으면 효소 계층에 종 축이 생긴다.
이 프로젝트가 사람 혈청 vs 쥐 혈청/분변을 비교하는 이상 이 축이 필요하다.

EC 2,033개를 하나씩 조회하면 2,033번 요청이다. 대신 **사람+쥐 reviewed 엔트리 중 EC를 가진
것 전체를 스트림으로 한 번에 받아** 로컬에서 EC → accession 색인을 만든다(요청 1회).
부수 효과로 **비포유류 EC가 드러난다**: 우리 EC 2,033개 중 사람·쥐 효소가 있는 것은 521개
(26%)뿐이고, 나머지 1,512개는 식물·세균 효소다. 기존 kegg/brenda 컬럼은 이를 구분 없이
나열하고 있었다.

수집(네트워크) 단계와 결정론적 단계(normalize → export)의 분리는 이 저장소의 규칙이다.
따라서 normalize.py는 이 캐시를 **선택적으로** 읽는다 — 캐시가 없으면 경로 1의 uniprot_acc는
채워지되 organism/reviewed가 비고, 경로 2 행은 아예 생성되지 않는다. 네트워크 없이도
(커버리지는 줄지만) 그대로 재현된다.

사용:
    PYTHONPATH=. python pipeline/collect_uniprot.py
"""
import sys
import json
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

HMDB_INDEX = C.WORK / "interim" / "hmdb_index.json"
ENZ_CACHE = C.WORK / "interim" / "enzyme_cache.json"
BRENDA_CACHE = C.WORK / "interim" / "brenda_cache.json"
UNI_CACHE = C.WORK / "interim" / "uniprot_cache.json"

ACC_ENDPOINT = "https://rest.uniprot.org/uniprotkb/accessions"
STREAM_ENDPOINT = "https://rest.uniprot.org/uniprotkb/stream"
FIELDS = "accession,id,protein_name,gene_primary,ec,organism_name,organism_id,reviewed"
BATCH = 200          # 엔드포인트 권장 범위 내에서 보수적으로
SLEEP = 0.5          # 공개 REST 예의


def hmdb_accessions():
    """hmdb_index.json에 들어있는 고유 UniProt accession 목록."""
    idx = json.loads(HMDB_INDEX.read_text(encoding="utf-8"))
    accs = set()
    for rec in idx.values():
        for p in rec.get("proteins") or []:
            if p.get("uniprot"):
                accs.add(p["uniprot"].strip())
    return sorted(accs)


def _protein_name(entry):
    d = entry.get("proteinDescription") or {}
    for key in ("recommendedName", "submissionNames"):
        v = d.get(key)
        if isinstance(v, list):
            v = v[0] if v else None
        if v and (v.get("fullName") or {}).get("value"):
            return v["fullName"]["value"]
    return None


def _ec_numbers(entry):
    rn = (entry.get("proteinDescription") or {}).get("recommendedName") or {}
    return sorted({e["value"] for e in (rn.get("ecNumbers") or []) if e.get("value")})


def fetch(accs):
    """accession 목록 -> ({acc: {...}}, UniProt release 문자열)."""
    out, release = {}, None
    for i in range(0, len(accs), BATCH):
        chunk = accs[i:i + BATCH]
        for attempt in range(3):
            try:
                r = requests.get(ACC_ENDPOINT,
                                 params={"accessions": ",".join(chunk),
                                         "fields": FIELDS, "format": "json"},
                                 timeout=90)
                if r.status_code == 200:
                    release = release or r.headers.get("X-UniProt-Release")
                    for e in r.json().get("results", []):
                        org = e.get("organism") or {}
                        genes = e.get("genes") or [{}]
                        out[e["primaryAccession"]] = {
                            "entry_name": e.get("uniProtkbId"),
                            "protein_name": _protein_name(e),
                            "gene_name": (genes[0].get("geneName") or {}).get("value"),
                            "ec_numbers": _ec_numbers(e),
                            "organism": org.get("scientificName"),
                            "organism_id": org.get("taxonId"),
                            "reviewed": str(e.get("entryType", "")).startswith("UniProtKB reviewed"),
                        }
                    break
            except Exception:
                pass
            time.sleep(1.5 * (attempt + 1))
        print(f"  {min(i + BATCH, len(accs))}/{len(accs)} resolved={len(out)}", flush=True)
        time.sleep(SLEEP)
    return out, release


def data_ec_numbers():
    """enzyme_cache(KEGG) + brenda_cache에 등장하는 고유 EC 번호."""
    ecs = set()
    if ENZ_CACHE.exists():
        for v in json.loads(ENZ_CACHE.read_text(encoding="utf-8")).values():
            ecs |= {e.strip() for e in (v.get("kegg_ec") or []) if e and e.strip()}
    if BRENDA_CACHE.exists():
        for v in json.loads(BRENDA_CACHE.read_text(encoding="utf-8")).values():
            ecs |= {e.strip() for e in (v.get("ec_numbers") or []) if e and e.strip()}
    return sorted(ecs)


def fetch_ec_index(wanted_ecs):
    """사람+쥐 reviewed 엔트리 중 EC 보유분을 한 번에 스트림 → {ec: [엔트리, ...]}.

    EC별로 2,033번 요청하는 대신 요청 1회로 색인을 만들고 로컬에서 교집합을 취한다.
    wanted_ecs에 없는 EC는 버려서 캐시를 작게 유지한다.
    """
    want = set(wanted_ecs)
    r = requests.get(STREAM_ENDPOINT,
                     params={"query": "(organism_id:9606 OR organism_id:10090) "
                                      "AND (reviewed:true) AND (ec:*)",
                             "fields": "accession,ec,organism_id,gene_primary",
                             "format": "tsv"},
                     timeout=300)
    r.raise_for_status()
    release = r.headers.get("X-UniProt-Release")
    index, n_entries = {}, 0
    lines = r.text.splitlines()
    for line in lines[1:]:                      # 헤더 1줄 건너뜀
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        acc, ecs, taxon, gene = parts[0], parts[1], parts[2], parts[3]
        n_entries += 1
        for e in ecs.split(";"):
            e = e.strip()
            if not e or e not in want:
                continue
            index.setdefault(e, []).append({
                "acc": acc,
                "organism_id": int(taxon),
                "organism": "Homo sapiens" if taxon == "9606" else "Mus musculus",
                "gene_name": gene or None,
            })
    for e in index:
        index[e].sort(key=lambda d: (d["organism_id"], d["acc"]))
    print(f"EC 색인: 사람+쥐 reviewed 효소 엔트리 {n_entries}개 스캔 → "
          f"데이터의 EC {len(want)}개 중 {len(index)}개 매칭 "
          f"({len(want) - len(index)}개는 사람·쥐 효소 없음)")
    return index, release


def main():
    accs = hmdb_accessions()
    print(f"HMDB protein_associations 고유 accession: {len(accs)}")
    data, release = fetch(accs)
    missing = [a for a in accs if a not in data]

    # ---- 경로 2: EC → 사람/쥐 Swiss-Prot ----
    wanted = data_ec_numbers()
    print(f"\n데이터의 고유 EC: {len(wanted)}")
    ec_index, ec_release = fetch_ec_index(wanted)
    release = release or ec_release
    nonmammalian = [e for e in wanted if e not in ec_index]

    payload = {
        "_meta": {
            "source": "UniProt",
            "source_version": f"UniProt-{release}" if release else C.SOURCE_VERSIONS["UniProt"],
            "retrieved_at": C.now_iso(),
            "seeded_from": "hmdb_index.json:proteins[*].uniprot",
            "n_requested": len(accs),
            "n_resolved": len(data),
            "n_missing": len(missing),
            "missing": missing,
            # 경로 2
            "ec_query": "(organism_id:9606 OR organism_id:10090) AND (reviewed:true) AND (ec:*)",
            "ec_requested": len(wanted),
            "ec_with_mammalian_enzyme": len(ec_index),
            "ec_nonmammalian": len(nonmammalian),
        },
        "entries": data,
        "ec_index": ec_index,
        "ec_nonmammalian": sorted(nonmammalian),
    }
    UNI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    UNI_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    by_org = {}
    for v in data.values():
        by_org[v["organism"]] = by_org.get(v["organism"], 0) + 1
    n_pairs = sum(len(v) for v in ec_index.values())
    n_h = sum(1 for v in ec_index.values() for d in v if d["organism_id"] == 9606)
    print(f"\n[경로 1] resolved {len(data)} / missing {len(missing)} (폐기·병합된 accession)"
          f" / reviewed(Swiss-Prot) {sum(1 for v in data.values() if v['reviewed'])}")
    print("         organism top:", sorted(by_org.items(), key=lambda kv: -kv[1])[:5])
    print(f"[경로 2] EC {len(ec_index)}개 → accession 쌍 {n_pairs} (사람 {n_h} / 쥐 {n_pairs - n_h})"
          f" / 비포유류 EC {len(nonmammalian)}")
    print(f"-> {UNI_CACHE}")


if __name__ == "__main__":
    main()
