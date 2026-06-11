#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ──────────────────────────────────────────────────────────────────────────
# 2. classification: no organism data(존재하지만 종 정보 없음) vs. not in release(매칭 자체 안 됨)
# ──────────────────────────────────────────────────────────────────────────
import pandas as pd
df = pd.read_excel("metabolites_step25.xlsx", sheet_name=0)
print(df['origin_evidence'].value_counts(dropna=False))
### 결과(아래 참고) ###
"""
origin_evidence
COCONUT: no organism data         422
NaN                               234
COCONUT: non-human organism(s)    189
COCONUT: not in release            54
COCONUT: Homo sapiens               3
Name: count, dtype: int64
"""
"""
해석
합계 확인: 422+189+54+3=668(unverified 전체)
NaN 234는 원래 분류돼 있던 endogenous 140 + exogenous 94로 처리 대상 아님

시사점
남은 476건 중 압도적 다수(422건)은 COCONUT: no organism data.
즉, COCONUT엔 있는데 생물종 주석이 없는 화합물로 COCONUT에서는 더이상 정보를 얻을 수 없음.
일부(54건)이 COCONUT에 없는 것임.

COCONUT은 endo/exo 분류 db가 아니라 천연물 db임.
"""

# import os
# import sys
# import pandas as pd

# # ──────────────────────────────────────────────────────────────────────────
# # 1. CONFIG
# # ──────────────────────────────────────────────────────────────────────────
# import os
# import sys
# import pandas as pd
"""
step25.py  (로컬 조인 버전 — API 호출 0)
========================================
metabolites_step24.xlsx 의 'unverified'(668행)를 COCONUT 2.0 전체 CSV 와
InChIKey 로 로컬 조인하여 생물종(organism) 정보로 분류 개선한다.

왜 로컬 조인인가:
  - COCONUT search API 는 로그인 토큰 필요(401).
  - 공개 bioschemas 는 CNP ID 로만 조회되는데, step24 의 Database ID(CNP)가
    현재 COCONUT 2.0 와 ID 체계가 어긋나 404 가 난다.
  → 버전 불변 키인 InChIKey 로 전체 CSV 에 조인하면 인증·404·rate limit 무관.

준비물 (한 번만):
  COCONUT 전체 데이터 CSV 다운로드
    https://coconut.naturalproducts.net/download   (CSV)
    또는 https://zenodo.org/records/13692394
  → 받은 파일 경로를 아래 CSV_FILE 에 지정.

분류 규칙 (적극적):
  - 해당 InChIKey 의 organism 에 Homo sapiens 포함  → endogenous
  - organism 있으나 사람 없음                        → exogenous
  - COCONUT CSV 에 organism 없음 / InChIKey 미발견    → unverified 유지
  ※ 이미 endogenous/exogenous 인 행은 손대지 않음.

시트 유지: Sheet1 수정 → to_excel → format_excel.apply_format() 로 Legend/Summary 재생성.

의존성: pip install pandas openpyxl
"""
# IN_FILE   = "metabolites_step24.xlsx"
# OUT_FILE  = "metabolites_step25.xlsx"
# CSV_FILE  = "coconut_complete.csv"        # ★ 내려받은 COCONUT 전체 CSV 경로

# CLASS_COL        = "compound_origin"
# UNVERIFIED_VALUE = "unverified"
# INCHIKEY_COL     = "InChIKey"             # step24 쪽 InChIKey 컬럼
# ID_COL           = "Database ID"          # CNP (보조 매칭용)

# # COCONUT CSV 의 컬럼명 (None 이면 자동탐지). INSPECT 로 먼저 확인 가능.
# CSV_INCHIKEY = None     # 예: "standard_inchi_key" / "inchikey"
# CSV_ORGANISM = None     # 예: "organisms"
# CSV_ID       = None     # 예: "identifier"

# HUMAN_KEY  = "homo sapiens"
# CHUNK      = 50000      # CSV 스트리밍 청크 크기
# MAX_ORG_STORE = 200    # organism 셀 저장 시 최대 글자수

# # CSV 컬럼명만 출력하고 종료 (자동탐지 결과가 의심스러우면 True 로 1회 실행)
# INSPECT_CSV = False

# # ──────────────────────────────────────────────────────────────────────────
# def detect_col(columns, contains_all=None, contains_any=None, equals=None):
#     low = {c: c.lower() for c in columns}
#     if equals:
#         for c, l in low.items():
#             if l in equals:
#                 return c
#     if contains_all:
#         for c, l in low.items():
#             if all(k in l for k in contains_all):
#                 return c
#     if contains_any:
#         for c, l in low.items():
#             if any(k in l for k in contains_any):
#                 return c
#     return None


