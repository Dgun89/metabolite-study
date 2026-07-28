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


def classify_row_v2(chebi_roles, hmdb_source, coconut_organisms):
    """
    정규화 스키마용 확장 분류.

    classify_row()의 우선순위 라벨(하위호환)은 그대로 두되, 각 소스가
    독립적으로 어떤 기원(endogenous/exogenous)을 지지하는지 모두 평가해
    소스 간 불일치(conflict)를 노출한다. 다중 기원을 단일 라벨로 뭉개던
    기존 문제를 해결하기 위한 함수.

    반환: dict {
        classification        : 최종 라벨(= classify_row() 우선순위 결과, 하위호환),
        classification_basis  : 최종 라벨 근거 문자열,
        conflict_flag         : bool — endogenous·exogenous 근거가 동시에 존재,
        conflicting_sources   : "ChEBI=endogenous;HMDB=exogenous" 형태 요약,
        source_verdicts       : {source: verdict} 딕셔너리(감사용),
    }
    """
    roles = [str(r).lower() for r in (chebi_roles or [])]
    hsrc = [str(s).lower() for s in (hmdb_source or [])]
    orgs = str(coconut_organisms or "").lower()
    has_orgs = bool(orgs) and orgs not in ("nan", "none", "")

    verdicts = {}  # source -> 'endogenous' | 'exogenous'

    # ChEBI
    if HUMAN_ROLE in roles:
        verdicts["ChEBI"] = "endogenous"
    elif roles:
        verdicts["ChEBI"] = "exogenous"

    # HMDB
    if any("endogenous" in s for s in hsrc):
        verdicts["HMDB"] = "endogenous"
    elif hsrc and any(any(k in s for k in EXO_SOURCE_KEYS) for s in hsrc):
        verdicts["HMDB"] = "exogenous"

    # COCONUT organisms
    if HOMO in orgs:
        verdicts["COCONUT"] = "endogenous"
    elif has_orgs:
        verdicts["COCONUT"] = "exogenous"

    distinct = set(verdicts.values())
    conflict = ("endogenous" in distinct) and ("exogenous" in distinct)
    conflicting = ";".join(f"{k}={v}" for k, v in sorted(verdicts.items())) if conflict else ""

    # 최종 라벨은 기존 우선순위 규칙과 동일(하위호환 보장)
    classification, basis = classify_row(chebi_roles, hmdb_source, coconut_organisms)

    return {
        "classification": classification,
        "classification_basis": basis,
        "conflict_flag": conflict,
        "conflicting_sources": conflicting,
        "source_verdicts": verdicts,
    }


def classify_row_v3(chebi_roles, hmdb_source, coconut_organisms, mmmdb_tissues=0):
    """
    v2에 MMMDB(실제 쥐 조직 검출) 근거를 최우선 규칙 E0로 추가한 분류.

    E0 (최우선): 화합물이 MMMDB(Mouse Multiple tissue Metabolome DataBase)에서
      실제 쥐 조직에 검출됨 -> endogenous. 이는 포유류 조직 대사체라는 직접 실험
      근거이므로 ChEBI/HMDB/COCONUT 규칙보다 우선한다.

    conflict_flag/conflicting_sources는 v2와 동일하게 ChEBI/HMDB/COCONUT 소스 간
    불일치를 노출한다(MMMDB는 conflict 계산에서 endogenous 근거로 함께 반영).

    반환: v2 dict + {mmmdb_detected, mmmdb_n_tissues}.
    """
    v2 = classify_row_v2(chebi_roles, hmdb_source, coconut_organisms)
    mmmdb_detected = bool(mmmdb_tissues and int(mmmdb_tissues) > 0)

    verdicts = dict(v2["source_verdicts"])
    if mmmdb_detected:
        verdicts["MMMDB"] = "endogenous"
        classification = "endogenous"
        basis = f"MMMDB: detected in {int(mmmdb_tissues)} mouse tissue(s)"
    else:
        classification = v2["classification"]
        basis = v2["classification_basis"]

    distinct = set(verdicts.values())
    conflict = ("endogenous" in distinct) and ("exogenous" in distinct)
    conflicting = ";".join(f"{k}={v}" for k, v in sorted(verdicts.items())) if conflict else ""

    return {
        "classification": classification,
        "classification_basis": basis,
        "conflict_flag": conflict,
        "conflicting_sources": conflicting,
        "source_verdicts": verdicts,
        "mmmdb_detected": mmmdb_detected,
        "mmmdb_n_tissues": int(mmmdb_tissues) if mmmdb_detected else 0,
    }


