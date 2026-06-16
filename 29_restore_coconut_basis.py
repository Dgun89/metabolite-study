#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
29_restore_coconut_basis.py
============================
step26~28 에서 ChEBI 재분류 시 unverified 로 남은 행의
classification_basis 가 덮어씌워진 문제를 복구한다.

원인:
  step25 에서 organism 없음/COCONUT 미존재 행은
  coconut_match_key / coconut_organisms 를 채우지 않고
  origin_evidence(현 classification_basis) 에만 텍스트로 기록했는데,
  step26~28 에서 ChEBI 조회 결과로 덮어씌워짐.

복구 방법:
  step25.xlsx 의 origin_evidence 를 참조하여
  step28 의 unverified 행 중 COCONUT 정보가 있는 행만 복원.
  ChEBI 로 재분류된 행(exogenous/endogenous)은 건드리지 않음.
"""

import pandas as pd

IN_FILE   = "metabolites_step28.xlsx"
REF_FILE  = "metabolites_step25.xlsx"   # COCONUT 원본 정보
OUT_FILE  = "metabolites_step29.xlsx"

def main():
    try:
        from format_excel import apply_format
    except ImportError:
        raise SystemExit("format_excel.py 를 찾을 수 없습니다.")

    print(f"읽는 중: {IN_FILE}")
    s28 = pd.read_excel(IN_FILE, sheet_name=0)
    print(f"  총 {len(s28)}행")

    print(f"참조: {REF_FILE}")
    s25 = pd.read_excel(REF_FILE, sheet_name=0)

    # step25 의 origin_evidence (Database ID 기준)
    coconut_map = s25.set_index('Database ID')['origin_evidence'].to_dict()

    # unverified 행만 대상
    unv_mask = s28['classification'] == 'unverified'
    print(f"  unverified 대상: {unv_mask.sum()}건")

    # 복구 전 현황
    print("\n복구 전 classification_basis:")
    print(s28[unv_mask]['classification_basis'].value_counts(dropna=False).head(5))

    # COCONUT 정보로 복구 (기존값 우선, COCONUT 정보 있으면 덮어씀)
    s28['classification_basis'] = s28['classification_basis'].astype(object)
    restored = 0
    for idx in s28.index[unv_mask]:
        db_id = s28.at[idx, 'Database ID']
        coconut_val = coconut_map.get(db_id)
        if coconut_val and str(coconut_val).startswith('COCONUT:'):
            s28.at[idx, 'classification_basis'] = coconut_val
            restored += 1

    # 복구 후 현황
    print(f"\n복구된 행: {restored}건")
    print("\n복구 후 classification_basis (unverified):")
    print(s28[unv_mask]['classification_basis'].value_counts(dropna=False))

    s28.to_excel(OUT_FILE, index=False)
    apply_format(OUT_FILE)

    print(f"\n저장: {OUT_FILE}")


if __name__ == "__main__":
    main()