# def inspect_csv():
#     cols = pd.read_csv(CSV_FILE, nrows=0).columns.tolist()
#     print(f"[INSPECT] {CSV_FILE} 컬럼 {len(cols)}개:")
#     for c in cols:
#         print("   -", c)
#     print("\n[INSPECT] 첫 행 샘플:")
#     print(pd.read_csv(CSV_FILE, nrows=1).T)
#     print("\n→ InChIKey/organism/identifier 컬럼명을 확인해 CONFIG 의")
#     print("  CSV_INCHIKEY / CSV_ORGANISM / CSV_ID 에 넣고 INSPECT_CSV=False 로 실행.")


# def norm_ik(x):
#     if x is None or (isinstance(x, float) and pd.isna(x)):
#         return None
#     s = str(x).strip().upper()
#     return s if len(s) >= 14 else None


# def main():
#     if not os.path.exists(CSV_FILE):
#         sys.exit(f"COCONUT CSV 없음: {CSV_FILE}\n  → 다운로드 후 CSV_FILE 경로 지정.")
#     if INSPECT_CSV:
#         inspect_csv(); return
#     if not os.path.exists(IN_FILE):
#         sys.exit(f"입력 파일 없음: {IN_FILE}")
#     try:
#         from format_excel import apply_format
#     except ImportError:
#         sys.exit("format_excel.py 를 찾을 수 없습니다(같은 폴더에 두세요).")

#     # ── 1) step24 읽고 대상 식별자 집합 만들기 ───────────────────────────
#     print(f"읽는 중: {IN_FILE}")
#     df = pd.read_excel(IN_FILE, sheet_name=0)
#     mask = (df[CLASS_COL].astype(str).str.strip().str.lower()
#             == UNVERIFIED_VALUE.lower())
#     targets = df.index[mask].tolist()
#     print(f"  총 {len(df)}행 / unverified {len(targets)}행")

#     want_ik_full = set()      # 완전 InChIKey
#     want_ik_skel = set()      # 앞 14자 스켈레톤
#     want_cnp     = set()      # CNP (보조)
#     for idx in targets:
#         ik = norm_ik(df.at[idx, INCHIKEY_COL]) if INCHIKEY_COL in df.columns else None
#         if ik:
#             want_ik_full.add(ik); want_ik_skel.add(ik[:14])
#         cnp = df.at[idx, ID_COL]
#         if pd.notna(cnp):
#             want_cnp.add(str(cnp).strip())

#     # ── 2) COCONUT CSV 컬럼 자동탐지 ─────────────────────────────────────
#     cols = pd.read_csv(CSV_FILE, nrows=0).columns.tolist()
#     ik_col  = CSV_INCHIKEY or detect_col(cols, contains_all=["inchi", "key"])
#     org_col = CSV_ORGANISM or detect_col(cols, contains_any=["organism", "taxonom", "species"])
#     id_col  = CSV_ID or detect_col(cols, equals=["identifier"],
#                                    contains_any=["identifier", "coconut_id"])
#     print(f"  CSV 컬럼 → InChIKey={ik_col!r}  organism={org_col!r}  id={id_col!r}")
#     if not ik_col or not org_col:
#         sys.exit("CSV 의 InChIKey/organism 컬럼 자동탐지 실패.\n"
#                  "  → INSPECT_CSV=True 로 컬럼명 확인 후 CONFIG 에 직접 지정.")

#     usecols = [c for c in [ik_col, org_col, id_col] if c]

#     # ── 3) 대용량 CSV 스트리밍하며 필요한 행만 수집 ──────────────────────
#     print(f"  COCONUT CSV 스캔 중 (청크 {CHUNK})...")
#     by_ik, by_skel, by_cnp = {}, {}, {}
#     scanned = 0
#     for chunk in pd.read_csv(CSV_FILE, usecols=usecols, chunksize=CHUNK,
#                              dtype=str, low_memory=False):
#         scanned += len(chunk)
#         for _, row in chunk.iterrows():
#             org = row.get(org_col)
#             ik  = norm_ik(row.get(ik_col))
#             cnp = str(row.get(id_col)).strip() if id_col and pd.notna(row.get(id_col)) else None
#             if ik:
#                 if ik in want_ik_full and ik not in by_ik:
#                     by_ik[ik] = org
#                 sk = ik[:14]
#                 if sk in want_ik_skel and sk not in by_skel:
#                     by_skel[sk] = org
#             if cnp and cnp in want_cnp and cnp not in by_cnp:
#                 by_cnp[cnp] = org
#         print(f"    {scanned:,}행 스캔  (ik매칭 {len(by_ik)}, skel {len(by_skel)}, cnp {len(by_cnp)})")
#     print(f"  스캔 완료: 총 {scanned:,}행")

