# 네이버 검색어 & 쇼핑 트렌드 수집 프로그램 (GitHub 협업 프로젝트)

네이버 데이터랩(DataLab) 오픈 API를 활용하여 **통합 검색어 트렌드**와 **쇼핑 검색어 트렌드**를 수집하고, 분석 가능한 시계열 데이터(CSV)로 저장하는 협업 프로젝트입니다.

---

## 👥 협업 역할 분담

본 프로젝트는 2인의 공동 작업자가 각각의 트렌드 수집 모듈을 독립적으로 개발하고 통합합니다.

| 담당자 / 역할 | 수집 대상 및 기능 | 사용 API 엔드포인트 | 저장 형식 |
| :--- | :--- | :--- | :--- |
| **담당자 A** | **네이버 통합 검색어 트렌드 조회**<br>- 주제어 및 하위 검색어별 기간별 검색 트렌드 조회<br>- 기기별(PC/모바일), 성별, 연령대별 조건 필터링 | `/v1/datalab/search` | `data/search_trend_{주제어}.csv` |
| **담당자 B** | **네이버 쇼핑 검색어 트렌드 조회**<br>- 쇼핑 카테고리/분야별 인기 키워드 트렌드 조회<br>- 카테고리 내 검색어 클릭/조회 트렌드 비교 | `/v1/datalab/shopping/category/keywords` | `data/shopping_trend_{카테고리}.csv` |

---

## 📌 주요 기능
- **다차원 트렌드 수집**: 기간(일간/주간/월간), 기기(PC/모바일), 성별, 연령대별 세부 검색량 트렌드 조회
- **구조화된 CSV 저장**: 수집된 JSON 응답을 Pandas DataFrame으로 가공하여 `data/` 디렉터리에 `utf-8-sig` 인코딩 CSV로 자동 저장 (Excel 호환)
- **보안 및 인증 관리**: `.env` 파일을 통해 Naver Client ID & Secret을 안전하게 격리 보관
- **Git 원자적 커밋 및 협업**: 모듈별 기능 브랜치 개발 및 Conventional Commits 규칙 준수

---

## 🛠️ 기술 스택
- **Language**: Python 3.14+
- **Package Manager**: `uv`
- **Libraries**:
  - `requests`: 네이버 DataLab API 호출 (POST 요청)
  - `pandas`: 트렌드 시계열 데이터 가공 및 CSV 변환
  - `ipykernel`: 데이터 탐색 및 인터랙티브 테스트 지원
  - `python-dotenv`: API 인증키 환경변수 로드

---

## 🚀 시작하기

### 1. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 네이버 개발자 센터에서 발급받은 **데이터랩(검색어트렌드/쇼핑인사이트)** API 키를 등록합니다.
```env
NAVER_CLIENT_ID=여러분의_클라이언트_ID
NAVER_CLIENT_SECRET=여러분의_시크릿_키
```

### 2. 의존성 패키지 동기화
```bash
uv sync
```

### 3. 모듈별 실행 방법

#### [담당자 A] 통합 검색어 트렌드 조회
```bash
# 통합 검색어 트렌드 수집 실행 (예시)
uv run python search_trend_scraper.py
```

#### [담당자 B] 쇼핑 검색어 트렌드 조회
```bash
# 쇼핑 카테고리 검색어 트렌드 수집 실행 (예시)
uv run python shopping_trend_scraper.py
```

---

## 📂 프로젝트 구조 (예정)
```text
wepscraping-git/
├── .env.example                # 환경변수 템플릿 파일
├── .gitignore                  # Git 추적 제외 목록 (.venv, .env, data/ 등)
├── GEMINI.md                   # Git 커밋 및 협업 개발 규칙
├── README.md                   # 프로젝트 협업 안내 문서
├── pyproject.toml              # uv 프로젝트 의존성 설정
├── uv.lock                     # 패키지 잠금 파일
├── search_trend_scraper.py     # [담당자 A] 통합 검색어 트렌드 수집 모듈
├── shopping_trend_scraper.py   # [담당자 B] 쇼핑 검색어 트렌드 수집 모듈
└── data/                       # 트렌드 CSV 결과 저장 폴더 (Git 제외)
```
