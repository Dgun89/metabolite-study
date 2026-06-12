##############################################################
# 2026-06-08: PubChem ID cross-validation with MetaboAnalyst #
##############################################################

##### 1. 전체 확인 #####
# import pandas as pd

# df = pd.read_excel("metabolites_step19.xlsx")

# # MetaboAnalyst에서 확인된 매핑
# metabo_check = {
#     "C01717": {"hmdb": "HMDB0000715", "pubchem": "3845"},
#     "C00380": {"hmdb": "HMDB0000630", "pubchem": "597"},
#     "C05135": {"hmdb": "HMDB0013253", "pubchem": "69602"},
#     "C00534": {"hmdb": "HMDB0001431", "pubchem": "1052"},
#     "C00250": {"hmdb": "HMDB0001545", "pubchem": "1050"},
#     "C01029": {"hmdb": "HMDB0002189", "pubchem": "123689"},
#     "C03413": {"hmdb": "HMDB0002172", "pubchem": "132680"},
#     "C10858": {"hmdb": "HMDB0006548", "pubchem": "443003"},
#     "C00242": {"hmdb": "HMDB0000132", "pubchem": "764"},
#     "C00178": {"hmdb": "HMDB0000262", "pubchem": "1135"},
#     "C00445": {"hmdb": "HMDB0001354", "pubchem": "135450599"},
#     "C00147": {"hmdb": "HMDB0000034", "pubchem": "190"},
#     "C00913": {"hmdb": "HMDB0011600", "pubchem": "1673"},
#     "C00780": {"hmdb": "HMDB0000259", "pubchem": "5202"},
#     "C05635": {"hmdb": "HMDB0000763", "pubchem": "1826"},
# }

# print(f"{'KEGG':<10} {'화합물명':<35} {'HMDB일치':<12} {'PubChem일치':<12}")
# print("-" * 70)

# for kegg_id, expected in metabo_check.items():
#     row = df[df['KEGG'] == kegg_id]
#     if row.empty:
#         print(f"{kegg_id:<10} {'미발견':<35} {'❌':<12} {'❌':<12}")
#         continue

#     name = row['QualitativeResults'].values[0]
#     hmdb_match = str(row['HMDB'].values[0]) == expected['hmdb']
#     pubchem_match = str(int(row['PubChem'].values[0])) == expected['pubchem']

#     print(f"{kegg_id:<10} {name:<35} {'✅' if hmdb_match else '❌':<12} {'✅' if pubchem_match else '❌':<12}")

##### 2. 3개가 다른데 왜 다른지 확인 #####
# import pandas as pd

# df = pd.read_excel("metabolites_step19.xlsx")

# mismatches = {
#     "C10858": "443003",
#     "C00242": "764",
#     "C00913": "1673",
# }

# for kegg_id, metabo_pubchem in mismatches.items():
#     row = df[df['KEGG'] == kegg_id]
#     name = row['QualitativeResults'].values[0]
#     our_pubchem = str(int(row['PubChem'].values[0]))
#     print(f"{name} ({kegg_id})")
#     print(f"  우리 DB    : {our_pubchem}")
#     print(f"  MetaboAnalyst: {metabo_pubchem}")
#     print()

##### 3. PubChem API로 두 CID를 직접 조회: 3가지 화합물 #####
# import requests

# #cids = {"우리 DB (91460)": "91460", "MetaboAnalyst (443003)": "443003"}
# #cids = {"우리 DB (135398634)": "135398634", "MetaboAnalyst (764)": "764"}
# #cids = {"우리 DB (135398661)": "135398661", "MetaboAnalyst (1673)": "1673"}

# for label, cid in cids.items():
#     resp = requests.get(
#         f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/IUPACName,MolecularFormula,InChIKey/JSON"
#     )
#     data = resp.json()['PropertyTable']['Properties'][0]
#     print(f"{label}")
#     print(f"  IUPACName : {data.get('IUPACName')}")
#     print(f"  Formula   : {data.get('MolecularFormula')}")
#     print(f"  InChIKey  : {data.get('InChIKey')}")
#     print()

