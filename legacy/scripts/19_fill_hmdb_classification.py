##### 1. test HMDB origin field #####
# import requests

# headers = {"User-Agent": "Mozilla/5.0"}
# resp = requests.get(
#     "https://hmdb.ca/metabolites/HMDB0000715.xml",
#     headers=headers
# )
# print(resp.status_code)
# print(resp.text[:500])

##### 2. Test Metabolomics Workbench classification #####
# import requests

# resp = requests.get(
#     "https://www.metabolomicsworkbench.org/rest/compound/inchi_key/HCZHHEIFKROPDY-UHFFFAOYSA-N/all"
# )
# print(resp.status_code)
# import json
# print(json.dumps(resp.json(), indent=2)[:1000])

##### 3. test HMDB XML parsing (streaming) #####
# import xml.etree.ElementTree as ET

# # 첫 3개만 구조 확인
# count = 0
# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite") and count < 3:
#         accession = elem.findtext("{http://www.hmdb.ca}accession")
#         name = elem.findtext("{http://www.hmdb.ca}name")
#         origin = elem.findtext("{http://www.hmdb.ca}origin")
#         print(f"accession: {accession}")
#         print(f"name: {name}")
#         print(f"origin: {origin}")
#         print()
#         count += 1
#         elem.clear()
#     if count >= 3:
#         break

##### 4. HMDB XML 필드 전체 확인 #####
# import xml.etree.ElementTree as ET

# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         for child in elem:
#             tag = child.tag.split("}")[-1]
#             print(f"{tag}: {str(child.text)[:50] if child.text else None}")
#         elem.clear()
#         break

##### 5. HMDB biological_properties & ontology
# import xml.etree.ElementTree as ET

# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         ns = "{http://www.hmdb.ca}"
        
#         # biological_properties 확인
#         bio = elem.find(f"{ns}biological_properties")
#         if bio is not None:
#             print("=== biological_properties ===")
#             for child in bio:
#                 print(f"  {child.tag.split('}')[-1]}: {str(child.text)[:80]}")
        
#         # ontology 확인
#         onto = elem.find(f"{ns}ontology")
#         if onto is not None:
#             print("\n=== ontology ===")
#             for child in onto:
#                 print(f"  {child.tag.split('}')[-1]}: {str(child.text)[:80]}")
        
#         elem.clear()
#         break

##### 6. HMDB ontology root 내부 확인 #####
##### 굉장히 중요!!!!! #####
# import xml.etree.ElementTree as ET

# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         ns = "{http://www.hmdb.ca}"
#         onto = elem.find(f"{ns}ontology")
#         if onto is not None:
#             for root_elem in onto:
#                 print("--- root ---")
#                 for child in root_elem:
#                     tag = child.tag.split("}")[-1]
#                     print(f"  {tag}: {child.text}")
#                     for grandchild in child:
#                         gtag = grandchild.tag.split("}")[-1]
#                         print(f"    {gtag}: {grandchild.text}")
#         elem.clear()
#         break

##### 7. HMDB Disposition descendants 확인 #####
import xml.etree.ElementTree as ET

for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
    if elem.tag.endswith("metabolite"):
        ns = "{http://www.hmdb.ca}"
        onto = elem.find(f"{ns}ontology")
        if onto is not None:
            for root_elem in onto:
                term = root_elem.findtext(f"{ns}term")
                if term == "Disposition":
                    print("=== Disposition ===")
                    import xml.etree.ElementTree as ET2
                    print(ET.tostring(root_elem, encoding='unicode')[:1000])
        elem.clear()
        break

##### 이것도 굉장히 중요 #####
# ontology
# └── root: Disposition
#     └── descendants
#         └── descendant: Source
#             └── descendants
#                 └── descendant: Endogenous ← 이게 필요한 것!

##### 8. HMDB Source term 추출 테스트 #####
# import xml.etree.ElementTree as ET

