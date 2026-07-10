"""
4단계: 내인성/외인성 분류 (규칙 기반, legacy 재현).

우선순위 (endogenous 우세):
  E1 ChEBI roles에 'human metabolite'  -> endogenous
  E2 HMDB source에 'Endogenous'        -> endogenous
  E3 COCONUT organisms에 Homo sapiens   -> endogenous
  X1 HMDB source에 'Exogenous'/'Food'/'Drug' (Endogenous 없음) -> exogenous
  X2 ChEBI roles 존재하나 human metabolite 없음               -> exogenous
  X3 COCONUT organisms 존재하나 Homo sapiens 없음(비인간만)    -> exogenous
  U  위 근거 모두 없음                                        -> unverified
classification_basis 문자열도 함께 기록 (legacy step29 스타일).
"""

HUMAN_ROLE = "human metabolite"
HOMO = "homo sapiens"
EXO_SOURCE_KEYS = ("exogenous", "food", "drug", "microbial", "plant", "toxin", "cosmetic")


def classify_row(chebi_roles, hmdb_source, coconut_organisms):
    """반환: (classification, basis)"""
    roles = [str(r).lower() for r in (chebi_roles or [])]
    hsrc = [str(s).lower() for s in (hmdb_source or [])]
    orgs = str(coconut_organisms or "").lower()
    has_orgs = bool(orgs) and orgs not in ("nan", "none", "")

    # --- endogenous 근거 ---
    if HUMAN_ROLE in roles:
        return "endogenous", "ChEBI role: human metabolite"
    if any("endogenous" in s for s in hsrc):
        return "endogenous", "HMDB source: Endogenous"
    if HOMO in orgs:
        return "endogenous", "COCONUT organisms: Homo sapiens"

    # --- exogenous 근거 ---
    if hsrc and any(any(k in s for k in EXO_SOURCE_KEYS) for s in hsrc):
        hit = next(s for s in hsrc if any(k in s for k in EXO_SOURCE_KEYS))
        return "exogenous", f"HMDB source: {hit}"
    if roles:
        return "exogenous", "ChEBI roles present, no human metabolite"
    if has_orgs:
        return "exogenous", "COCONUT organisms: non-human only"

    # --- 근거 없음 ---
    # COCONUT 매칭됐으나 organism 정보 없음 vs 아예 미매칭 구분 (legacy step29 스타일)
    return "unverified", "no organism/role data"
