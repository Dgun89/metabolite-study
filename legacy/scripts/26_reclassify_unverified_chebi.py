#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
26_reclassify_unverified_chebi.py
==================================
metabolites_step25.xlsx 의 'unverified'(476건)를 ChEBI roles 로 재분류.

step16 과의 차이:
  - 전체 902행이 아닌 unverified 476건만 타깃
  - ChEBI ID 이미 있는 31건 → roles 조회 바로 진행 (InChIKey 검색 생략)
  - InChIKey 있는 나머지 → InChIKey → ChEBI ID → roles
  - origin_evidence 컬럼 업데이트
  - 저장 후 format_excel.apply_format() 으로 3시트 유지

분류 규칙 (step16 과 동일, 관점 B):
  roles 에 "human metabolite" 포함 → endogenous
  roles 있으나 human metabolite 없음 → exogenous
  ChEBI 미발견 / roles 없음 → unverified 유지

의존성: pip install pandas openpyxl requests
"""

import time
import requests
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────
IN_FILE  = "metabolites_step25.xlsx"
OUT_FILE = "metabolites_step26.xlsx"

CLASS_COL        = "compound_origin"
UNVERIFIED_VALUE = "unverified"
INCHIKEY_COL     = "InChIKey"
CHEBI_COL        = "ChEBI"

REQUEST_DELAY = 0.35
MAX_RETRIES   = 3
MAX_ROWS      = None   # 테스트 시 정수(예: 20), 본실행 None

# ──────────────────────────────────────────────────────────────────────────
# ChEBI API
# ──────────────────────────────────────────────────────────────────────────
def get_chebi_id(inchikey: str) -> str:
    """InChIKey → ChEBI ID. 못 찾으면 빈 문자열."""
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?term={inchikey}&size=5&page=1"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('results'):
                    return str(data['results'][0]['_id'])
                return ""
            time.sleep(REQUEST_DELAY * attempt * 2)
        except Exception as e:
            print(f"  [search retry {attempt}] {e}")
            time.sleep(REQUEST_DELAY * attempt * 2)
    return ""


def get_roles(chebi_id: str) -> list:
    """ChEBI ID → roles_classification 리스트. 실패 시 빈 리스트."""
    # ChEBI ID 앞 'CHEBI:' 제거
    cid = str(chebi_id).replace("CHEBI:", "").strip()
    url = f"https://www.ebi.ac.uk/chebi/backend/api/public/compound/{cid}/"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return [r['name'] for r in res.json().get('roles_classification', [])]
            time.sleep(REQUEST_DELAY * attempt * 2)
        except Exception as e:
            print(f"  [roles retry {attempt}] {e}")
            time.sleep(REQUEST_DELAY * attempt * 2)
    return []


# ──────────────────────────────────────────────────────────────────────────
def main():
    try:
        from format_excel import apply_format
    except ImportError:
        raise SystemExit("format_excel.py 를 찾을 수 없습니다.")

    print(f"읽는 중: {IN_FILE}")
    df = pd.read_excel(IN_FILE, sheet_name=0)
    df['ChEBI'] = df['ChEBI'].astype(object)
    print(f"  총 {len(df)}행")

    mask = (df[CLASS_COL].astype(str).str.strip().str.lower()
            == UNVERIFIED_VALUE.lower())
    targets = df.index[mask].tolist()
    if MAX_ROWS:
        targets = targets[:MAX_ROWS]
    print(f"  처리 대상(unverified): {len(targets)}건\n")

    n_endo = n_exo = n_keep = 0

    for n, idx in enumerate(targets, 1):
        name     = df.at[idx, 'compound_name']
        inchikey = df.at[idx, INCHIKEY_COL]
        chebi    = df.at[idx, CHEBI_COL]

        chebi_id  = ""
        from_col  = False

        # 1) 이미 ChEBI ID 있으면 바로 사용
        if pd.notna(chebi) and str(chebi).strip():
            chebi_id = str(chebi).strip()
            from_col = True
        # 2) InChIKey → ChEBI ID 검색
        elif pd.notna(inchikey) and str(inchikey).strip():
            chebi_id = get_chebi_id(str(inchikey).strip())
            time.sleep(REQUEST_DELAY)

        if not chebi_id:
            df.at[idx, 'origin_evidence'] = "ChEBI: not found"
            n_keep += 1
            if n % 25 == 0:
                print(f"  {n}/{len(targets)}  (→endo {n_endo}, →exo {n_exo}, 유지 {n_keep})")
            continue

        # ChEBI ID 새로 찾았으면 컬럼 업데이트
        if not from_col:
            df.at[idx, CHEBI_COL] = f"CHEBI:{chebi_id}"

        roles = get_roles(chebi_id)
        time.sleep(REQUEST_DELAY)

        if not roles:
            df.at[idx, 'origin_evidence'] = f"ChEBI: no roles ({chebi_id})"
            n_keep += 1
        elif "human metabolite" in roles:
            df.at[idx, CLASS_COL]       = "endogenous"
            df.at[idx, 'origin_evidence'] = f"ChEBI: human metabolite ({chebi_id})"
            n_endo += 1
        else:
            df.at[idx, CLASS_COL]       = "exogenous"
            df.at[idx, 'origin_evidence'] = f"ChEBI: non-human roles ({chebi_id})"
            n_exo += 1

        if n % 25 == 0:
            print(f"  {n}/{len(targets)}  (→endo {n_endo}, →exo {n_exo}, 유지 {n_keep})")

    # 저장 + 3시트 재생성
    df.to_excel(OUT_FILE, index=False)
    apply_format(OUT_FILE)

    print("\n완료.")
    print(f"  unverified {len(targets)}건 중:")
    print(f"    → endogenous : {n_endo}")
    print(f"    → exogenous  : {n_exo}")
    print(f"    → 유지       : {n_keep}")
    print(f"  남은 unverified: {len(targets) - n_endo - n_exo}")
    print(f"  저장: {OUT_FILE}")


if __name__ == "__main__":
    main()