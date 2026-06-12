#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
28_reclassify_via_kegg_hmdb_chebi.py
=====================================
unverified 중 'ChEBI: not found' 인 행에서
KEGG ID → KEGG API → ChEBI ID
HMDB ID → UniChem API → ChEBI ID
로 ChEBI ID 를 새로 찾아 roles 조회 후 classification 업데이트.

대상: KEGG 8건 + HMDB 5건 (중복 포함 11건)
"""

import time
import requests
import pandas as pd

# ──────────────────────────────────────────────────────────────────────────
IN_FILE  = "metabolites_step27.xlsx"
OUT_FILE = "metabolites_step28.xlsx"

REQUEST_DELAY = 0.35
MAX_RETRIES   = 3

# ──────────────────────────────────────────────────────────────────────────
def get_chebi_from_kegg(kegg_id: str) -> str:
    """KEGG ID → ChEBI ID. KEGG DB link API 사용."""
    url = f"https://rest.kegg.jp/link/chebi/{kegg_id}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200 and res.text.strip():
            # 응답 형식: "cpd:C07708\tchebi:15422"
            for line in res.text.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) == 2 and "chebi:" in parts[1].lower():
                    return parts[1].strip().replace("chebi:", "").strip()
    except Exception as e:
        print(f"  [KEGG→ChEBI error] {kegg_id}: {e}")
    return ""


def get_chebi_from_hmdb(hmdb_id: str) -> str:
    """HMDB ID → ChEBI ID. UniChem API 사용."""
    # UniChem: HMDB source ID = 2, ChEBI source ID = 7
    hmdb_clean = hmdb_id.replace("HMDB", "").lstrip("0")
    url = f"https://www.ebi.ac.uk/unichem/rest/src_compound_id/{hmdb_clean}/2/7"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list):
                return str(data[0].get("src_compound_id", ""))
    except Exception as e:
        print(f"  [HMDB→ChEBI error] {hmdb_id}: {e}")
    return ""


def get_roles(chebi_id: str) -> str:
    """ChEBI ID → roles 세미콜론 문자열."""
    cid = str(chebi_id).replace("CHEBI:", "").strip()
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
            print(f"  [roles retry {attempt}] {chebi_id}: {e}")
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

    # 대상: unverified + ChEBI not found + KEGG 또는 HMDB 있는 행
    mask = (
        (df['classification'] == 'unverified') &
        (df['classification_basis'] == 'ChEBI: not found') &
        (df['KEGG'].notna() | df['HMDB'].notna())
    )
    targets = df.index[mask].tolist()
    print(f"  처리 대상: {len(targets)}건\n")

    # ChEBI 컬럼 타입 보정
    df['ChEBI'] = df['ChEBI'].astype(object)
    if 'chebi_roles' not in df.columns:
        df['chebi_roles'] = pd.NA
    df['chebi_roles'] = df['chebi_roles'].astype(object)

    n_endo = n_exo = n_keep = 0

    for idx in targets:
        name  = df.at[idx, 'compound_name']
        kegg  = df.at[idx, 'KEGG']
        hmdb  = df.at[idx, 'HMDB']

        chebi_id = ""
        source   = ""

        # 1) KEGG → ChEBI
        if pd.notna(kegg) and str(kegg).strip():
            chebi_id = get_chebi_from_kegg(str(kegg).strip())
            time.sleep(REQUEST_DELAY)
            if chebi_id:
                source = f"KEGG({kegg})"

        # 2) HMDB → ChEBI (KEGG로 못 찾은 경우)
        if not chebi_id and pd.notna(hmdb) and str(hmdb).strip():
            chebi_id = get_chebi_from_hmdb(str(hmdb).strip())
            time.sleep(REQUEST_DELAY)
            if chebi_id:
                source = f"HMDB({hmdb})"

        if not chebi_id:
            print(f"  ✗ {name} — ChEBI ID 못 찾음")
            df.at[idx, 'classification_basis'] = "ChEBI: not found (KEGG/HMDB tried)"
            n_keep += 1
            continue

        # ChEBI ID 저장
        df.at[idx, 'ChEBI'] = f"CHEBI:{chebi_id}"
        print(f"  ✓ {name} — ChEBI {chebi_id} (via {source})")

        # 3) roles 조회
        roles = get_roles(chebi_id)
        time.sleep(REQUEST_DELAY)

        if roles:
            df.at[idx, 'chebi_roles'] = roles
        
        if not roles:
            df.at[idx, 'classification_basis'] = f"ChEBI: no roles ({chebi_id}) via {source}"
            n_keep += 1
            print(f"    → roles 없음")
        elif "human metabolite" in roles:
            df.at[idx, 'classification']       = "endogenous"
            df.at[idx, 'classification_basis'] = f"ChEBI: human metabolite ({chebi_id}) via {source}"
            n_endo += 1
            print(f"    → endogenous ✓")
        else:
            df.at[idx, 'classification']       = "exogenous"
            df.at[idx, 'classification_basis'] = f"ChEBI: non-human roles ({chebi_id}) via {source}"
            n_exo += 1
            print(f"    → exogenous")

    df.to_excel(OUT_FILE, index=False)
    apply_format(OUT_FILE)

    print("\n완료.")
    print(f"  대상 {len(targets)}건 중:")
    print(f"    → endogenous : {n_endo}")
    print(f"    → exogenous  : {n_exo}")
    print(f"    → 유지       : {n_keep}")
    print(f"  저장: {OUT_FILE}")


if __name__ == "__main__":
    main()