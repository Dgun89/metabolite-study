"""정규화 재현 검증 — Windows에서 normalize.py 재실행 후 이 스크립트로 대조.

사용:
    set PYTHONPATH=.
    python pipeline\\04_classify_run.py        # (선택) 분류부터 재현하려면
    python pipeline\\normalize.py               # 정규화 테이블 재생성
    python verify_reproduction.py               # 기준 지문과 대조

기준 지문(REPRODUCE_reference_fingerprints.json)은 Ubuntu에서 생성한 것.
행수 + 정렬 후 내용 sha256이 모두 일치하면 재현 성공.
"""
import pandas as pd, hashlib, json, glob, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
NORM = os.path.join(BASE, "data", "normalized")
REF = os.path.join(BASE, "REPRODUCE_reference_fingerprints.json")

def fp(df):
    d = df.sort_values(list(df.columns)).reset_index(drop=True)
    return len(df), hashlib.sha256(d.to_csv(index=False).encode()).hexdigest()

ref = json.load(open(REF, encoding="utf-8"))
ok = True
print(f"{'table':26s} {'rows':>12s}  {'content':>8s}")
print("-" * 52)
for name, exp in ref.items():
    p = os.path.join(NORM, name + ".parquet")
    if not os.path.exists(p):
        print(f"{name:26s} {'MISSING':>12s}"); ok = False; continue
    n, h = fp(pd.read_parquet(p))
    r_ok = (n == exp["rows"]); h_ok = (h == exp["sha256"])
    ok = ok and r_ok and h_ok
    rows = f"{n}=={exp['rows']}" if r_ok else f"{n}!={exp['rows']}"
    print(f"{name:26s} {rows:>12s}  {'MATCH' if h_ok else 'DIFFER':>8s}")

print("-" * 52)
print("RESULT:", "✅ 완전 일치 — 재현 성공" if ok else "❌ 불일치 — 위 DIFFER 항목 확인")
sys.exit(0 if ok else 1)
