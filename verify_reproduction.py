"""정규화 재현 검증 — Windows에서 normalize.py 재실행 후 이 스크립트로 대조.

사용:
    set PYTHONPATH=.
    python pipeline\\04_classify_run.py        # (선택) 분류부터 재현하려면
    python pipeline\\normalize.py               # 정규화 테이블 재생성
    python verify_reproduction.py               # 기준 지문과 대조

기준 지문(REPRODUCE_reference_fingerprints.json)은 Ubuntu에서 생성한 것.
행수 + 내용 sha256이 모두 일치하면 재현 성공.

이 지문은 값(semantic) 기준이라 OS·pandas 버전 차이에 흔들리지 않는다:
  - 휘발성 provenance 타임스탬프(created_at/classified_at/retrieved_at)는 실행마다
    값이 바뀌므로 해시에서 제외(VOLATILE_COLS). source_version 등 안정 provenance는 유지.
  - 각 셀을 플랫폼 독립 canonical 문자열로 정규화(결측→"", int/float 표준 표기).
  - 행 순서는 pandas sort_values(로케일 의존)가 아니라, 정규화한 행 문자열을
    파이썬 기본 정렬(유니코드 코드포인트, 플랫폼 무관)로 정렬해 결정.
  - to_csv(줄바꿈이 \\n vs \\r\\n) 대신 제어문자 US/RS 구분자로 직렬화.
따라서 Ubuntu와 Windows가 같은 데이터를 만들면 반드시 동일한 해시가 나온다.
"""
import pandas as pd, hashlib, json, glob, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
NORM = os.path.join(BASE, "data", "normalized")
REF = os.path.join(BASE, "REPRODUCE_reference_fingerprints.json")

# 실행시각에 찍히는 휘발성 컬럼 — 내용 해시에서 제외
VOLATILE_COLS = {"created_at", "classified_at", "retrieved_at"}
US, RS = "\x1f", "\x1e"   # unit / record separator (데이터에 없는 제어문자)

def _canon(v):
    """플랫폼·pandas 버전 독립 스칼라 문자열화. 결측→"", 정수형 float(1.0)→'1'."""
    if v is None or v is pd.NA:
        return ""
    if isinstance(v, float):
        if pd.isna(v):
            return ""
        # 1.0 처럼 정수값이면 int로 표기해 dtype 흔들림 흡수
        return str(int(v)) if v.is_integer() else repr(v)
    # numpy 불리언/정수/문자열 등은 str()로 통일 (True/False/0/1/문자열)
    return str(v)

def _row_strings(df):
    cols = [c for c in df.columns if c not in VOLATILE_COLS]
    d = df[cols]
    return [US.join(_canon(v) for v in row) for row in d.itertuples(index=False)]

def fp(df):
    """행수 + 값기준 sha256. 행 문자열을 코드포인트 순으로 정렬해 순서 의존 제거."""
    rows = sorted(_row_strings(df))
    blob = RS.join(rows)
    return len(df), hashlib.sha256(blob.encode("utf-8")).hexdigest()

def diagnose(df, name):
    """DIFFER가 났을 때 어떤 컬럼이 흔들리는지 컬럼별 부분 해시로 좁힌다."""
    cols = [c for c in df.columns if c not in VOLATILE_COLS]
    out = []
    for c in cols:
        vals = sorted(_canon(v) for v in df[c].tolist())
        h = hashlib.sha256(RS.join(vals).encode("utf-8")).hexdigest()[:12]
        out.append(f"    {c:22s} {str(df[c].dtype):18s} {h}")
    return "\n".join(out)

ref = json.load(open(REF, encoding="utf-8"))
ok = True
diffs = []
print(f"{'table':26s} {'rows':>12s}  {'content':>8s}")
print("-" * 52)
for name, exp in ref.items():
    p = os.path.join(NORM, name + ".parquet")
    if not os.path.exists(p):
        print(f"{name:26s} {'MISSING':>12s}"); ok = False; continue
    df = pd.read_parquet(p)
    n, h = fp(df)
    r_ok = (n == exp["rows"]); h_ok = (h == exp["sha256"])
    ok = ok and r_ok and h_ok
    rows = f"{n}=={exp['rows']}" if r_ok else f"{n}!={exp['rows']}"
    print(f"{name:26s} {rows:>12s}  {'MATCH' if h_ok else 'DIFFER':>8s}")
    if not h_ok:
        diffs.append(name)

print("-" * 52)
print("RESULT:", "✅ 완전 일치 — 재현 성공" if ok else "❌ 불일치 — 위 DIFFER 항목 확인")
if diffs and os.environ.get("VERIFY_DIAGNOSE"):
    print("\n[진단] 컬럼별 값 해시 (Ubuntu 기준과 대조하려면 양쪽 출력 비교):")
    for name in diffs:
        print(f"  {name}:")
        print(diagnose(pd.read_parquet(os.path.join(NORM, name + ".parquet")), name))
sys.exit(0 if ok else 1)
