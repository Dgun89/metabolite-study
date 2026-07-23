from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date

GROUPS = {
    "Basic Identifiers": {
        "columns": ["InChIKey", "compound_name", "SMILES"],
        "color": "BDD7EE",
        "description": "Core compound identifiers (primary key = InChIKey)"
    },
    "Dataset Membership": {
        "columns": ["datasets"],
        "color": "D6DCE4",
        "description": "Which source datasets this compound appears in (combined view only)"
    },
    "External DB IDs": {
        "columns": ["COCONUT", "PubChem", "KEGG", "HMDB", "ChEBI", "DrugBank", "FooDB", "LIPID MAPS"],
        "color": "C6EFCE",
        "description": "Cross-reference IDs from external databases (UniChem-resolved)"
    },
    "Classification": {
        "columns": ["classification"],
        "color": "FFEB9C",
        "description": "Final classification: endogenous / exogenous / unverified"
    },
    "Classification Sources": {
        "columns": ["hmdb_origin", "coconut_organisms", "chebi_roles"],
        "color": "FFD9B3",
        "description": "Source data used to determine classification"
    },
    "Classification Metadata": {
        "columns": ["classification_basis"],
        "color": "E4DFEC",
        "description": "Reasoning behind classification"
    },
    "DB Support": {
        "columns": ["db_support_level", "db_support_evidence", "mmmdb_detected", "mmmdb_tissues"],
        "color": "FCE4D6",
        "description": "Structure-consensus support from independent databases (not spectral MSI) and MMMDB mouse-tissue evidence"
    },
    "Classification Conflicts": {
        "columns": ["conflict_flag", "conflicting_sources"],
        "color": "F8CBAD",
        "description": "Whether sources disagree on origin, and which verdicts conflict"
    },
    "Enzyme Information": {
        "columns": ["kegg_enzymes", "hmdb_enzymes", "reactome_catalysts", "brenda_enzymes"],
        "color": "DAEEF3",
        "description": "Enzyme data from multiple databases"
    }
}

COL_SOURCE = {
    "InChIKey"             : "COCONUT",
    "compound_name"        : "COCONUT",
    "COCONUT"              : "COCONUT",
    "datasets"             : "pipeline",
    "SMILES"               : "COCONUT",
    "PubChem"              : "PubChem",
    "KEGG"                 : "KEGG",
    "HMDB"                 : "HMDB",
    "ChEBI"                : "ChEBI",
    "DrugBank"             : "UniChem",
    "FooDB"                : "UniChem",
    "LIPID MAPS"           : "UniChem",
    "classification"       : "ChEBI + HMDB + COCONUT + MMMDB",
    "hmdb_origin"          : "HMDB",
    "coconut_organisms"    : "COCONUT",
    "chebi_roles"          : "ChEBI",
    "classification_basis" : "ChEBI + COCONUT + MMMDB",
    "db_support_level"     : "pipeline",
    "db_support_evidence"  : "pipeline",
    "mmmdb_detected"       : "MMMDB",
    "mmmdb_tissues"        : "MMMDB",
    "conflict_flag"        : "ChEBI + HMDB + COCONUT",
    "conflicting_sources"  : "ChEBI + HMDB + COCONUT",
    "kegg_enzymes"         : "KEGG",
    "hmdb_enzymes"         : "HMDB",
    "reactome_catalysts"   : "Reactome",
    "brenda_enzymes"       : "BRENDA", 
}

# External DB IDs 그룹의 헤더(1행)에 걸 각 데이터베이스 공식 홈페이지 링크.
# 클릭하면 해당 사이트로 이동한다(값 셀이 아니라 컬럼 타이틀에만 링크).
DB_HOMEPAGE = {
    "COCONUT"   : "https://coconut.naturalproducts.net/",
    "PubChem"   : "https://pubchem.ncbi.nlm.nih.gov/",
    "KEGG"      : "https://www.kegg.jp/",
    "HMDB"      : "https://hmdb.ca/",
    "ChEBI"     : "https://www.ebi.ac.uk/chebi/",
    "DrugBank"  : "https://go.drugbank.com/",
    "FooDB"     : "https://foodb.ca/",
    "LIPID MAPS": "https://www.lipidmaps.org/",
}

