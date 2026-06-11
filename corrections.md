# Data Corrections Log

This file documents manual corrections made to the metabolite database, including the reason for each change and the source of the corrected value.

데이터베이스에 적용된 수동 수정 이력을 기록합니다. 각 수정의 원인과 수정값의 출처를 함께 명시합니다.

---

## 2026-06-08

### PubChem CID correction — 3-Methyladenine

| Item | Value |
|------|-------|
| Compound | 3-Methyladenine |
| KEGG ID | C00913 |
| Field | PubChem CID |
| Before | 135398661 |
| After | 1673 |
| File | metabolites_step19.xlsx |

**Reason:**  
During cross-validation with MetaboAnalyst, a PubChem CID mismatch was identified.  
CID 135398661 corresponds to the imine tautomer (3-methyl-7H-purin-6-imine), which is a non-standard representation.  
CID 1673 corresponds to the amine tautomer (3-methylpurin-6-amine), which is the biologically standard form and the canonical entry in PubChem.  
InChIKeys differ between the two entries, confirming they represent structurally distinct tautomers.

**이유:**  
MetaboAnalyst와의 교차 검증 중 PubChem CID 불일치가 발견되었습니다.  
CID 135398661은 이민 호변이성질체(3-methyl-7H-purin-6-imine)로, 비표준 표현형입니다.  
CID 1673은 아민 호변이성질체(3-methylpurin-6-amine)로, 생물학적 표준 형태이자 PubChem의 canonical 항목입니다.  
두 항목의 InChIKey가 다르며, 이는 구조적으로 구별되는 호변이성질체임을 확인해줍니다.

**Source of correction / 수정 출처:** MetaboAnalyst compound ID mapping (https://www.metaboanalyst.ca/)

---

## Notes on other reviewed compounds / 기타 검토 화합물 (2026-06-08)

| Compound | Our CID | MetaboAnalyst CID | Verdict | 판정 |
|----------|---------|-------------------|---------|------|
| Ekgonin | 91460 | 443003 | Acceptable — same compound, different stereoisomer specification | 허용 — 동일 화합물, 입체이성질체 표현 차이 |
| Guanine | 135398634 | 764 | Acceptable — identical InChIKey, duplicate CID in PubChem | 허용 — InChIKey 동일, PubChem 중복 CID |
| 3-Methyladenine | 135398661 | 1673 | **Corrected** — different InChIKey, non-standard tautomer | **수정됨** — InChIKey 상이, 비표준 호변이성질체 |
