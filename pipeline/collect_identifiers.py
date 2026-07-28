"""
3단계: identifier 교차수집 (InChIKey 기반, 캐시).
UniChem(xref 한 번에) + ChEBI detail(roles, KEGG/HMDB accession) + PubChem(CID 폴백).
결과를 InChIKey→dict JSON 캐시로 저장.
"""
import sys, json, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

CACHE = C.WORK / "interim" / "identifier_cache.json"
import threading as _th
_local = _th.local()

class _SessProxy:
    """스레드별 requests.Session 제공 (thread-safe)."""
    def _s(self):
        s = getattr(_local, "sess", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"Accept": "application/json"})
            _local.sess = s
        return s
    def get(self, *a, **k):
        return self._s().get(*a, **k)
    def post(self, *a, **k):
        return self._s().post(*a, **k)

SESS = _SessProxy()

UNICHEM_URL = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
CHEBI_SEARCH = "https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={ik}&size=5&page=1"
CHEBI_DETAIL = "https://www.ebi.ac.uk/chebi/backend/api/public/compound/{cid}/"
PUBCHEM_CID = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{ik}/cids/JSON"


def _get(url, **kw):
    for a in range(3):
        try:
            r = SESS.get(url, timeout=20, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(1.5 * (a + 1))
    return None


def unichem_sources(ik):
    """InChIKey -> {shortName: compoundId, ...}"""
    out = {}
    for a in range(3):
        try:
            r = SESS.post(UNICHEM_URL, json={"type": "inchikey", "compound": ik}, timeout=20)
            if r.status_code == 200:
                comps = r.json().get("compounds", [])
                if comps:
                    for s in comps[0].get("sources", []):
                        # 소스별 첫 값 유지
                        out.setdefault(s.get("shortName"), s.get("compoundId"))
                return out
            if r.status_code == 404:
                return out
        except Exception:
            pass
        time.sleep(1.5 * (a + 1))
    return out


def chebi_search(ik):
    r = _get(CHEBI_SEARCH.format(ik=ik))
    if not r:
        return None
    res = r.json().get("results", [])
    if not res:
        return None
    acc = res[0].get("_source", {}).get("chebi_accession", "")
    # "CHEBI:88429" -> "88429"
    return acc.split(":")[-1] if acc else res[0].get("_id")


def chebi_detail(chebi_id):
    r = _get(CHEBI_DETAIL.format(cid=chebi_id))
    if not r:
        return {}
    j = r.json()
    roles = [x.get("name") for x in (j.get("roles_classification") or []) if x.get("name")]
    kegg, hmdb = None, None
    xrefs = j.get("database_accessions", {})
    manual = xrefs.get("MANUAL_X_REF", []) if isinstance(xrefs, dict) else []
    for x in manual:
        sn = x.get("source_name")
        if sn == "KEGG COMPOUND" and not kegg:
            kegg = x.get("accession_number")
        elif sn == "HMDB" and not hmdb:
            hmdb = x.get("accession_number")
    return {"chebi_roles": roles, "chebi_kegg": kegg, "chebi_hmdb": hmdb}


def pubchem_cid(ik):
    r = _get(PUBCHEM_CID.format(ik=ik))
    if not r:
        return None
    cids = r.json().get("IdentifierList", {}).get("CID", [])
    return str(cids[0]) if cids else None


def collect_one(ik):
    # inchikey(소문자) 표준 컬럼 + InChIKey 하위호환 별칭 둘 다 기록
    rec = {"inchikey": ik, "InChIKey": ik}
    src = unichem_sources(ik)
    rec["unichem"] = src
    rec["hmdb_id"] = src.get("hmdb")
    rec["kegg_id"] = src.get("kegg")
    rec["chebi_id"] = (src.get("chebi") or "").replace("CHEBI:", "") or None
    rec["pubchem_cid"] = src.get("pubchem")
    # ChEBI id 없으면 검색
    if not rec["chebi_id"]:
        rec["chebi_id"] = chebi_search(ik)
    # ChEBI detail (roles + KEGG/HMDB 보강)
    if rec["chebi_id"]:
        d = chebi_detail(rec["chebi_id"])
        rec.update(d)
        rec["kegg_id"] = rec["kegg_id"] or d.get("chebi_kegg")
        rec["hmdb_id"] = rec["hmdb_id"] or d.get("chebi_hmdb")
    else:
        rec["chebi_roles"] = []
    # PubChem CID 폴백
    if not rec["pubchem_cid"]:
        rec["pubchem_cid"] = pubchem_cid(ik)
    # provenance: 어떤 소스들에서 언제 수집했는지
    used = ["UniChem"]
    if rec.get("chebi_id"):
        used.append("ChEBI")
    if rec.get("pubchem_cid"):
        used.append("PubChem")
    rec["source"] = "+".join(used)
    rec["source_version"] = ";".join(C.SOURCE_VERSIONS[s] for s in used)
    rec["retrieved_at"] = C.now_iso()
    return rec


def main(inchikeys):
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    todo = [ik for ik in inchikeys if ik not in cache]
    print(f"전체 {len(inchikeys)} | 캐시됨 {len(inchikeys)-len(todo)} | 수집대상 {len(todo)}", flush=True)
    for i, ik in enumerate(todo, 1):
        cache[ik] = collect_one(ik)
        if i % 25 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(todo)} …", flush=True)
        time.sleep(0.34)  # KEGG/ChEBI rate 매너
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"완료. 캐시 {len(cache)}개 → {CACHE.name}", flush=True)
    return cache


def main_parallel(inchikeys, workers=6):
    """병렬 수집. 캐시된 것은 스킵, 주기적 저장."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    todo = [ik for ik in inchikeys if ik not in cache]
    print(f"전체 {len(inchikeys)} | 캐시됨 {len(inchikeys)-len(todo)} | 수집대상 {len(todo)} | workers={workers}", flush=True)
    lock = threading.Lock()
    done = [0]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(collect_one, ik): ik for ik in todo}
        for fut in as_completed(futs):
            ik = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"inchikey": ik, "InChIKey": ik, "error": str(e)[:100],
                       "retrieved_at": C.now_iso()}
            with lock:
                cache[ik] = rec
                done[0] += 1
                if done[0] % 50 == 0:
                    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                    print(f"  {done[0]}/{len(todo)} …", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"완료. 캐시 {len(cache)}개 → {CACHE.name}", flush=True)
    return cache


if __name__ == "__main__":
    # 세 종(human/mouse/legacy) step2의 고유 InChIKey를 한 번에 수집(캐시 공유).
    iks = C.all_inchikeys()
    mode = sys.argv[1] if len(sys.argv) > 1 else "parallel"
    if mode == "parallel":
        main_parallel(iks)
    else:
        main(iks)
