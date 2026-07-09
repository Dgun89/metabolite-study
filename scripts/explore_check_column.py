import pandas as pd

df = pd.read_excel("annotation_output_hito.xlsx")

# # 1. check 값 분포
# print("=== check 분포 ===")
# print(df["check"].value_counts())
# print()

# # 2. 전체 행 수 대비 비율
# print("=== 비율 ===")
# print(df["check"].value_counts(normalize=True))

false_rows = df[df["check"] == False]
true_rows = df[df["check"] == True]

# 3. score 비교
print("=== score 평균 비교 ====")
print("False 행 score 평균:", false_rows["score"].mean())
print("True 행 score 평균:", true_rows["score"].mean())
print()

# 4. blank 검출 비교 (오염 여부)
print("=== blank_ave 평균 비교===")
print("False 행 blank_ave 평균:", false_rows["Blank_ave"].mean())
print("True 행 blank_ave 평균:", true_rows["Blank_ave"].mean())
print()

# 5. false 행 실제로 들여다보기
print("=== False 행 샘플 ===")
print(false_rows[["score", "Blank_ave", "max", "annotation"]].head(10))
