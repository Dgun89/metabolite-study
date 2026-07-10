"""
6단계: BRENDA 효소 수집 (SOAP, 화합물명 기반). 순차 처리 (rate limit ≤1 req/sec).
크리덴셜: 환경변수 BRENDA_EMAIL / BRENDA_PASSWORD (sha256 해시).
결과: annotation 이름 -> {ligand_id, ec_numbers} JSON 캐시.
"""
import os, json, time, hashlib
from pathlib import Path
from zeep import Client, Settings

WORK = Path("/home/dgun89/.claude-science/orgs/b775b206-ef44-477d-b8e7-a47020d337a1/workspaces/b721070f-708d-4613-b6ab-5b485695cf35")
CACHE = WORK / "interim" / "brenda_cache.json"
WSDL = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"

EMAIL = os.environ["BRENDA_EMAIL"]
PW = hashlib.sha256(os.environ["BRENDA_PASSWORD"].encode("utf-8")).hexdigest()


def make_client():
    return Client(WSDL, settings=Settings(strict=False))


def query_one(client, name):
    """화합물명 -> {ligand_id, ec_numbers}"""
    rec = {"ligand_id": None, "ec_numbers": []}
    try:
        lig = client.service.getLigandStructureIdByCompoundName(EMAIL, PW, name)
    except Exception as e:
        rec["error"] = f"ligand: {str(e)[:80]}"
        return rec
    if not lig:
        return rec
    rec["ligand_id"] = str(lig)
    try:
        res = client.service.getSubstrate(EMAIL, PW, "ecNumber*", "substrate*", "product*",
                                          "commentary*", f"ligandStructureId*{lig}")
        ecs = sorted(set(r["ecNumber"] for r in res if r["ecNumber"])) if res else []
        rec["ec_numbers"] = ecs
    except Exception as e:
        rec["error"] = f"substrate: {str(e)[:80]}"
    return rec


def main(names):
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text())
    todo = [n for n in names if n not in cache]
    print(f"전체 {len(names)} | 캐시됨 {len(names)-len(todo)} | 수집대상 {len(todo)}", flush=True)
    client = make_client()
    for i, name in enumerate(todo, 1):
        cache[name] = query_one(client, name)
        if i % 25 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False))
            matched = sum(1 for v in cache.values() if v.get("ec_numbers"))
            print(f"  {i}/{len(todo)} … (EC매칭 {matched})", flush=True)
        time.sleep(1.05)  # rate limit
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))
    matched = sum(1 for v in cache.values() if v.get("ec_numbers"))
    print(f"완료. 캐시 {len(cache)}개 | EC매칭 {matched}개 → {CACHE.name}", flush=True)
    return cache


if __name__ == "__main__":
    import pandas as pd
    h = pd.read_parquet(WORK / "interim" / "human" / "human_step4_classified.parquet")
    m = pd.read_parquet(WORK / "interim" / "mouse" / "mouse_step4_classified.parquet")
    names = pd.concat([h["annotation"], m["annotation"]]).dropna().astype(str)
    uniq = sorted(names[names.str.strip() != ""].unique())
    main(uniq)