# import pandas as pd

# df = pd.read_excel("metabolites_step19.xlsx")

# # 수정 전 확인
# row = df[df['KEGG'] == 'C00913']
# print(f"수정 전: {row['QualitativeResults'].values[0]} → PubChem {row['PubChem'].values[0]}")

# # 수정
# df.loc[df['KEGG'] == 'C00913', 'PubChem'] = 1673

# # 수정 후 확인
# row = df[df['KEGG'] == 'C00913']
# print(f"수정 후: {row['QualitativeResults'].values[0]} → PubChem {row['PubChem'].values[0]}")

# df.to_excel("metabolites_step19.xlsx", index=False)
# print("저장 완료")

##### 엑셀 칼럼 재정렬을 위한 칼럼 조회 #####
# import pandas as pd

# df = pd.read_excel("metabolites_step21.xlsx")
# print(df.columns.tolist())
# print(f"행 수: {len(df)}")
### 정렬결과는 아래의 코드에 맞춰서 ###

##### 엑셀 칼럼 재정렬 코드 #####
# import pandas as pd

# df = pd.read_excel("metabolites_step21.xlsx")

# # 컬럼명 변경
# df = df.rename(columns={
#     'QualitativeResults': 'compound_name',
#     'chebi_id'          : 'ChEBI',
#     'hmdb_source'       : 'hmdb_origin'
# })

# # 컬럼 순서 재배치
# new_order = [
#     # 기본 식별자
#     'Database ID', 'compound_name', 'InChIKey', 'SMILES',
#     # 외부 DB ID
#     'PubChem', 'KEGG', 'HMDB', 'ChEBI',
#     # 분류
#     'filter_status', 'hmdb_origin',
#     # 효소 정보
#     'kegg_enzymes', 'hmdb_enzymes', 'reactome_catalysts'
# ]

# df = df[new_order]

# print("=== 정리된 컬럼 ===")
# for col in df.columns:
#     filled = df[col].notna().sum()
#     print(f"  {col:<25} {filled}/902")

# df.to_excel("metabolites_step21.xlsx", index=False)
# print("\n저장 완료")
### 정렬 완료 ###

###### 칼럼 볼드 처리 #####
# import pandas as pd
# from openpyxl import load_workbook
# from openpyxl.styles import Font

# df = pd.read_excel("metabolites_step21.xlsx")

# # 컬럼명 변경
# df = df.rename(columns={
#     'QualitativeResults': 'compound_name',
#     'chebi_id'          : 'ChEBI',
#     'hmdb_source'       : 'hmdb_origin'
# })

# # 컬럼 순서 재배치
# new_order = [
#     'Database ID', 'compound_name', 'InChIKey', 'SMILES',
#     'PubChem', 'KEGG', 'HMDB', 'ChEBI',
#     'filter_status', 'hmdb_origin',
#     'kegg_enzymes', 'hmdb_enzymes', 'reactome_catalysts'
# ]

# df = df[new_order]

# # 저장
# df.to_excel("metabolites_step21.xlsx", index=False)

# # 헤더 볼드 처리
# wb = load_workbook("metabolites_step21.xlsx")
# ws = wb.active
# for cell in ws[1]:
#     cell.font = Font(bold=True)
# wb.save("metabolites_step21.xlsx")

# print("저장 완료")
### 분류 완료 ###

##### 범례 및 색 구분 #####
# import pandas as pd
# from openpyxl import load_workbook
# from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# df = pd.read_excel("metabolites_step21.xlsx")