COL_DESC = {
    "InChIKey"             : "Chemical structure key (27-char) — primary key for all joins/merges/sorting",
    "compound_name"        : "Compound name",
    "COCONUT"              : "COCONUT compound ID(s) (CNP) mapped to this InChIKey (display reference; semicolon-separated)",
    "datasets"             : "Source datasets this compound appears in (human / mouse_serum / mouse_feces; semicolon-separated)",
    "SMILES"               : "Chemical structure in text format",
    "PubChem"              : "PubChem Compound ID (CID)",
    "KEGG"                 : "KEGG Compound ID",
    "HMDB"                 : "Human Metabolome Database ID",
    "ChEBI"                : "Chemical Entities of Biological Interest ID",
    "DrugBank"             : "DrugBank ID (cross-linked via UniChem)",
    "FooDB"                : "FooDB ID (cross-linked via UniChem)",
    "LIPID MAPS"           : "LIPID MAPS ID (cross-linked via UniChem)",
    "classification"       : "Final classification: endogenous / exogenous / unverified",
    "hmdb_origin"          : "HMDB origin field (Endogenous / Food / Drug etc.)",
    "coconut_organisms"    : "Organisms associated with compound in COCONUT (used to infer classification)",
    "chebi_roles"          : "Role classification from ChEBI (semicolon-separated)",
    "classification_basis" : "Reason behind classification (e.g. MMMDB: detected in mouse tissue / ChEBI: human metabolite)",
    "db_support_level"     : "DB-support level (structure-consensus proxy, NOT spectral MSI): L2 = >=2 independent DB IDs / L3 = <=1 / L4 formula-only / L5 unknown",
    "db_support_evidence"  : "Independent databases supporting this structure (InChIKey + cross-references, incl. MMMDB tissue evidence)",
    "mmmdb_detected"       : "True if compound detected in real mouse tissue (MMMDB, InChIKey match)",
    "mmmdb_tissues"        : "Mouse tissues where compound was detected in MMMDB (semicolon-separated)",
    "conflict_flag"        : "True if sources disagree on endogenous vs exogenous origin",
    "conflicting_sources"  : "Per-source verdicts when they conflict (e.g. COCONUT=endogenous;ChEBI=exogenous)",
    "kegg_enzymes"         : "EC numbers from KEGG (semicolon-separated)",
    "hmdb_enzymes"         : "Enzyme gene names from HMDB (semicolon-separated)",
    "reactome_catalysts"   : "Catalyst activity names from Reactome",
    "brenda_enzymes"       : "EC numbers from BRENDA (semicolon-separated; source: BRENDA Enzyme Database)",
}

