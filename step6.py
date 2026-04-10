import requests

url = "https://coconut.naturalproducts.net/api/search"
payload = {"query": "Kynurenic acid"}

response = requests.post(url, json=payload)
# print(response.status_code)
# print(response.json())

login_url = "https://coconut.naturalproducts.net/api/auth/login"
credentials = {
    "email": "iszdg99@icloud.com",
    "password": "Th9043bq##"
}

login_response = requests.post(login_url, json=credentials)
# print(login_response.status_code)
# print(login_response.json())

token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}
molecules_url = "https://coconut.naturalproducts.net/api/molecules/CNP0333612"

mol_response = requests.get(molecules_url, headers=headers)
print(mol_response.status_code)
print(mol_response.json())