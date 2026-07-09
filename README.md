# metabolite-study

대사체 데이터의 화합물 주석(annotation) 및 내인성/외인성(endogenous/exogenous) 분류 프로젝트.

## 프로젝트 구조

```metabolite-study/```
```├─ data/            현재 작업 데이터 (사람·쥐)```
```│   ├─ reference/   COCONUT 전체 데이터 등 참조용```
```│   ├─ human/       사람 혈청 (raw → interim → final)```
```│   └─ mouse/       쥐 혈청 (raw → interim → final)```
```├─ scripts/         현재 작업 코드 (HTML 추출 → SMILES 조회 → 분류)```
```├─ legacy/          기존 파이프라인 (step1~29, COCONUT 902 화합물 DB)```
```├─ format_excel.py  엑셀 서식 도구```
```└─ validate.py      데이터 검증 도구```

## 현재 작업

사람·쥐 혈청 대사체(COCONUT으로 주석된 화합물)에 대해:


AG Grid HTML 리포트에서 화합물 표 추출
CNP id로 COCONUT 데이터에서 SMILES 조회
DarkMet 모델로 내인성/외인성 분류
종별 최종 DB 구축


각 종의 결과는 data/{species}/final/에 저장.

## 데이터 처리 원칙


raw/는 원본 보존, 수정하지 않음
interim/은 중간 산출물, 언제든 재생성 가능
final/은 분석·공유용 최종 결과
코드는 종(human/mouse) 무관하게 공통 사용, SPECIES 설정으로 전환


## 기존 작업 (legacy)

legacy/는 COCONUT 기반 902 화합물 DB 구축 파이프라인(step1~29).
상세는 legacy/README.md 참고.

## 노트


RESEARCHNOTE.md — 연구 결정과 근거
STUDYNOTE.md — 코드 메커니즘