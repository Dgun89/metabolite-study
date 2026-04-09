import requests

def get_cid(name):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON"
    response = requests.get(url)

    if response.status_code == 200:
        cid = response.json()["IdentifierList"]["CID"][0]
        return cid
    else:
        return None

print(get_cid("Glucose"))
print(get_cid("Kynurenic acid"))
print(get_cid("asdf1234"))