# def get_hmdb_source(metabolite_elem, ns):
#     onto = metabolite_elem.find(f"{ns}ontology")
#     if onto is None:
#         return ""
#     for root_elem in onto:
#         term = root_elem.findtext(f"{ns}term")
#         if term == "Disposition":
#             for desc in root_elem.iter(f"{ns}descendant"):
#                 if desc.findtext(f"{ns}term") == "Source":
#                     sources = []
#                     for subdesc in desc.findall(f"{ns}descendants/{ns}descendant"):
#                         t = subdesc.findtext(f"{ns}term")
#                         if t:
#                             sources.append(t)
#                     return ";".join(sources)
#     return ""

# ns = "{http://www.hmdb.ca}"
# count = 0
# for event, elem in ET.iterparse("hmdb_metabolites.xml", events=["end"]):
#     if elem.tag.endswith("metabolite"):
#         accession = elem.findtext(f"{ns}accession")
#         name = elem.findtext(f"{ns}name")
#         source = get_hmdb_source(elem, ns)
#         print(f"{accession} | {name} | {source}")
#         elem.clear()
#         count += 1
#         if count >= 10:
#             break

##### 9. 19_fill_hmdb_classification.py #####
import xml.etree.ElementTree as ET
import pandas as pd

INPUT_FILE  = "metabolites_step18.xlsx"
OUTPUT_FILE = "metabolites_step19.xlsx"
HMDB_XML    = "hmdb_metabolites.xml"
ns = "{http://www.hmdb.ca}"

# ─────────────────────────────
# 1. 대상 HMDB ID 목록 추출
# ─────────────────────────────
df = pd.read_excel(INPUT_FILE)
print(f"입력 행 수: {len(df)}")

hmdb_targets = set(
    df[df['HMDB'].notna()]['HMDB'].astype(str).tolist()
)
print(f"HMDB ID 보유: {len(hmdb_targets)}개")

# ─────────────────────────────
# 2. XML 스트리밍 파싱
# ─────────────────────────────
def get_hmdb_source(metabolite_elem):
    onto = metabolite_elem.find(f"{ns}ontology")
    if onto is None:
        return ""
    for root_elem in onto:
        term = root_elem.findtext(f"{ns}term")
        if term == "Disposition":
            for desc in root_elem.iter(f"{ns}descendant"):
                if desc.findtext(f"{ns}term") == "Source":
                    sources = []
                    for subdesc in desc.findall(f"{ns}descendants/{ns}descendant"):
                        t = subdesc.findtext(f"{ns}term")
                        if t:
                            sources.append(t)
                    return ";".join(sources)
    return ""

print("XML 파싱 중... (시간이 걸릴 수 있습니다)")
hmdb_source_map = {}

for event, elem in ET.iterparse(HMDB_XML, events=["end"]):
    if elem.tag.endswith("metabolite"):
        accession = elem.findtext(f"{ns}accession")
        if accession in hmdb_targets:
            source = get_hmdb_source(elem)
            hmdb_source_map[accession] = source
            print(f"  {accession} → {source}")
        elem.clear()

print(f"\n매칭된 HMDB ID: {len(hmdb_source_map)}개")

# ─────────────────────────────
# 3. filter_status 업데이트
# ─────────────────────────────
df['hmdb_source'] = ""

for idx, row in df.iterrows():
    hmdb_id = str(row['HMDB']) if pd.notna(row['HMDB']) else ""
    if hmdb_id in hmdb_source_map:
        source = hmdb_source_map[hmdb_id]
        df.at[idx, 'hmdb_source'] = source

        # unverified인 경우만 업데이트
        if row['filter_status'] == 'unverified':
            if 'Endogenous' in source:
                df.at[idx, 'filter_status'] = 'endogenous'
            elif source:
                df.at[idx, 'filter_status'] = 'exogenous'

# ─────────────────────────────
# 4. 결과 확인 및 저장
# ─────────────────────────────
print("\n=== 업데이트된 filter_status ===")
print(df['filter_status'].value_counts())

df.to_excel(OUTPUT_FILE, index=False)
print(f"\n저장 완료: {OUTPUT_FILE}")