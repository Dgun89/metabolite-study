"""
5단계: 효소 정보 수집 (KEGG EC + Reactome catalyst). HMDB gene은 인덱스에서 조인.
InChIKey 기반 캐시. kegg_id / chebi_id는 3단계 identifier_cache에서 가져옴.
"""
import json, time, requests
from pathlib import Path

WORK = Path("/home/dgun89/.claude-science/orgs/b775b206-ef44-477d-b8e7-a47020d337a1/workspaces/b721070f-708d-4613-b6ab-5b485695cf35")
ID_CACHE = WORK / "interim" / "identifier_cache.json"
ENZ_CACHE = WORK / "interim" / "enzyme_cache.json"

import threading as _th
_local = _th.local()

class _SessProxy:
    def _s(self):
        s = getattr(_local, "sess", None)
        if s is None:
            s = requests.Session()
            _local.sess = s
        return s
    def get(self, *a, **k):
        return self._s().get(*a, **k)

SESS = _SessProxy()

KEGG_LINK = "https://rest.kegg.jp/link/enzyme/cpd:{kid}"
REACTOME_MAP = "https://reactome.org/ContentService/data/mapping/ChEBI/{cid}/reactions"
REACTOME_QUERY = "https://reactome.org/ContentService/data/query/{stid}"


def kegg_ec(kegg_id):
    """KEGG compound id -> [EC, ...]"""
    if not kegg_id:
        return []
    kid = kegg_id.replace("cpd:", "")
    for a in range(3):
        try:
            r = SESS.get(KEGG_LINK.format(kid=kid), timeout=20)
            if r.status_code == 200:
                ecs = []
                for line in r.text.strip().splitlines():
                    parts = line.split("\t")
                    if len(parts) == 2:
                        ecs.append(parts[1].replace("ec:", ""))
                return sorted(set(ecs))
            if r.status_code == 404:
                return []
        except Exception:
            pass
        time.sleep(1.0 * (a + 1))
    return []


def reactome_catalysts(chebi_id):
    """ChEBI id -> [catalyst displayName, ...]"""
    if not chebi_id:
        return []
    cid = str(chebi_id).replace("CHEBI:", "")
    try:
        r = SESS.get(REACTOME_MAP.format(cid=cid), timeout=20)
        if r.status_code != 200:
            return []
        reactions = r.json()
    except Exception:
        return []
    cats = []
    for rx in reactions[:15]:  # 과도한 호출 방지
        stid = rx.get("stId")
        if not stid:
            continue
        try:
            q = SESS.get(REACTOME_QUERY.format(stid=stid), timeout=20)
            if q.status_code == 200:
                for ca in (q.json().get("catalystActivity") or []):
                    dn = ca.get("displayName")
                    if dn:
                        cats.append(dn)
        except Exception:
            pass
        time.sleep(0.2)
    return sorted(set(cats))


def collect_one(ik, id_rec):
    kegg_id = id_rec.get("kegg_id")
    chebi_id = id_rec.get("chebi_id")
    return {
        "InChIKey": ik,
        "kegg_ec": kegg_ec(kegg_id),
        "reactome_catalysts": reactome_catalysts(chebi_id),
    }


def main(inchikeys):
    id_cache = json.loads(ID_CACHE.read_text())
    cache = {}
    if ENZ_CACHE.exists():
        cache = json.loads(ENZ_CACHE.read_text())
    todo = [ik for ik in inchikeys if ik not in cache and ik in id_cache]
    print(f"전체 {len(inchikeys)} | 캐시됨 {len(cache)} | 수집대상 {len(todo)}", flush=True)
    for i, ik in enumerate(todo, 1):
        cache[ik] = collect_one(ik, id_cache[ik])
        if i % 25 == 0:
            ENZ_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
            print(f"  {i}/{len(todo)} …", flush=True)
        time.sleep(0.3)
    ENZ_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    print(f"완료. 캐시 {len(cache)}개 → {ENZ_CACHE.name}", flush=True)
    return cache


def main_parallel(inchikeys, workers=6):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    id_cache = json.loads(ID_CACHE.read_text())
    cache = {}
    if ENZ_CACHE.exists():
        cache = json.loads(ENZ_CACHE.read_text())
    # kegg_id 또는 chebi_id가 있는 것만 수집 대상 (없으면 효소 조회 불가)
    todo = [ik for ik in inchikeys if ik not in cache and ik in id_cache
            and (id_cache[ik].get("kegg_id") or id_cache[ik].get("chebi_id"))]
    print(f"전체 {len(inchikeys)} | 캐시됨 {len(cache)} | 수집대상 {len(todo)} | workers={workers}", flush=True)
    lock = threading.Lock(); done = [0]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(collect_one, ik, id_cache[ik]): ik for ik in todo}
        for fut in as_completed(futs):
            ik = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"InChIKey": ik, "kegg_ec": [], "reactome_catalysts": [], "error": str(e)[:100]}
            with lock:
                cache[ik] = rec; done[0] += 1
                if done[0] % 25 == 0:
                    ENZ_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
                    print(f"  {done[0]}/{len(todo)} …", flush=True)
    ENZ_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    print(f"완료. 캐시 {len(cache)}개 → {ENZ_CACHE.name}", flush=True)
    return cache


if __name__ == "__main__":
    import pandas as pd
    h = pd.read_parquet(WORK / "interim" / "human" / "human_step2_coconut.parquet")
    m = pd.read_parquet(WORK / "interim" / "mouse" / "mouse_step2_coconut.parquet")
    iks = sorted(pd.concat([h["InChIKey"], m["InChIKey"]]).dropna().unique())
    main_parallel(iks)
