import openpyxl
wb = openpyxl.load_workbook("metabolites_step2_KEGG_HMDB.xlsx")
ws = wb.active

full = 0  # all three mapped
partial = 0  # partially mapped
pubchem_only = 0  # PubChem only
unresolved = 0  # nothing mapped  

for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
    kegg = row[2]  # Column C
    hmdb = row[3]  # Column D
    pubchem = row[4]  # Column E

    if pubchem is None:
        unresolved += 1
    elif kegg is not None and hmdb is not None:
        full += 1
    elif kegg is None and hmdb is None:
        pubchem_only += 1
    else:
        partial += 1

print(f"fully mapped (all 3): {full}")
print(f"partially mapped: {partial}")
print(f"PubChem Only: {pubchem_only}")
print(f"unresolved: {unresolved}")
print(f"total: {full+partial+pubchem_only+unresolved}")

kegg_only = 0
hmdb_only = 0

for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
    kegg    = row[2]
    hmdb    = row[3]

    if kegg is not None and hmdb is None:
        kegg_only += 1
    elif kegg is None and hmdb is not None:
        hmdb_only += 1

print(f"KEGG only: {kegg_only}")
print(f"HMDB only: {hmdb_only}")