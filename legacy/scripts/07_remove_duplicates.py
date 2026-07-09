import pandas as pd

df = pd.read_excel("metabolites_step2_KEGG_HMDB.xlsx")

df_clean = df.drop_duplicates(subset='Database ID', keep='first')

len(df)
len(df_clean)
len(df) - len(df_clean)

print(f"Original rows: {len(df)}")
print(f"After deduplication: {len(df_clean)}")
print(f"Removed rows: {len(df) - len(df_clean)}")

df_clean.to_excel("metabolites_dropDuplicates.xlsx", index=False)