# # ─────────────────────────────
# # 그룹 정의
# # ─────────────────────────────
# groups = {
#     "Basic Identifiers": {
#         "columns": ["Database ID", "compound_name", "InChIKey", "SMILES"],
#         "color": "BDD7EE",
#         "description": "Core compound identifiers"
#     },
#     "External DB IDs": {
#         "columns": ["PubChem", "KEGG", "HMDB", "ChEBI"],
#         "color": "C6EFCE",
#         "description": "Cross-reference IDs from external databases"
#     },
#     "Classification": {
#         "columns": ["filter_status", "hmdb_origin"],
#         "color": "FFEB9C",
#         "description": "Endogenous/exogenous classification"
#     },
#     "Enzyme Information": {
#         "columns": ["kegg_enzymes", "hmdb_enzymes", "reactome_catalysts"],
#         "color": "FCE4D6",
#         "description": "Enzyme data from multiple databases"
#     }
# }

# # 컬럼 → 색상 매핑
# col_color = {}
# col_group = {}
# for group, info in groups.items():
#     for col in info["columns"]:
#         col_color[col] = info["color"]
#         col_group[col] = group

# # ─────────────────────────────
# # 저장 후 포맷 적용
# # ─────────────────────────────
# df.to_excel("metabolites_step21.xlsx", index=False)
# wb = load_workbook("metabolites_step21.xlsx")
# ws = wb.active

# # 헤더 컬러 + 볼드
# for cell in ws[1]:
#     col_name = cell.value
#     color = col_color.get(col_name, "FFFFFF")
#     cell.font = Font(bold=True)
#     cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
#     cell.alignment = Alignment(horizontal="center")

# # 컬럼 너비 자동 조정
# for col in ws.columns:
#     max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
#     ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

# # ─────────────────────────────
# # Legend 시트 추가
# # ─────────────────────────────
# legend_ws = wb.create_sheet("Legend")

# # 타이틀
# legend_ws["A1"] = "Metabolite Database — Column Legend"
# legend_ws["A1"].font = Font(bold=True, size=13)
# legend_ws.merge_cells("A1:D1")

# headers = ["Group", "Color", "Column", "Description"]
# header_colors = {"Group": "D9D9D9", "Color": "D9D9D9",
#                  "Column": "D9D9D9", "Description": "D9D9D9"}

# for i, h in enumerate(headers, 1):
#     cell = legend_ws.cell(row=3, column=i, value=h)
#     cell.font = Font(bold=True)
#     cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

# col_desc = {
#     "Database ID"        : "COCONUT compound ID",
#     "compound_name"      : "Compound name",
#     "InChIKey"           : "Chemical structure key (27-char)",
#     "SMILES"             : "Chemical structure in text format",
#     "PubChem"            : "PubChem Compound ID (CID)",
#     "KEGG"               : "KEGG Compound ID",
#     "HMDB"               : "Human Metabolome Database ID",
#     "ChEBI"              : "Chemical Entities of Biological Interest ID",
#     "filter_status"      : "endogenous / exogenous / unverified",
#     "hmdb_origin"        : "HMDB source field (Endogenous / Food / Drug etc.)",
#     "kegg_enzymes"       : "EC numbers from KEGG (semicolon-separated)",
#     "hmdb_enzymes"       : "Enzyme gene names from HMDB (semicolon-separated)",
#     "reactome_catalysts" : "Catalyst activity names from Reactome",
# }

# row = 4
# for group, info in groups.items():
#     for col in info["columns"]:
#         legend_ws.cell(row=row, column=1, value=group)
#         color_cell = legend_ws.cell(row=row, column=2, value="")
#         color_cell.fill = PatternFill(
#             start_color=info["color"],
#             end_color=info["color"],
#             fill_type="solid"
#         )
#         legend_ws.cell(row=row, column=3, value=col)
#         legend_ws.cell(row=row, column=4, value=col_desc.get(col, ""))
#         row += 1

# # Legend 컬럼 너비
# legend_ws.column_dimensions["A"].width = 22
# legend_ws.column_dimensions["B"].width = 10
# legend_ws.column_dimensions["C"].width = 25
# legend_ws.column_dimensions["D"].width = 50

# wb.save("metabolites_step21.xlsx")
# print("저장 완료 — 컬러 헤더 + Legend 시트 추가됨")

# validate.py
# Cross-validation and data correction utilities

