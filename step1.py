import requests

name = "Kynurenic acid"
url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"

response = requests.get(url)
print(response.status_code)
print(response.json())

cid = response.json()["IdentifierList"]["CID"][0]
print("CID:", cid)
