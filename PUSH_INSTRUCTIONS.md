# 깃허브 푸시 방법

프로젝트가 정리되어 Git 저장소에 커밋되었습니다. 깃허브에 푸시하려면 다음 단계를 따르세요:

## 1. 깃허브 저장소 확인

저장소 이름이 정확한지 확인하세요:
- 저장소 이름: `동대문구_노인보호구역_위험도평가`
- 저장소가 생성되어 있는지 확인

## 2. 원격 저장소 설정

저장소 URL이 다르다면 다음 명령어로 수정하세요:

```bash
git remote set-url origin https://github.com/사용자명/동대문구_노인보호구역_위험도평가.git
```

## 3. 푸시 실행

```bash
git push -u origin main
```

## 현재 프로젝트 구조

```
동대문구_노인보호구역_위험도평가/
├── .gitignore          # Git 제외 파일 설정
├── README.md           # 프로젝트 설명서
├── requirements.txt    # Python 패키지 목록
├── data/               # 원본 데이터
├── notebooks/          # Jupyter Notebook 분석 파일
├── src/                # Python 스크립트
├── models/             # MaxEnt 모델 관련 파일
├── results/            # 분석 결과물
└── docs/               # 문서 및 발표 자료
```

## 주의사항

- `.gitignore`에 의해 다음 파일들은 제외됩니다:
  - `maxent.cache/` (캐시 파일)
  - `*.asc`, `*.shp`, `*.dat` (대용량 파일)
  - `재현이 실수해서 다시한거/`, `현재 지정 모델/` (대용량 폴더)

필요한 경우 `.gitignore`를 수정하여 특정 파일을 포함시킬 수 있습니다.