# import pandas as pd
# from format_excel import apply_format

# # ────────────────────────────────────────────────────────
# # 2026-06-08: PubChem ID cross-validation with MetaboAnalyst
# # ────────────────────────────────────────────────────────

# # ────────────────────────────────────────────────────────
# # 2026-06-09: filter_status → compound_origin 컬럼명 변경
# # ────────────────────────────────────────────────────────
# TARGET_FILE = "metabolites_step23.xlsx"

# df = pd.read_excel(TARGET_FILE)
# df = df.rename(columns={'filter_status': 'compound_origin'})
# df.to_excel(TARGET_FILE, index=False)
# apply_format(TARGET_FILE)
# print("compound_origin 컬럼명 변경 완료")
"""
이게 진짜
"""
# import pandas as pd
# from format_excel import apply_format

# # ────────────────────────────────────────────────────────
# # 2026-06-08: PubChem ID cross-validation with MetaboAnalyst
# # ────────────────────────────────────────────────────────

# # ────────────────────────────────────────────────────────
# # 2026-06-09: filter_status → compound_origin 컬럼명 변경
# # ────────────────────────────────────────────────────────

# # ────────────────────────────────────────────────────────
# # 2026-06-10: brenda_enzymes 추가 후 포맷 재적용
# # ────────────────────────────────────────────────────────
# apply_format("metabolites_step25.xlsx")
# print("포맷 적용 완료")

# import pandas as pd

# df = pd.read_excel("metabolites_step24.xlsx")

# def hv(col):
#     return df[col].notna() & (df[col].astype(str).str.strip() != "")

# has_kegg     = hv('kegg_enzymes')
# has_hmdb     = hv('hmdb_enzymes')
# has_reactome = hv('reactome_catalysts')
# has_brenda   = hv('brenda_enzymes')

# combos = {
#     "KEGG + HMDB":              (has_kegg  & has_hmdb  & ~has_reactome & ~has_brenda).sum(),
#     "KEGG + Reactome":          (has_kegg  & ~has_hmdb & has_reactome  & ~has_brenda).sum(),
#     "KEGG + BRENDA":            (has_kegg  & ~has_hmdb & ~has_reactome & has_brenda).sum(),
#     "HMDB + Reactome":          (~has_kegg & has_hmdb  & has_reactome  & ~has_brenda).sum(),
#     "HMDB + BRENDA":            (~has_kegg & has_hmdb  & ~has_reactome & has_brenda).sum(),
#     "Reactome + BRENDA":        (~has_kegg & ~has_hmdb & has_reactome  & has_brenda).sum(),
#     "KEGG + HMDB + Reactome":   (has_kegg  & has_hmdb  & has_reactome  & ~has_brenda).sum(),
#     "KEGG + HMDB + BRENDA":     (has_kegg  & has_hmdb  & ~has_reactome & has_brenda).sum(),
#     "KEGG + Reactome + BRENDA": (has_kegg  & ~has_hmdb & has_reactome  & has_brenda).sum(),
#     "HMDB + Reactome + BRENDA": (~has_kegg & has_hmdb  & has_reactome  & has_brenda).sum(),
#     "전체 4개":                  (has_kegg  & has_hmdb  & has_reactome  & has_brenda).sum(),
# }

# for combo, count in combos.items():
#     if count > 0:
#         print(f"{combo}: {count}개")

