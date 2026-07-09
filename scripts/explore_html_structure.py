with open("Annotation_ヒト血清.html", encoding="utf-8") as f:
    html = f.read()

print("smiles 있음:", "smiles" in html.lower())