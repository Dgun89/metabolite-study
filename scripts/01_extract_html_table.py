import re, json5
import pandas as pd
from pathlib import Path

# ===== 여기 한 줄만 바꾸기 =====
SPECIES = "mouse" # 또는 "human"
# ============================

BASE = Path(r"C:\dev\metabolite-study")

# 종별 설정
CONFIG = {
    "human": {
        "html": "Annotation_ヒト血清.html",
        "output": "annotation_output_hito.xlsx",
    },
    "mouse": {
        "html": "Annotation_マウス血清.html",
        "output": "annotation_output_mouse.xlsx",
    },
}

# 경로 조립
raw_dir = BASE / "data" / SPECIES / "raw"
html_path = raw_dir / CONFIG[SPECIES]["html"]
output_path = raw_dir / CONFIG[SPECIES]["output"]

# 1. 파일 읽기
with open(html_path, encoding="utf-8") as f:
    html = f.read()

# 2. rowData 배열 부분만 추출
idx = html.find("rowData")
match = re.search(r"rowData\s*=\s*(\[.*?\])\s*;", html[idx:], re.DOTALL)

# 3. json5로 파싱 (따옴표 없는 키 허용)
data = json5.loads(match.group(1))
df = pd.DataFrame(data)

print("처리 대상:", SPECIES)
print("원본:", df.shape)
print("열 목록:", list(df.columns))

# 4. 무거운 이미지 열(structure) 제거
if "structure" in df.columns:
    df = df.drop(columns=["structure"])

# 5. 엑셀로 저장
df.to_excel(output_path, index=False)
print("저장 완료:", df.shape)
print("저장 위치:", output_path)
print(df.head())
