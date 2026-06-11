import pandas as pd

df = pd.read_excel("metabolites_step24.xlsx")

def has_value(col):
    return df[col].notna() & (df[col].astype(str).str.strip() != "")

has_kegg     = has_value('kegg_enzymes')
has_hmdb     = has_value('hmdb_enzymes')
has_reactome = has_value('reactome_catalysts')
has_brenda   = has_value('brenda_enzymes')

has_any = has_kegg | has_hmdb | has_reactome | has_brenda
brenda_only = (~has_kegg) & (~has_hmdb) & (~has_reactome) & has_brenda

print(f"KEGG 효소      : {has_kegg.sum()}")
print(f"HMDB 효소      : {has_hmdb.sum()}")
print(f"Reactome      : {has_reactome.sum()}")
print(f"BRENDA        : {has_brenda.sum()}")
print(f"BRENDA만 있는  : {brenda_only.sum()}")
print(f"전체 커버리지  : {has_any.sum()} / 902")
# ────────────────────────────────────────────────────────
# 8. Ligand Structure ID → EC 번호 >> 이거 중요함
# ────────────────────────────────────────────────────────
# import hashlib
# import pandas as pd
# import time
# from zeep import Client, Settings
# from format_excel import apply_format

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()
# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# INPUT_FILE  = "metabolites_step23.xlsx"
# OUTPUT_FILE = "metabolites_step24.xlsx"

# df = pd.read_excel(INPUT_FILE)
# df['brenda_enzymes'] = ""

# found = 0

# for idx, row in df.iterrows():
#     name = str(row['compound_name'])
#     try:
#         # Step 1: 화합물명 → ligandStructureId
#         ligand_id = client.service.getLigandStructureIdByCompoundName(
#             email, password, name
#         )
#         time.sleep(1)

#         if not ligand_id:
#             continue

#         # Step 2: ligandStructureId → EC 번호
#         params2 = (
#             email, password,
#             "ecNumber*",
#             "substrate*",
#             "product*",
#             "commentary*",
#             f"ligandStructureId*{ligand_id}"
#         )
#         result = client.service.getSubstrate(*params2)
#         time.sleep(1)

#         if result:
#             ec_numbers = list(set([r['ecNumber'] for r in result]))
#             df.at[idx, 'brenda_enzymes'] = ";".join(ec_numbers)
#             found += 1
#             print(f"✅ [{idx+1}/902] {name[:35]} → {ec_numbers}")
#         else:
#             print(f"   [{idx+1}/902] {name[:35]} → 없음")

#     except Exception as e:
#         print(f"  [error] {name[:35]}: {e}")
#         time.sleep(1)

# filled = df['brenda_enzymes'].apply(lambda x: x != "").sum()
# print(f"\n결과: {filled} / 902개 brenda_enzymes 확보")

# df.to_excel(OUTPUT_FILE, index=False)
# apply_format(OUTPUT_FILE)
# print(f"저장 완료: {OUTPUT_FILE}")
### brenda_enzymes: 113 / 902 (신규) ###

# ────────────────────────────────────────────────────────
# 7. Ligand Structure ID → EC 번호
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()
# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# # Step 1: 화합물명 → ligandStructureId
# params = (email, password, "Kynurenic acid")
# ligand_id = client.service.getLigandStructureIdByCompoundName(*params)
# print(f"Ligand ID: {ligand_id}")

# # Step 2: ligandStructureId → substrate 조회
# params2 = (
#     email, password,
#     "ecNumber*",
#     "substrate*",
#     "product*",
#     "commentary*",
#     f"ligandStructureId*{ligand_id}"
# )
# result = client.service.getSubstrate(*params2)

# # Step 3: EC 번호만 추출
# if result:
#     ec_numbers = list(set([r['ecNumber'] for r in result]))
#     print(f"EC 번호: {ec_numbers}")
# else:
#     print("결과 없음")
### ID에 따른 EC 번호 출력 정상 작동 ###

