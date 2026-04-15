import pandas as pd
# df = pd.read_excel('metabolites_step10.xlsx')
# df = pd.read_excel('metabolites_step10_ver4.xlsx')
df = pd.read_excel('metabolites_step11.xlsx')

print(f"PubChem + KEGG + HMDB: {len(df[df['KEGG'].notna() & df['HMDB'].notna() & df['PubChem'].notna()])}")
print(f"PubChem + KEGG only: {len(df[df['KEGG'].notna() & df['HMDB'].isna() & df['PubChem'].notna()])}")
print(f"PubChem + HMDB only: {len(df[df['KEGG'].isna() & df['HMDB'].notna() & df['PubChem'].notna()])}")
print(f"PubChem only: {len(df[df['KEGG'].isna() & df['HMDB'].isna() & df['PubChem'].notna()])}")
print(f"Unresolved: {len(df[df['PubChem'].isna()])}")
print(f"Total: {len(df)}")
print(f"\nInChIKey 있는 것: {df['InChIKey'].notna().sum()}")
print(f"InChIKey 없는 것: {df['InChIKey'].isna().sum()}")