# ────────────────────────────────────────────────────────
# 1. 19-1_fill_hmdb_classification_all.py
# ────────────────────────────────────────────────────────
import xml.etree.ElementTree as ET
import pandas as pd

INPUT_FILE  = "metabolites_step18.xlsx"
OUTPUT_FILE = "metabolites_step19-1.xlsx"
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
# 3. filter_status 전체 업데이트
# ─────────────────────────────
df['hmdb_source'] = ""

for idx, row in df.iterrows():
    hmdb_id = str(row['HMDB']) if pd.notna(row['HMDB']) else ""
    if hmdb_id in hmdb_source_map:
        source = hmdb_source_map[hmdb_id]
        df.at[idx, 'hmdb_source'] = source

        # 조건 없이 전체 업데이트
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