#     # ── 4) 분류 적용 ────────────────────────────────────────────────────
#     for col in ["coconut_organisms", "coconut_match_key", "origin_evidence"]:
#         if col not in df.columns:
#             df[col] = pd.NA

#     n_endo = n_exo = n_keep = 0
#     for idx in targets:
#         ik  = norm_ik(df.at[idx, INCHIKEY_COL]) if INCHIKEY_COL in df.columns else None
#         cnp = str(df.at[idx, ID_COL]).strip() if pd.notna(df.at[idx, ID_COL]) else None

#         org, key = None, None
#         if ik and ik in by_ik:
#             org, key = by_ik[ik], "inchikey"
#         elif ik and ik[:14] in by_skel:
#             org, key = by_skel[ik[:14]], "inchikey_skeleton"
#         elif cnp and cnp in by_cnp:
#             org, key = by_cnp[cnp], "cnp_id"

#         has_org = isinstance(org, str) and org.strip() != "" and org.strip().lower() != "nan"
#         has_human = has_org and (HUMAN_KEY in org.lower())

#         if has_org:
#             df.at[idx, "coconut_organisms"] = org[:MAX_ORG_STORE]
#             df.at[idx, "coconut_match_key"] = key

#         if has_human:
#             df.at[idx, CLASS_COL] = "endogenous"
#             df.at[idx, "origin_evidence"] = "COCONUT: Homo sapiens"
#             n_endo += 1
#         elif has_org:
#             df.at[idx, CLASS_COL] = "exogenous"
#             df.at[idx, "origin_evidence"] = "COCONUT: non-human organism(s)"
#             n_exo += 1
#         else:
#             df.at[idx, "origin_evidence"] = ("COCONUT: not in release"
#                                              if key is None else "COCONUT: no organism data")
#             n_keep += 1

#     # ── 5) 저장 + 포맷 재생성 ───────────────────────────────────────────
#     df.to_excel(OUT_FILE, index=False)
#     apply_format(OUT_FILE)

#     print("\n완료.")
#     print(f"  unverified {len(targets)} 중 →endogenous {n_endo}, →exogenous {n_exo}, 유지 {n_keep}")
#     print(f"  남은 unverified: {len(targets) - n_endo - n_exo}")
#     print(f"  저장: {OUT_FILE} (Sheet1 + Legend + Summary)")


# if __name__ == "__main__":
#     main()
### 결과 아래 참조 ###
"""
읽는 중: metabolites_step24.xlsx
  총 902행 / unverified 668행
  CSV 컬럼 → InChIKey='standard_inchi_key'  organism='organisms'  id='identifier'
  COCONUT CSV 스캔 중 (청크 50000)...
    50,000행 스캔  (ik매칭 22, skel 61, cnp 22)
    100,000행 스캔  (ik매칭 45, skel 124, cnp 44)
    150,000행 스캔  (ik매칭 63, skel 179, cnp 62)
    200,000행 스캔  (ik매칭 85, skel 221, cnp 81)
    250,000행 스캔  (ik매칭 103, skel 262, cnp 100)
    300,000행 스캔  (ik매칭 121, skel 303, cnp 117)
    350,000행 스캔  (ik매칭 139, skel 347, cnp 134)
    400,000행 스캔  (ik매칭 152, skel 378, cnp 149)
    450,000행 스캔  (ik매칭 170, skel 410, cnp 167)
    500,000행 스캔  (ik매칭 188, skel 447, cnp 186)
    550,000행 스캔  (ik매칭 201, skel 478, cnp 201)
    600,000행 스캔  (ik매칭 229, skel 517, cnp 229)
    650,000행 스캔  (ik매칭 252, skel 550, cnp 252)
    700,000행 스캔  (ik매칭 271, skel 582, cnp 273)
    738,827행 스캔  (ik매칭 285, skel 608, cnp 288)
  스캔 완료: 총 738,827행
포맷 적용 완료: metabolites_step25.xlsx
완료.
  unverified 668 중 →endogenous 3, →exogenous 189, 유지 476
  남은 unverified: 476
  저장: metabolites_step25.xlsx (Sheet1 + Legend + Summary)
"""