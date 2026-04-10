import requests

url = "https://coconut.naturalproducts.net/api/search"
payload = {"query": "Kynurenic acid"}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())