##### HMDB 검증 #####
# import pandas as pd
# df = pd.read_excel('metabolites_step25.xlsx', sheet_name=0)
# unv = df[df['compound_origin']=='unverified']
# print('unverified 총:', len(unv))
# print('HMDB 보유:', unv['HMDB'].notna().sum())
# print('HMDB 없음:', unv['HMDB'].isna().sum())
# print(unv[unv['HMDB'].notna()][['compound_name','HMDB','hmdb_origin']].head(5).to_string())
### 검증 결과 하기 참고 ###
"""
unverified 총: 476
HMDB 보유: 22
HMDB 없음: 454
                                                                        compound_name         HMDB hmdb_origin
15                                                                            Creatol  HMDB0244988         NaN
23   2(3H)-Furanone, 3-ethyldihydro-4-[(1-methyl-1H-imidazol-5-yl)methyl]-, (3S-cis)-  HMDB0243539         NaN
104                        1-(2-Hydroxyethyl)-2-(hydroxymethyl)piperidine-3,4,5-triol  HMDB0243780         NaN
171                                                       5-Hydroxy-1-methylhydantoin  HMDB0246800         NaN
196                                                                 2,8-Quinolinediol  HMDB0240311         NaN
"""

##### HMDB 재조회 #####
# import pandas as pd
# import xml.etree.ElementTree as ET

# df = pd.read_excel('metabolites_step25.xlsx', sheet_name=0)
# unv = df[df['compound_origin']=='unverified']
# hmdb_ids = set(unv[unv['HMDB'].notna()]['HMDB'].tolist())

# ns = '{http://www.hmdb.ca}'
# found = 0
# for event, elem in ET.iterparse('hmdb_metabolites.xml', events=['end']):
#     if elem.tag == f'{ns}metabolite':
#         acc = elem.findtext(f'{ns}accession')
#         if acc in hmdb_ids:
#             origin = elem.findtext(f'{ns}origin') or elem.findtext(f'{ns}biospecimen_locations') or '없음'
#             name = elem.findtext(f'{ns}name')
#             print(f"{acc} | {name} | {origin[:60]}")
#             found += 1
#         elem.clear()
#         if found == 22:
#             break
        
### 조회 결과 하기 참고 ###
"""
HMDB0028739 | Asparaginyl-Proline | 없음
HMDB0028744 | Asparaginyl-Valine | 없음
HMDB0028765 | Aspartyl-Tyrosine | 없음
HMDB0028783 | Cysteinyl-Proline | 없음
HMDB0028914 | Isoleucyl-Phenylalanine | 없음
HMDB0028934 | Leucyl-Lysine | 없음
HMDB0028981 | Methionyl-Proline | 없음
HMDB0240311 | 2,8-Quinolinediol | 없음
HMDB0242128 | 2-Aminoheptanoic acid | 없음
HMDB0243539 | (+)-Isopilocarpine | 없음
HMDB0243678 | (R)-Equol | 없음
HMDB0243780 | 1-(2-Hydroxyethyl)-2-(hydroxymethyl)piperidine-3,4,5-triol | 없음
HMDB0244988 | 5-Hydroxy-2-imino-1-methylimidazolidin-4-one | 없음
HMDB0246205 | [(2R,3R,4S,5S)-3,4,5,6-Tetrahydroxyoxan-2-yl]methyl dihydrogen phosphate | 없음
HMDB0246800 | 5-Hydroxy-1-methylhydantoin | 없음
HMDB0252569 | Gabexate | 없음
HMDB0252604 | Gamabufotalin | 없음
HMDB0253104 | Heptaminol | 없음
HMDB0254052 | levomedetomidine | 없음
HMDB0257557 | (2R,5S)-2-(6-Aminopurin-9-yl)-5-(methylsulfanylmethyl)oxolane-3,4-diol | 없음
HMDB0257923 | 2-[(3alpha,7alpha,12alpha-Trihydroxy-24-oxocholane-24-yl)amino]ethanesulfonic acid | 없음
HMDB0258242 | Ser-Leu | 없음
"""

##### ChEBI ID, InChIKey 보유 현황 체크 #####
import pandas as pd
df = pd.read_excel('metabolites_step25.xlsx', sheet_name=0)
unv = df[df['compound_origin']=='unverified']
print('unverified 총:', len(unv))
print('ChEBI 보유:', unv['ChEBI'].notna().sum())
print('InChIKey 보유:', unv['InChIKey'].notna().sum())
print('ChEBI도 InChIKey도 없음:', (unv['ChEBI'].isna() & unv['InChIKey'].isna()).sum())
