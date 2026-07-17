"""
find_species_overlap.py

human_final.xlsx / mouse_final.xlsx 사이에 겹치는 화합물이 있는지 확인.
compare_legacy.py와 동일한 방식(InChIKey full + 14자 skeleton)으로 매칭.

사용법:
    python find_species_overlap.py \
        --human data/human/final/2nd_works_human_final.xlsx \
        --mouse data/mouse/final/2nd_works_mouse_final.xlsx

파일 경로를 안 주면 data/{species}/final/ 안에서 "*_final.xlsx" 패턴으로 자동 검색한다
(예: 2nd_works_human_final.xlsx 처럼 접두사가 붙어도 인식).
결과: overlap_human_mouse.csv (겹치는 화합물 상세) + 콘솔 요약
"""
import argparse
import re
from pathlib import Path

import pandas as pd

IK_PATTERN = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

CANDIDATE_DIRS = {
    "human": ["data/human/final", "final", "."],
    "mouse": ["data/mouse/final", "final", "."],
}


def find_file(species: str, given: str | None) -> str:
    if given:
        fp = Path(given)
        if fp.exists():
            return str(fp)
        raise FileNotFoundError(f"{species}: {given} 을(를) 찾을 수 없습니다.")
    # 정확히 "{species}_final.xlsx"뿐 아니라 "2nd_works_human_final.xlsx"처럼
    # 접두사가 붙은 파일명도 잡히도록 glob 패턴으로 검색
    for d in CANDIDATE_DIRS.get(species, []):
        matches = sorted(Path(d).glob(f"*{species}_final.xlsx"))
        if matches:
            if len(matches) > 1:
                print(f"[안내] {species}: {d} 에서 후보 {len(matches)}개 중 "
                      f"{matches[0].name} 사용 (다른 파일: "
                      f"{', '.join(m.name for m in matches[1:])})")
            return str(matches[0])
    raise FileNotFoundError(
        f"{species}_final.xlsx 를 못 찾았습니다. --{species} 옵션으로 경로를 직접 지정해 주세요."
    )


def clean_ik(series: pd.Series) -> pd.Series:
    return series.map(lambda x: str(x).strip().upper() if pd.notna(x) else "")


def load_valid(path: str, sheet="Sheet1") -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    df["ik"] = clean_ik(df["InChIKey"])
    df = df[df["ik"].map(lambda x: bool(IK_PATTERN.match(x)))].copy()
    df["sk"] = df["ik"].str[:14]
    return df


def summarize_overlap(human: pd.DataFrame, mouse: pd.DataFrame):
    h_full = set(human["ik"])
    m_full = set(mouse["ik"])
    full_common = sorted(h_full & m_full)

    h_sk = set(human["sk"])
    m_sk = set(mouse["sk"])
    sk_common = sorted(h_sk & m_sk)
    # skeleton만 겹치고 full InChIKey는 다른 것(입체이성질체 등)
    sk_only = [s for s in sk_common if s not in {ik[:14] for ik in full_common}]

    return full_common, sk_common, sk_only


def build_report(human: pd.DataFrame, mouse: pd.DataFrame, full_common):
    hu = human.drop_duplicates("ik").set_index("ik")
    mu = mouse.drop_duplicates("ik").set_index("ik")

    rows = []
    for ik in full_common:
        h_row = hu.loc[ik]
        m_row = mu.loc[ik]
        rows.append(
            {
                "InChIKey": ik,
                "human_id": h_row.get("Database ID"),
                "human_name": h_row.get("compound_name"),
                "human_classification": h_row.get("classification"),
                "mouse_id": m_row.get("Database ID"),
                "mouse_name": m_row.get("compound_name"),
                "mouse_classification": m_row.get("classification"),
                "classification_match": str(h_row.get("classification")).strip().lower()
                == str(m_row.get("classification")).strip().lower(),
            }
        )
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human", default=None, help="human_final.xlsx 경로")
    ap.add_argument("--mouse", default=None, help="mouse_final.xlsx 경로")
    ap.add_argument("--out", default="overlap_human_mouse.csv")
    args = ap.parse_args()

    human_path = find_file("human", args.human)
    mouse_path = find_file("mouse", args.mouse)
    print(f"human: {human_path}")
    print(f"mouse: {mouse_path}")

    human = load_valid(human_path)
    mouse = load_valid(mouse_path)

    full_common, sk_common, sk_only = summarize_overlap(human, mouse)

    print("\n=== 요약 ===")
    print(f"human 유효 InChIKey: {len(human)} / mouse 유효 InChIKey: {len(mouse)}")
    print(f"InChIKey 완전 일치(동일 화합물): {len(full_common)}건")
    print(f"  - human 대비 {len(full_common)/len(human)*100:.1f}%")
    print(f"  - mouse 대비 {len(full_common)/len(mouse)*100:.1f}%")
    print(f"14자 skeleton만 일치(입체이성질체 등 가능성): {len(sk_only)}건")

    report = build_report(human, mouse, full_common)
    if not report.empty:
        mismatch = report[~report["classification_match"]]
        print(f"\n겹치는 화합물 중 사람/쥐 분류(endogenous/exogenous/unverified)가 다른 경우: "
              f"{len(mismatch)}/{len(report)}건")
        if not mismatch.empty:
            print(mismatch[["InChIKey", "human_name", "human_classification",
                             "mouse_name", "mouse_classification"]].to_string(index=False))

    report.to_csv(args.out, index=False)
    print(f"\n상세 결과 저장: {args.out}")


if __name__ == "__main__":
    main()