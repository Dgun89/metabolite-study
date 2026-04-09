import requests # 1.라이브러리 불러오기

def get_cid(name): # 2. 함수 정의
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"
    response = requests.get(url)

    if response.status_code == 200:
        cid = response.json()["IdentifierList"]["CID"][0]
        return cid
    else:
        return None

print(get_cid("Glucose")) # 3. 함수 호출
print(get_cid("Kynurenic acid"))
print(get_cid("asdf1234"))
