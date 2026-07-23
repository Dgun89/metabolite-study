"""정규화 재현 검증 — Windows에서 normalize.py 재실행 후 이 스크립트로 대조.

사용:
    set PYTHONPATH=.
    python pipeline\\04_classify_run.py        # (선택) 분류부터 재현하려면
    python pipeline\\normalize.py               # 정규화 테이블 재생성
    python verify_reproduction.py               # 기준 지문과 대조

기준 지문(REPRODUCE_reference_fingerprints.json)은 Ubuntu에서 생성한 것.
행수 + 정렬 후 내용 sha256이 모두 일치하면 재현 성공.

주의: created_at/classified_at/retrieved_at 은 파이프라인을 "언제 재실행했는가"를
기록하는 provenance 타임스탬프라 실행마다 값이 바뀐다. 데이터 재현성과 무관하므로
내용 해시에서 제외한다(VOLATILE_COLS). source_version 등 안정적 provenance는 유지.
"""
import pandas as pd, hashlib, json, glob, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
NORM = os.path.join(BASE, "data", "normalized")
REF = os.path.join(BASE, "REPRODUCE_reference_fingerprints.json")

# 실행시각에 찍히는 휘발성 컬럼 — 내용 해시에서 제외
VOLATILE_COLS = {"created_at", "classified_at", "retrieved_at"}

def _canon(v):
    """플랫폼·pandas 버전 독립적인 스칼라 문자열화. 결측은 모두 빈 문자열."""
    if v is None or v is pd.NA:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)

def fp(df):
    """행수 + 내용 sha256. to_csv(줄바꿈이 OS마다 \\n vs \\r\\n) 대신
    명시적 구분자로 직렬화해 플랫폼 독립적으로 만든다."""
    cols = [c for c in df.columns if c not in VOLATILE_COLS]
    d = df[cols].sort_values(cols, kind="stable").reset_index(drop=True)
    US, RS = "\x1f", "\x1e"          # unit / record separator (데이터에 없는 제어문자)
    blob = RS.join(US.join(_canon(v) for v in row) for row in d.itertuples(index=False))
    return len(df), hashlib.sha256(blob.encode("utf-8")).hexdigest()

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
