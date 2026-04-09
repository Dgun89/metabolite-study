import requests

cid = "3845"
url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"

response = requests.get(url)
data = response.json()

print(response.status_code)
print(data.keys())

sections = data["Record"]["Section"]
for section in sections:
    if section.get("TOCHeading") == "Names and Identifiers":
        for subsection in section.get("Section", []):
            if subsection.get("TOCHeading") == "Other Identifiers":
                for subsubsection in subsection.get("Section", []):
                    heading = subsubsection.get("TOCHeading")
                    if heading in ["HMDB ID", "KEGG ID"]:
                        for info in subsubsection.get("Information", []):
                            for val in info.get("Value", {}).get("StringWithMarkup", []):
                                print(heading, "→", val.get("String"))


