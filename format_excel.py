from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date

GROUPS = {
    "Basic Identifiers": {
        "columns": ["Database ID", "compound_name", "InChIKey", "SMILES"],
        "color": "BDD7EE",
        "description": "Core compound identifiers"
    },
    "External DB IDs": {
        "columns": ["PubChem", "KEGG", "HMDB", "ChEBI"],
        "color": "C6EFCE",
        "description": "Cross-reference IDs from external databases"
    },
    "Classification": {
        "columns": ["compound_origin", "hmdb_origin"],
        "color": "FFEB9C",
        "description": "Endogenous/exogenous classification"
    },
    "Origin Evidence": {
        "columns": ["coconut_organisms", "coconut_match_key", "origin_evidence"],
        "color": "E4DFEC",
        "description": "Provenance / audit trail behind compound_origin"
    },
    "Enzyme Information": {
        "columns": ["kegg_enzymes", "hmdb_enzymes", "reactome_catalysts", "brenda_enzymes"],
        "color": "FCE4D6",
        "description": "Enzyme data from multiple databases"
    }
}

COL_SOURCE = {
        "Database ID"        : "COCONUT",
    "compound_name"      : "COCONUT",
    "InChIKey"           : "PubChem",
    "SMILES"             : "PubChem",
    "PubChem"            : "PubChem",
    "KEGG"               : "KEGG",
    "HMDB"               : "HMDB",
    "ChEBI"              : "ChEBI",
    "compound_origin"    : "ChEBI + HMDB",
    "hmdb_origin"        : "HMDB",
    "kegg_enzymes"       : "KEGG",
    "hmdb_enzymes"       : "HMDB",
    "reactome_catalysts" : "Reactome",
    "brenda_enzymes"     : "BRENDA",
    "coconut_organisms"  : "COCONUT",
    "coconut_match_key"  : "COCONUT",
    "origin_evidence"    : "COCONUT", 
}

COL_DESC = {
    "Database ID"        : "COCONUT compound ID",
    "compound_name"      : "Compound name",
    "InChIKey"           : "Chemical structure key (27-char)",
    "SMILES"             : "Chemical structure in text format",
    "PubChem"            : "PubChem Compound ID (CID)",
    "KEGG"               : "KEGG Compound ID",
    "HMDB"               : "Human Metabolome Database ID",
    "ChEBI"              : "Chemical Entities of Biological Interest ID",
    "compound_origin"    : "Final classification: endogenous / exogenous / unverified",
    "hmdb_origin"        : "HMDB source field (Endogenous / Food / Drug etc.)",
    "coconut_organisms"  : "Producing organisms from COCONUT used to infer origin",
    "coconut_match_key"  : "COCONUT match method: inchikey / inchikey_skeleton / cnp_id",
    "origin_evidence"    : "Reason behind compound_origin (e. g. COCONUT: Homo sapiens / non-human / no organism data / not in release)",
    "kegg_enzymes"       : "EC numbers from KEGG (semicolon-separated)",
    "hmdb_enzymes"       : "Enzyme gene names from HMDB (semicolon-separated)",
    "reactome_catalysts" : "Catalyst activity names from Reactome",
    "brenda_enzymes"     : "EC numbers from BRENDA (semicolon-separated; source: BRENDA Enzyme Database)",
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

    # 헤더 볼드 + 배경색
    for cell in ws[1]:
        col_name = cell.value
        color = col_color.get(col_name, "FFFFFF")
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

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
        ("Classification", "Endogenous",      (df['compound_origin']=='endogenous').sum(), f"{(df['compound_origin']=='endogenous').sum()/total*100:.1f}%"),
        ("Classification", "Exogenous",       (df['compound_origin']=='exogenous').sum(),  f"{(df['compound_origin']=='exogenous').sum()/total*100:.1f}%"),
        ("Classification", "Unverified",      (df['compound_origin']=='unverified').sum(), f"{(df['compound_origin']=='unverified').sum()/total*100:.1f}%"),
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

    if 'origin_evidence' in df.columns:
        ev = df['origin_evidence'].astype(str)
        def cnt(key): return int(ev.str.contains(key, case=False, na=False).sum())
        rows += [
            ("Origin Evidence", "Reclassified → endogenous", cnt('Homo sapiens'), f"{cnt('Homo sapiens')/total*100:.1f}%"),
            ("Origin Evidence", "Reclassified → exogenous", cnt('non-human'), f"{cnt('non-human')/total*100:.1f}%"),
            ("Origin Evidence", "Unverified: no organism data", cnt('no organism'), f"{cnt('no organism')/total*100:.1f}%"),
            ("Origin Evidence", "Unverified: not in COCONUT", cnt('not in release'), f"{cnt('not in release')/total*100:.1f}%"),
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

    wb.save(filepath)
    print(f"포맷 적용 완료: {filepath}")