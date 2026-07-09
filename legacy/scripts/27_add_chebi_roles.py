#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27_add_chebi_roles.py
=====================
ChEBI ID 보유 326건에 대해 ChEBI roles 를 재조회하여
`chebi_roles` 컬럼으로 저장한다.

목적:
  - step16/26 에서 ChEBI roles 를 classification 에만 반영하고
    원문을 저장하지 않았음
  - Classification Sources 그룹에 chebi_roles 컬럼 추가로 완성도 향상

아울러 이번 step 에서 컬럼명/그룹 재구성도 함께 적용:
  - compound_origin  → classification
  - origin_evidence  → classification_basis
  - format_excel.py 의 GROUPS 도 새 구조로 업데이트 필요

의존성: pip install pandas openpyxl requests
"""

import time
import requests
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────
IN_FILE  = "metabolites_step26.xlsx"
OUT_FILE = "metabolites_step27.xlsx"

CHEBI_COL = "ChEBI"

REQUEST_DELAY = 0.35
MAX_RETRIES   = 3
MAX_ROWS      = None   # 테스트 시 정수(예: 20), 본실행 None

# ──────────────────────────────────────────────────────────────────────────
def get_roles(chebi_id: str) -> str:
    """ChEBI ID → roles 세미콜론 구분 문자열. 실패 시 빈 문자열."""
    cid = str(chebi_id).replace("CHEBI:", "").strip()
    # 숫자 아닌 값 방어
    if not cid or not cid.replace(".", "").isdigit():
        return ""
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{cid}/"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                roles_data = res.json().get('roles_classification') or []
                roles = [r['name'] for r in roles_data if isinstance(r, dict)]
                return "; ".join(roles)
            time.sleep(REQUEST_DELAY * attempt * 2)
        except Exception as e:
            print(f"  [retry {attempt}] {chebi_id}: {e}")
            time.sleep(REQUEST_DELAY * attempt * 2)
    return ""


def main():
    try:
        from format_excel import apply_format
    except ImportError:
        raise SystemExit("format_excel.py 를 찾을 수 없습니다.")

    print(f"읽는 중: {IN_FILE}")
    df = pd.read_excel(IN_FILE, sheet_name=0)
    print(f"  총 {len(df)}행")

    # ── 컬럼명 변경 ──────────────────────────────────────────────────────
    df = df.rename(columns={
        'compound_origin' : 'classification',
        'origin_evidence' : 'classification_basis',
    })
    print("  컬럼명 변경: compound_origin → classification, origin_evidence → classification_basis")

    # ── chebi_roles 컬럼 준비 ────────────────────────────────────────────
    if 'chebi_roles' not in df.columns:
        df['chebi_roles'] = pd.NA

    targets = df.index[df[CHEBI_COL].notna()].tolist()
    if MAX_ROWS:
        targets = targets[:MAX_ROWS]
    print(f"  ChEBI ID 보유 → roles 조회 대상: {len(targets)}건\n")

    found = empty = error = 0

    for n, idx in enumerate(targets, 1):
        chebi = str(df.at[idx, CHEBI_COL]).strip()
        roles = get_roles(chebi)
        time.sleep(REQUEST_DELAY)

        if roles:
            df.at[idx, 'chebi_roles'] = roles
            found += 1
        else:
            df.at[idx, 'chebi_roles'] = pd.NA
            empty += 1

        if n % 25 == 0:
            print(f"  {n}/{len(targets)}  (roles있음 {found}, 없음 {empty})")

    # ── 저장 + 3시트 재생성 ──────────────────────────────────────────────
    df.to_excel(OUT_FILE, index=False)
    apply_format(OUT_FILE)

    print("\n완료.")
    print(f"  roles 획득: {found}/{len(targets)}")
    print(f"  roles 없음: {empty}/{len(targets)}")
    print(f"  저장: {OUT_FILE}")


if __name__ == "__main__":
    main()