"""
9단계: legacy 신뢰성 대조 (공통 InChIKey 교집합).

이 프로젝트의 핵심 세일즈포인트: 기존 legacy 산출물(metabolites_step29.xlsx, 902개
수기 큐레이션 DB)을, 새 InChIKey 정규화 파이프라인으로 **처음부터 독립 재현**한
legacy_final.xlsx와 대조해 legacy DB의 신뢰성을 재검증한다.

대조 1 (핵심): reproduced legacy_final.xlsx  vs  기존 legacy/etc/metabolites_step29.xlsx
대조 2 (종간): human/mouse_final.xlsx        vs  기존 step29

각 대조에서:
- 공통 InChIKey(full 27자 + skeleton 14자) 교집합 추출
- classification / 외부 식별자 / 효소 플래그 일치율 계산

결과: data/export/comparison_report.md + data/export/legacy_comparison.png
경로는 config(이식성) 사용, 환경변수로 오버라이드 가능.
"""
import sys, re, glob
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config as C

pat = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

def find_legacy():
    for p in ["legacy/etc/metabolites_step29.xlsx", "legacy/data/metabolites_step29.xlsx",
              "legacy/final/metabolites_step29.xlsx"]:
        fp = C.BASE / p
        if fp.exists():
            return str(fp)
    hits = glob.glob(str(C.BASE / "**" / "*step29*.xlsx"), recursive=True)
    return hits[0] if hits else None

def clean_ik(series):
    return series.map(lambda x: str(x).strip().upper() if pd.notna(x) else "")

def has_val(x):
    return pd.notna(x) and str(x).strip() != "" and str(x).strip().lower() != "nan"

def norm_id(x):
    """float 문자열 '16176.0' -> '16176', 'CHEBI:16176' -> '16176'."""
    if not has_val(x):
        return None
    s = str(x).strip().upper().replace("CHEBI:", "")
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except ValueError:
        pass
    return s

def load_valid(path, sheet=0):
    df = pd.read_excel(path, sheet_name=sheet)
    df["ik"] = clean_ik(df["InChIKey"])
    df = df[df["ik"].map(lambda x: bool(pat.match(x)))].copy()
    return df

def compare(new_df, leg_df, key="ik"):
    if key == "sk":
        new_df = new_df.assign(sk=new_df["ik"].str[:14])
        leg_df = leg_df.assign(sk=leg_df["ik"].str[:14])
    nu = new_df.drop_duplicates(key).set_index(key)
    lu = leg_df.drop_duplicates(key).set_index(key)
    common = sorted(set(nu.index) & set(lu.index))
    n = len(common)
    cls = sum(str(nu.loc[s, "classification"]).strip().lower()
              == str(lu.loc[s, "classification"]).strip().lower() for s in common)
    ids = {}
    for c in ["PubChem", "KEGG", "HMDB", "ChEBI"]:
        both = va = 0
        for s in common:
            nv, lv = norm_id(nu.loc[s, c]), norm_id(lu.loc[s, c])
            if nv and lv:
                both += 1
                va += (nv == lv)
        ids[c] = (both, va)
    enz = {}
    for c in ["kegg_enzymes", "hmdb_enzymes", "reactome_catalysts", "brenda_enzymes"]:
        enz[c] = sum(has_val(nu.loc[s, c]) == has_val(lu.loc[s, c]) for s in common)
    return dict(n=n, cls=cls, ids=ids, enz=enz)

def _pct(a, b):
    return f"{a}/{b} ({a/b*100:.1f}%)" if b else f"{a}/{b} (n/a)"


def run():
    lp = find_legacy()
    assert lp, "legacy step29 xlsx not found under legacy/{etc,data,final}/"
    leg = load_valid(lp)
    export = C.EXPORT_DIR

    # 대조 대상: reproduced mouse_feces(핵심 — 구 legacy) + human/mouse_serum(종간)
    targets = [("mouse_feces", "재현 mouse_feces(쥐 분변) vs 기존 step29 (핵심 신뢰성 검증)"),
               ("human_serum", "human_serum vs 기존 step29"),
               ("mouse_serum", "mouse_serum(쥐 혈청) vs 기존 step29")]

    results = {}
    for sp, _desc in targets:
        fp = export / f"{sp}_final.xlsx"
        if not fp.exists():
            print(f"  [skip] {fp} 없음")
            continue
        new = load_valid(str(fp), sheet="Sheet1")
        results[sp] = {name: compare(new, leg, key)
                       for key, name in [("ik", "full"), ("sk", "skeleton")]}
        for name in ("full", "skeleton"):
            r = results[sp][name]
            print(f"{sp} {name}: n={r['n']} cls={_pct(r['cls'], r['n'])}")

    # ---------- 리포트 ----------
    lines = ["# Legacy 신뢰성 대조 리포트", "",
             f"- 기준(baseline): `{Path(lp).relative_to(C.BASE)}` — 기존 수기 큐레이션 DB",
             f"- 대조(reproduced): `data/export/{{species}}_final.xlsx` — 새 InChIKey 정규화 파이프라인 재현",
             f"- 대조 축: 공통 InChIKey 교집합 (full 27자 / skeleton 14자)", "",
             "분류 라벨(endogenous/exogenous/unverified) 일치율과 외부 식별자·효소 커버리지 일치를 계산한다.",
             ""]
    for sp, desc in targets:
        if sp not in results:
            continue
        lines += [f"## {sp} — {desc}", ""]
        for name in ("full", "skeleton"):
            r = results[sp][name]
            lines += [f"### InChIKey {name} 교집합 (n={r['n']})", "",
                      f"- **classification 일치**: {_pct(r['cls'], r['n'])}", "",
                      "| 외부 ID | 양쪽 보유 | 값 일치 |", "|---|---|---|"]
            for c, (both, va) in r["ids"].items():
                lines.append(f"| {c} | {both} | {_pct(va, both)} |")
            lines += ["", "| 효소 소스 | 유무 플래그 일치 |", "|---|---|"]
            for c, v in r["enz"].items():
                lines.append(f"| {c} | {_pct(v, r['n'])} |")
            lines.append("")

    report = export / "comparison_report.md"
    export.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n리포트 → {report.relative_to(C.BASE)}")

    # ---------- 그림 ----------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        sps = [sp for sp, _ in targets if sp in results]
        fig, ax = plt.subplots(figsize=(7, 4.2))
        x = range(len(sps))
        cls_full = [results[sp]["full"]["cls"] / results[sp]["full"]["n"] * 100
                    if results[sp]["full"]["n"] else 0 for sp in sps]
        n_full = [results[sp]["full"]["n"] for sp in sps]
        bars = ax.bar(x, cls_full, color=["#2c7fb8", "#7fcdbb", "#c7e9b4"][:len(sps)])
        ax.set_xticks(list(x))
        ax.set_xticklabels([f"{sp}\n(n={n})" for sp, n in zip(sps, n_full)])
        ax.set_ylabel("classification agreement (%)")
        ax.set_ylim(0, 105)
        ax.set_title("Legacy reliability: reproduced vs step29 baseline\n(full InChIKey intersection)")
        for b, v in zip(bars, cls_full):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%",
                    ha="center", va="bottom", fontsize=10)
        fig.tight_layout()
        figp = export / "legacy_comparison.png"
        fig.savefig(figp, dpi=150)
        print(f"그림 → {figp.relative_to(C.BASE)}")
    except Exception as e:
        print(f"  [그림 생략] {e}")

    return results


if __name__ == "__main__":
    run()