def apply_format(filepath: str):
    import pandas as pd
    df = pd.read_excel(filepath)

    # GROUPS 정의 순서대로 컬럼 재배치 (Legend 계층과 물리 순서 일치)
    ordered = [c for g in GROUPS.values() for c in g["columns"] if c in df.columns]
    extras = [c for c in df.columns if c not in ordered]
    df = df[ordered + extras]
    df.to_excel(filepath, index=False)

    col_color = {}
    for group, info in GROUPS.items():
        for col in info["columns"]:
            col_color[col] = info["color"]

    wb = load_workbook(filepath)
    ws = wb.active

    # 헤더 볼드 + 배경색 (External DB IDs는 헤더에 홈페이지 하이퍼링크)
    for cell in ws[1]:
        col_name = cell.value
        color = col_color.get(col_name, "FFFFFF")
        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
        url = DB_HOMEPAGE.get(col_name)
        if url:
            cell.hyperlink = url
            # 링크가 걸린 헤더: 밑줄 + 진한 파랑으로 클릭 가능함을 표시
            cell.font = Font(bold=True, underline="single", color="0563C1")
        else:
            cell.font = Font(bold=True)

    # 컬럼 너비 자동 조정
    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    # ─────────────────────────────
    # Legend 시트
    # ─────────────────────────────
    if "Legend" in wb.sheetnames:
        del wb["Legend"]
    legend_ws = wb.create_sheet("Legend")

    legend_ws["A1"] = "Metabolite Database — Column Legend"
    legend_ws["A1"].font = Font(bold=True, size=13)
    legend_ws.merge_cells("A1:D1")

    for i, h in enumerate(["Group", "Color", "Column", "Description", "Source"], 1):
        cell = legend_ws.cell(row=3, column=i, value=h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    row = 4
    for group, info in GROUPS.items():
        for col in info["columns"]:
            legend_ws.cell(row=row, column=1, value=group)
            legend_ws.cell(row=row, column=2).fill = PatternFill(
                start_color=info["color"], end_color=info["color"], fill_type="solid"
            )
            legend_ws.cell(row=row, column=3, value=col)
            legend_ws.cell(row=row, column=4, value=COL_DESC.get(col, ""))
            legend_ws.cell(row=row, column=5, value=COL_SOURCE.get(col, ""))
            row += 1

    legend_ws.column_dimensions["A"].width = 22
    legend_ws.column_dimensions["B"].width = 10
    legend_ws.column_dimensions["C"].width = 25
    legend_ws.column_dimensions["D"].width = 50
    legend_ws.column_dimensions["E"].width = 20

    # ─────────────────────────────
    # Summary 시트
    # ─────────────────────────────
    if "Summary" in wb.sheetnames:
        del wb["Summary"]
    summary_ws = wb.create_sheet("Summary")

    summary_ws["A1"] = "Metabolite Database — Coverage Summary"
    summary_ws["A1"].font = Font(bold=True, size=13)
    summary_ws.merge_cells("A1:D1")

    summary_ws["A2"] = f"Last updated: {date.today()}"
    summary_ws["A2"].font = Font(italic=True)

    # 헤더
    for i, h in enumerate(["Category", "Item", "Count", "Coverage"], 1):
        cell = summary_ws.cell(row=4, column=i, value=h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    total = len(df)

     # 효소 플래그
    def hv(col):
        return df[col].notna() & (df[col].astype(str).str.strip() != "")

    has_kegg     = hv('kegg_enzymes')
    has_hmdb     = hv('hmdb_enzymes')
    has_reactome = hv('reactome_catalysts')
    has_brenda   = hv('brenda_enzymes')

    rows = [
        ("Overview",       "Total compounds", total,                        "100%"),
        ("Overview",       "InChIKey",        df['InChIKey'].notna().sum(), f"{df['InChIKey'].notna().sum()/total*100:.1f}%"),
        ("Overview",       "SMILES",          df['SMILES'].notna().sum(),   f"{df['SMILES'].notna().sum()/total*100:.1f}%"),
        ("External DB IDs","PubChem",         df['PubChem'].notna().sum(),  f"{df['PubChem'].notna().sum()/total*100:.1f}%"),
        ("External DB IDs","KEGG",            df['KEGG'].notna().sum(),     f"{df['KEGG'].notna().sum()/total*100:.1f}%"),
        ("External DB IDs","HMDB",            df['HMDB'].notna().sum(),     f"{df['HMDB'].notna().sum()/total*100:.1f}%"),
        ("External DB IDs","ChEBI",           df['ChEBI'].notna().sum(),    f"{df['ChEBI'].notna().sum()/total*100:.1f}%"),
        ("Classification", "Endogenous",      (df['classification']=='endogenous').sum(), f"{(df['classification']=='endogenous').sum()/total*100:.1f}%"),
        ("Classification", "Exogenous",       (df['classification']=='exogenous').sum(),  f"{(df['classification']=='exogenous').sum()/total*100:.1f}%"),
        ("Classification", "Unverified",      (df['classification']=='unverified').sum(), f"{(df['classification']=='unverified').sum()/total*100:.1f}%"),
    ]

    if 'origin_evidence' in df.columns:
        ev = df['origin_evidence'].astype(str)
        def cnt(key): return int(ev.str.contains(key, case=False, na=False).sum())
        rows += [
            ("Origin Evidence", "Reclassified → endogenous", cnt('Homo sapiens'), f"{cnt('Homo sapiens')/total*100:.1f}%"),
            ("Origin Evidence", "Reclassified → exogenous", cnt('non-human'), f"{cnt('non-human')/total*100:.1f}%"),
            ("Origin Evidence", "Unverified: no organism data", cnt('no organism'), f"{cnt('no organism')/total*100:.1f}%"),
            ("Origin Evidence", "Unverified: not in COCONUT", cnt('not in release'), f"{cnt('not in release')/total*100:.1f}%"),
        ]

    rows += [
            # 단독
            ("Enzyme Info (single source)", "KEGG only",     int((has_kegg  & ~has_hmdb & ~has_reactome & ~has_brenda).sum()), f"{(has_kegg & ~has_hmdb & ~has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (single source)", "HMDB only",     int((~has_kegg & has_hmdb  & ~has_reactome & ~has_brenda).sum()), f"{(~has_kegg & has_hmdb & ~has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (single source)", "Reactome only", int((~has_kegg & ~has_hmdb & has_reactome  & ~has_brenda).sum()), f"{(~has_kegg & ~has_hmdb & has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (single source)", "BRENDA only",   int((~has_kegg & ~has_hmdb & ~has_reactome & has_brenda).sum()),  f"{(~has_kegg & ~has_hmdb & ~has_reactome & has_brenda).sum()/total*100:.1f}%"),
            # 중복
            ("Enzyme Info (overlap)", "KEGG + HMDB",              int((has_kegg & has_hmdb  & ~has_reactome & ~has_brenda).sum()), f"{(has_kegg & has_hmdb & ~has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "KEGG + Reactome",          int((has_kegg & ~has_hmdb & has_reactome  & ~has_brenda).sum()), f"{(has_kegg & ~has_hmdb & has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "KEGG + BRENDA",            int((has_kegg & ~has_hmdb & ~has_reactome & has_brenda).sum()),  f"{(has_kegg & ~has_hmdb & ~has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "HMDB + Reactome",          int((~has_kegg & has_hmdb & has_reactome  & ~has_brenda).sum()), f"{(~has_kegg & has_hmdb & has_reactome & ~has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "HMDB + BRENDA",            int((~has_kegg & has_hmdb & ~has_reactome & has_brenda).sum()),  f"{(~has_kegg & has_hmdb & ~has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "Reactome + BRENDA",        int((~has_kegg & ~has_hmdb & has_reactome & has_brenda).sum()),  f"{(~has_kegg & ~has_hmdb & has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "KEGG + HMDB + BRENDA",     int((has_kegg & has_hmdb & ~has_reactome & has_brenda).sum()),   f"{(has_kegg & has_hmdb & ~has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "KEGG + Reactome + BRENDA", int((has_kegg & ~has_hmdb & has_reactome & has_brenda).sum()),   f"{(has_kegg & ~has_hmdb & has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "HMDB + Reactome + BRENDA", int((~has_kegg & has_hmdb & has_reactome & has_brenda).sum()),   f"{(~has_kegg & has_hmdb & has_reactome & has_brenda).sum()/total*100:.1f}%"),
            ("Enzyme Info (overlap)", "All 4 sources",            int((has_kegg & has_hmdb & has_reactome & has_brenda).sum()),    f"{(has_kegg & has_hmdb & has_reactome & has_brenda).sum()/total*100:.1f}%"),
            # 합계
            ("Enzyme Info", "Total (unique)", int((has_kegg | has_hmdb | has_reactome | has_brenda).sum()), f"{(has_kegg | has_hmdb | has_reactome | has_brenda).sum()/total*100:.1f}%"),
        ]

    for i, (category, item, count, coverage) in enumerate(rows, 5):
        summary_ws.cell(row=i, column=1, value=category)
        summary_ws.cell(row=i, column=2, value=item)
        summary_ws.cell(row=i, column=3, value=count)
        summary_ws.cell(row=i, column=4, value=coverage)

    summary_ws.column_dimensions["A"].width = 20
    summary_ws.column_dimensions["B"].width = 25
    summary_ws.column_dimensions["C"].width = 10
    summary_ws.column_dimensions["D"].width = 12

    _build_classification_rules_sheet(wb)

    wb.save(filepath)
    print(f"포맷 적용 완료: {filepath}")


def _build_classification_rules_sheet(wb):
    """
    conflicting_sources / classification 우선순위 규칙을 명시하는 시트.
    영어 블록 먼저, 이어서 한국어 블록. 내용은 pipeline/classify.py의
    classify_row_v3() 실제 로직과 1:1 대응(추측 아님).
    """
    ws = wb.create_sheet("Classification Rules")

    H1  = Font(bold=True, size=14)
    H2  = Font(bold=True, size=12, color="1F4E79")
    BOLD = Font(bold=True)
    ITAL = Font(italic=True, color="595959")
    ENDO_FILL = PatternFill("solid", fgColor="C6EFCE")   # green
    EXO_FILL  = PatternFill("solid", fgColor="FFD9B3")   # orange
    UNV_FILL  = PatternFill("solid", fgColor="D9D9D9")   # grey
    HEAD_FILL = PatternFill("solid", fgColor="BDD7EE")   # blue

    r = 1
    def line(text, font=None, fill=None, col=1):
        nonlocal r
        c = ws.cell(row=r, column=col, value=text)
        if font: c.font = font
        if fill: c.fill = fill
        r += 1
        return c

    def rule_row(code, condition, verdict, fill):
        nonlocal r
        vals = [code, condition, verdict]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.fill = fill
            if j == 1:
                c.font = BOLD
        r += 1

    # ================= ENGLISH =================
    line("Classification & Conflict-Resolution Rules", H1); r += 1
    line("How the single `classification` label is decided when databases disagree "
         "(source: pipeline/classify.py → classify_row_v3).", ITAL); r += 1

    line("Priority order (endogenous-dominant — first matching rule wins):", H2)
    for j, h in enumerate(["Rule", "Condition", "Verdict"], start=1):
        c = ws.cell(row=r, column=j, value=h); c.font = BOLD; c.fill = HEAD_FILL
    r += 1
    rule_row("E0", "Detected in real mouse tissue (MMMDB, >=1 tissue)", "endogenous", ENDO_FILL)
    rule_row("E1", "ChEBI role contains 'human metabolite'", "endogenous", ENDO_FILL)
    rule_row("E2", "HMDB source contains 'Endogenous'", "endogenous", ENDO_FILL)
    rule_row("E3", "COCONUT organisms contain Homo sapiens", "endogenous", ENDO_FILL)
    rule_row("X1", "HMDB source is Exogenous/Food/Drug/Microbial/Plant/Toxin/Cosmetic (no Endogenous)", "exogenous", EXO_FILL)
    rule_row("X2", "ChEBI roles present, but none is 'human metabolite'", "exogenous", EXO_FILL)
    rule_row("X3", "COCONUT organisms present, but non-human only", "exogenous", EXO_FILL)
    rule_row("U",  "None of the above (no organism/role/tissue evidence)", "unverified", UNV_FILL)
    r += 1

    line("Tie-break: the FIRST matching endogenous rule (E0>E1>E2>E3) is applied "
         "before any exogenous rule. So a compound with COCONUT=exogenous, "
         "ChEBI=endogenous, HMDB=exogenous is labelled ENDOGENOUS (E1 fires first), "
         "even though 2 of 3 sources say exogenous.", None); r += 1

    line("Why endogenous-dominant? (two principles):", H2)
    line("  1. A positive endogenous signal is a specific, curated assertion "
         "(e.g. ChEBI's 'human metabolite' role, or actual tissue detection in MMMDB). "
         "An exogenous verdict is often inferred from the ABSENCE of such a signal, "
         "which is weaker evidence.", None)
    line("  2. Conflicts are never silently merged away. The final single label is a "
         "convenience; `conflict_flag` (True/False) and `conflicting_sources` "
         "(e.g. 'ChEBI=endogenous;HMDB=exogenous') preserve the full disagreement "
         "for audit.", None); r += 1

    line("conflict_flag = True  when at least one source votes endogenous AND at least "
         "one votes exogenous (MMMDB tissue detection counts as an endogenous vote).", None)
    line("conflicting_sources  lists each source's independent verdict, sorted, e.g. "
         "'ChEBI=endogenous;COCONUT=exogenous;HMDB=exogenous'.", None); r += 2

    # ================= KOREAN =================
    line("분류 · 충돌 해소 규칙 (한국어)", H1); r += 1
    line("데이터베이스 간 기원 판정이 엇갈릴 때 단일 `classification` 라벨을 어떻게 "
         "정하는가 (출처: pipeline/classify.py → classify_row_v3).", ITAL); r += 1

    line("우선순위 (내인성 우세 — 먼저 걸리는 규칙이 최종값):", H2)
    for j, h in enumerate(["규칙", "조건", "판정"], start=1):
        c = ws.cell(row=r, column=j, value=h); c.font = BOLD; c.fill = HEAD_FILL
    r += 1
    rule_row("E0", "MMMDB에서 실제 쥐 조직에 검출 (조직 1개 이상)", "endogenous", ENDO_FILL)
    rule_row("E1", "ChEBI role에 'human metabolite' 포함", "endogenous", ENDO_FILL)
    rule_row("E2", "HMDB source에 'Endogenous' 포함", "endogenous", ENDO_FILL)
    rule_row("E3", "COCONUT organisms에 Homo sapiens 포함", "endogenous", ENDO_FILL)
    rule_row("X1", "HMDB source가 Exogenous/Food/Drug/Microbial/Plant/Toxin/Cosmetic (Endogenous 없음)", "exogenous", EXO_FILL)
    rule_row("X2", "ChEBI role은 있으나 'human metabolite' 아님", "exogenous", EXO_FILL)
    rule_row("X3", "COCONUT organisms는 있으나 비인간만", "exogenous", EXO_FILL)
    rule_row("U",  "위 근거 전무 (organism/role/조직 정보 없음)", "unverified", UNV_FILL)
    r += 1

    line("Tie-break: 내인성 규칙(E0>E1>E2>E3)이 외인성 규칙보다 먼저 적용된다. "
         "따라서 COCONUT=exogenous, ChEBI=endogenous, HMDB=exogenous인 화합물은 "
         "3개 중 2개가 exogenous라도 E1이 먼저 걸려 ENDOGENOUS로 판정된다.", None); r += 1

    line("왜 내인성 우세인가? (두 원칙):", H2)
    line("  1. 내인성 신호(예: ChEBI의 큐레이션된 'human metabolite' role, MMMDB의 실제 "
         "조직 검출)는 구체적·명시적 근거다. 반면 외인성 판정은 그런 신호의 '부재'에서 "
         "추론되는 경우가 많아 근거가 약하다.", None)
    line("  2. 충돌은 절대 조용히 뭉개지 않는다. 최종 단일 라벨은 편의값일 뿐이며, "
         "`conflict_flag`(True/False)와 `conflicting_sources`(예: "
         "'ChEBI=endogenous;HMDB=exogenous')가 원래의 불일치를 감사용으로 모두 보존한다.", None); r += 1

    line("conflict_flag = True  : endogenous 근거와 exogenous 근거가 동시에 존재할 때 "
         "(MMMDB 조직 검출은 endogenous 표로 계산).", None)
    line("conflicting_sources   : 각 소스의 독립 판정을 정렬해 나열, 예 "
         "'ChEBI=endogenous;COCONUT=exogenous;HMDB=exogenous'.", None)

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 78
    ws.column_dimensions["C"].width = 14