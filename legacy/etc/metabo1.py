import pandas as pd

df = pd.read_excel("metabolites_step19.xlsx")

target = df[
    (df['filter_status'] == 'endogenous') &
    (df['KEGG'].notna()) &
    (df['KEGG'].str.startswith('C'))
]
print(f"대상: {len(target)}개")
target['KEGG'].to_csv("kegg_ids_for_metaboanalyst.txt", index=False, header=False)
print("저장 완료")