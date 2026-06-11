# ────────────────────────────────────────────────────────
# 3. 세 가지 DB 중 겹치는 부분 체크
# ────────────────────────────────────────────────────────

import pandas as pd

df = pd.read_excel("metabolites_step21.xlsx")

has_kegg   = df['kegg_enzymes'].notna() & (df['kegg_enzymes'] != "")
has_react  = df['reactome_catalysts'].notna() & (df['reactome_catalysts'] != "")
has_hmdb   = df['hmdb_enzymes'].notna() & (df['hmdb_enzymes'] != "")
has_any    = has_kegg | has_react | has_hmdb

print(f"KEGG만      : {(has_kegg & ~has_react & ~has_hmdb).sum()}")
print(f"HMDB만      : {(~has_kegg & ~has_react & has_hmdb).sum()}")
print(f"Reactome만  : {(~has_kegg & has_react & ~has_hmdb).sum()}")
print(f"중복 포함   : {has_any.sum()}")
print(f"전체 커버리지: {has_any.sum()} / {len(df)}")


# ────────────────────────────────────────────────────────
# 2. 21_extract_enzymes_hmdb.py
# ────────────────────────────────────────────────────────
# import xml.etree.ElementTree as ET
# import pandas as pd

# INPUT_FILE  = "metabolites_step20.xlsx"
# OUTPUT_FILE = "metabolites_step21.xlsx"
# HMDB_XML    = "hmdb_metabolites.xml"
# ns = "{http://www.hmdb.ca}"

# df = pd.read_excel(INPUT_FILE)
# hmdb_targets = set(df[df['HMDB'].notna()]['HMDB'].astype(str).tolist())
# print(f"대상 HMDB ID: {len(hmdb_targets)}개")

# # ─────────────────────────────
# # XML 스트리밍 파싱
# # ─────────────────────────────
# print("XML 파싱 중...")
# hmdb_enzyme_map = {}  # {HMDB_ID: "GENE1;GENE2;..."}

# for event, elem in ET.iterparse(HMDB_XML, events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         accession = elem.findtext(f"{ns}accession")
#         if accession in hmdb_targets:
#             proteins = elem.find(f"{ns}protein_associations")
#             enzymes = []
#             if proteins is not None:
#                 for protein in proteins:
#                     ptype = protein.findtext(f"{ns}protein_type")
#                     gene  = protein.findtext(f"{ns}gene_name")
#                     if ptype == "Enzyme" and gene:
#                         enzymes.append(gene)
#             hmdb_enzyme_map[accession] = ";".join(enzymes)
#             print(f"  {accession} → {len(enzymes)}개 효소")
#         elem.clear()

# print(f"\n매칭된 HMDB ID: {len(hmdb_enzyme_map)}개")

# # ─────────────────────────────
# # 컬럼 추가
# # ─────────────────────────────
# df['hmdb_enzymes'] = ""

# for idx, row in df.iterrows():
#     hmdb_id = str(row['HMDB']) if pd.notna(row['HMDB']) else ""
#     if hmdb_id in hmdb_enzyme_map:
#         df.at[idx, 'hmdb_enzymes'] = hmdb_enzyme_map[hmdb_id]

# filled = df['hmdb_enzymes'].apply(lambda x: x != "").sum()
# print(f"효소 정보 있는 행: {filled} / {len(df)}")

# df.to_excel(OUTPUT_FILE, index=False)
# print(f"저장 완료: {OUTPUT_FILE}")

### HMDB 효소 정보 있는 행: 56 / 902 ###

# ────────────────────────────────────────────────────────
# 1. Test HMDB protein_associations 구조 확인
# ────────────────────────────────────────────────────────
# import xml.etree.ElementTree as ET
# import json

# ns = "{http://www.hmdb.ca}"
# count = 0

# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         accession = elem.findtext(f"{ns}accession")
#         if accession == "HMDB0000715":  # Kynurenic acid
#             proteins = elem.find(f"{ns}protein_associations")
#             if proteins is not None:
#                 for protein in proteins:
#                     print({child.tag.split("}")[1]: child.text for child in protein})
#             elem.clear()
#             break
#         elem.clear()
### 구조 확인 가능 ###
# protein_accession : HMDBP00464
# name              : Kynurenine--oxoglutarate transaminase 1
# uniprot_id        : Q16773
# gene_name         : CCBL1
# protein_type      : Enzyme ← 이것만 필터링