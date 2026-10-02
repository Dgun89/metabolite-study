"""5b단계: UniProt 단백질 주석 수집 (경로 1 — HMDB protein_associations 기반).

`build_hmdb_index.py`가 이미 HMDB `protein_associations/protein`에서 `uniprot_id`를
파싱해 `hmdb_index.json`의 `proteins[*].uniprot`에 넣어두는데, 기존 `normalize.py`는
`genes`(유전자명)만 읽고 accession을 버리고 있었다. 이 스크립트는 그 accession들을
모아 UniProt REST로 **단백질 메타데이터(생물종/리뷰상태/EC/단백질명)** 만 해석해
`.work/interim/uniprot_cache.json`에 적재한다.

왜 organism을 하드코딩하지 않는가: HMDB가 사람 중심 DB라 사실상 사람 accession이지만
전부는 아니다 — 예) A0A0K1YW63 = Apis cerana. 종을 가정하지 않고 UniProt에서 읽는다.

수집(네트워크) 단계와 결정론적 단계(normalize → export)의 분리는 이 저장소의 규칙이다.
따라서 normalize.py는 이 캐시를 **선택적으로** 읽는다 — 캐시가 없으면 uniprot_acc는
채워지되 organism/reviewed가 비는 것일 뿐, 네트워크 없이도 그대로 재현된다.

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
UNI_CACHE = C.WORK / "interim" / "uniprot_cache.json"

ACC_ENDPOINT = "https://rest.uniprot.org/uniprotkb/accessions"
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


def main():
    accs = hmdb_accessions()
    print(f"HMDB protein_associations 고유 accession: {len(accs)}")
    data, release = fetch(accs)
    missing = [a for a in accs if a not in data]
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
        },
        "entries": data,
    }
    UNI_CACHE.parent.mkdir(parents=True, exist_ok=True)
    UNI_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    by_org = {}
    for v in data.values():
        by_org[v["organism"]] = by_org.get(v["organism"], 0) + 1
    print(f"resolved {len(data)} / missing {len(missing)} (폐기·병합된 accession)")
    print(f"reviewed(Swiss-Prot) {sum(1 for v in data.values() if v['reviewed'])}")
    print("organism top:", sorted(by_org.items(), key=lambda kv: -kv[1])[:6])
    print(f"-> {UNI_CACHE}")


if __name__ == "__main__":
    main()