def assign_msi(has_inchikey, db_id_count, mmmdb_detected=False):
    """
    MSI(Metabolomics Standards Initiative) 동정 신뢰도 등급 자동 부여.

    논타겟 데이터라 정제 표준물질 대조(진정한 MSI Level 1)는 부여하지 않는다
    (프로젝트 연구 노트 방침). 독립 DB 교차증거 수로 등급을 매긴다:

      L2 probable structure : InChIKey 있음 AND 독립 DB ID >=2개 교차확인
                              (HMDB/KEGG/ChEBI/… + MMMDB full-InChIKey 매칭은
                               종 특이 확인으로 1개로 계수).
      L3 tentative          : InChIKey 있음 AND 독립 DB ID <=1개
      L4 molecular formula  : InChIKey 없음, DB name link만 존재
      L5 unknown            : InChIKey 없음 AND DB ID 전무

    반환: 'L2' | 'L3' | 'L4' | 'L5'
    """
    db = int(db_id_count or 0) + (1 if mmmdb_detected else 0)
    if has_inchikey and db >= 2:
        return "L2"
    if has_inchikey:
        return "L3"
    if db >= 1:
        return "L4"
    return "L5"


def classify_row_v4(chebi_roles, hmdb_source, coconut_organisms, mmmdb_tissues=0):
    """
    5단계: 우선순위 규칙 폐기 — 각 DB의 판정을 그대로 나열한다 (2026-07-27 회의).

    배경: v1~v3는 여러 DB의 기원 신호를 우선순위(E1>E2>E3>X1...)로 눌러
    **하나의 최종 라벨**을 강제했다. 그러나 각 DB는 서로 다른 축
    (ChEBI=produced / HMDB=detected / COCONUT=isolated-from)으로 기원을 말하므로,
    하나로 합치면 축을 뭉갠다. v4는 판정을 강제하지 않고 DB별 판정을 병렬로 노출한다.

    - classification 컬럼 = "ChEBI:endogenous; HMDB:endogenous; COCONUT:exogenous;
      MMMDB:endogenous" 형태(판정 근거가 있는 DB만; 정렬은 고정 우선순위 표시용 아님).
    - 아무 DB도 판정 못 하면 "unverified".
    - conflict_flag/conflicting_sources는 유지 — endo·exo가 동시에 존재하는지의
      감사 신호는 여전히 유용하다(어느 쪽이 '맞다'고 고르지 않을 뿐).

    v3(classify_row_v3)는 하위호환/박제를 위해 그대로 둔다. v4는 그 위에 쌓는다.

    반환: v3와 동일 키 + source_verdicts(감사용). classification/basis만 의미가 바뀜:
      classification : "DB:verdict; ..." 병렬 나열 (또는 "unverified")
      classification_basis : 사람이 읽는 요약(동일 나열 + MMMDB 조직수)
    """
    # v3의 verdicts 계산을 그대로 재사용(축별 판정 산출) — 단, 최종 라벨 강제는 버린다.
    v3 = classify_row_v3(chebi_roles, hmdb_source, coconut_organisms, mmmdb_tissues)
    verdicts = dict(v3["source_verdicts"])  # {source: 'endogenous'|'exogenous'}

    # DB 판정을 고정 순서로 나열(가독성용 순서일 뿐, 우선순위 아님).
    ORDER = ["ChEBI", "HMDB", "COCONUT", "MMMDB"]
    items = ([(s, verdicts[s]) for s in ORDER if s in verdicts]
             + [(s, v) for s, v in sorted(verdicts.items()) if s not in ORDER])
    if items:
        classification = "; ".join(f"{s}:{v}" for s, v in items)
    else:
        classification = "unverified"

    # basis: 나열 + MMMDB 조직수(있으면) — 판정이 아니라 '무엇을 근거로 나열했나'.
    basis = classification
    if v3["mmmdb_detected"]:
        basis += f"  [MMMDB: {v3['mmmdb_n_tissues']} tissue(s)]"

    return {
        "classification": classification,
        "classification_basis": basis,
        "conflict_flag": v3["conflict_flag"],
        "conflicting_sources": v3["conflicting_sources"],
        "source_verdicts": verdicts,
        "mmmdb_detected": v3["mmmdb_detected"],
        "mmmdb_n_tissues": v3["mmmdb_n_tissues"],
    }