# ────────────────────────────────────────────────────────
# 6. 화합물명 → Ligand Structure ID
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()
# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# ligand_id = "1002"  # 아까 확인된 Kynurenic acid ID

# params2 = (
#     email, password,
#     "ecNumber*",
#     "substrate*",
#     "product*",
#     "commentary*",
#     f"ligandStructureId*{ligand_id}"
# )
# result = client.service.getSubstrate(*params2)
# print(result[:1000] if result else "결과 없음")
### 결과정리 하기 참고 > Homo sapiens 필터를 뺐는데 다른 생물종도 나옴. 인간 데이터가 없거나 필터 문제일 수 있음###
# Kynurenic acid (ligandStructureId: 1002)
# → EC 1.14.99.2 (kynurenate monooxygenase)
# → organism: Pseudomonas fluorescens / Pseudomonas sp.

# ────────────────────────────────────────────────────────
# 5. Test getEcNumbersFromSubstrate (파라미터 수정)
# ────────────────────────────────────────────────────────
# import hashlib

# email = BRENDA_EMAIL      # ← 정확한 이메일
# password_raw = BRENDA_PASSWORD  # ← 실제 비밀번호
# password_hashed = hashlib.sha256(password_raw.encode("utf-8")).hexdigest()

# print(f"email: {email}")
# print(f"hashed password: {password_hashed}")
### 해시값이 제대로 나옴 ###

# ────────────────────────────────────────────────────────
# 4. Test getEcNumbersFromSubstrate (파라미터 수정)
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()

# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# # 파라미터를 하나의 문자열로 합치기
# param_str = f"substrate*Kynurenic acid#organism*Homo sapiens#commentary*#literature*"

# result = client.service.getEcNumbersFromSubstrate(email + "#" + password, param_str)
# print(result)
### 이메일 인증이 안 됨 ###

# ────────────────────────────────────────────────────────
# 4. Test getEcNumbersFromSubstrate
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()

# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# parameters = (
#     email, password,
#     "substrate*Kynurenic acid",
#     "organism*Homo sapiens",
#     "commentary*",
#     "literature*"
# )
# result = client.service.getEcNumbersFromSubstrate(*parameters)
# print(result)
### 파라미터 수정이 필요함 ###

# ────────────────────────────────────────────────────────
# 3. BRENDA API 함수 목록 확인
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# # 사용 가능한 서비스 목록 출력
# for service in client.wsdl.services.values():
#     for port in service.ports.values():
#         for op in port.binding._operations.values():
#             print(op.name)
### 함수 목록 확인 후 getEcNumbersFromSubstrate 찾음 ###

# ────────────────────────────────────────────────────────
# 2. Test BRENDA SOAP API
# ────────────────────────────────────────────────────────
# import hashlib
# from zeep import Client, Settings

# wsdl = "https://www.brenda-enzymes.org/soap/brenda_zeep.wsdl"
# email = BRENDA_EMAIL
# password = hashlib.sha256(BRENDA_PASSWORD.encode("utf-8")).hexdigest()

# settings = Settings(strict=False)
# client = Client(wsdl, settings=settings)

# # Kynurenic acid로 테스트 (EC 2.6.1.7)
# parameters = (email, password, "ecNumber*2.6.1.7", "organism*Homo sapiens", "substrate*", "product*", "commentary*", "literature*")
# result = client.service.getSubstrate(*parameters)
# print(result[:500] if result else "결과 없음")
### 파라미터 수가 맞지 않아 진행 불가 ###

# ────────────────────────────────────────────────────────
# 1. Test BRENDA SPARQL endpoint
# ────────────────────────────────────────────────────────
# import requests

# url = "https://sparql.dsmz.de/brenda"

# # 간단한 테스트 쿼리
# query = """
# SELECT ?s ?p ?o WHERE {
#   ?s ?p ?o .
# } LIMIT 5
# """

# resp = requests.post(
#     url,
#     data={"query": query},
#     headers={"Accept": "application/sparql-results+json"}
# )
# print(resp.status_code)
# print(resp.text[:500])
### error code: 403 ###