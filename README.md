# GitHub를 이용한 뉴스 검색 프로그램 제작

네이버 뉴스 검색 API와 BeautifulSoup을 활용하여 원하는 키워드의 최신 뉴스를 검색하고, 기사 상세 본문까지 자동으로 수집하여 구조화된 데이터(CSV)로 저장하는 프로젝트입니다.

---

## 📌 주요 기능
- **검색어 및 수집 건수 설정**: 코드 상단 설정 변수 또는 터미널 인자를 통해 간편하게 수정 가능 (최대 1,000건)
- **네이버 뉴스 본문 크롤링**: `n.news.naver.com` 기사의 경우 기자 정보/광고를 제외한 순수 본문 자동 수집
- **한글 깨짐 없는 CSV 저장**: `data/` 디렉터리에 `utf-8-sig` 인코딩으로 저장되어 Excel에서도 바로 열람 가능
- **Git 원자적 커밋 및 협업 관리**: 변경 사항을 논리적 단위로 분할 커밋하고 GitHub를 통해 버전 관리

---

## 🛠️ 기술 스택
- **Language**: Python 3.14+
- **Package Manager**: `uv`
- **Libraries**:
  - `requests`: HTTP 요청 및 API 통신
  - `beautifulsoup4`: HTML 파싱 및 기사 본문 추출
  - `pandas`: 수집 데이터 구조화 및 CSV 저장
  - `selenium`: 동적 페이지 확장 대비
  - `ipykernel`: 인터랙티브 주피터 환경 지원

---

## 🚀 시작하기

### 1. 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 네이버 API 키를 입력합니다.
```env
NAVER_CLIENT_ID=여러분의_클라이언트_ID
NAVER_CLIENT_SECRET=여러분의_시크릿_키
```
*(네이버 개발자 센터 및 네이버 클라우드 플랫폼 NCP 키를 모두 자동 지원합니다.)*

### 2. 의존성 패키지 동기화
```bash
uv sync
```

### 3. 프로그램 실행

#### 방법 1: 터미널 명령행 인자 전달 (추천)
```bash
# 기본 설정(인공지능, 20건) 실행
uv run python naver_news_scraper.py

# 원하는 키워드와 수집 건수 직접 지정 (예: '반도체' 30건)
uv run python naver_news_scraper.py "반도체" 30
```

#### 방법 2: 코드 상단 설정값 직접 수정
`naver_news_scraper.py` 파일 상단의 `KEYWORD`와 `TARGET_COUNT` 변수를 변경한 후 실행합니다.
```python
KEYWORD = "로봇"
TARGET_COUNT = 50
```

#### 방법 3: 파이썬 모듈로 임포트하여 사용
```python
from naver_news_scraper import scrape_naver_news

df = scrape_naver_news(query="자율주행", count=20)
print(df.head())
```

---

## 📂 프로젝트 구조
```text
wepscraping-git/
├── .env.example            # 환경변수 템플릿 파일
├── .gitignore              # Git 추적 제외 목록 (.venv, .env, data/ 등)
├── GEMINI.md               # Git 커밋 및 프로젝트 개발 규칙
├── README.md               # 프로젝트 안내 문서
├── naver_news_scraper.py   # 네이버 뉴스 수집 메인 프로그램
├── pyproject.toml          # uv 프로젝트 의존성 설정
├── uv.lock                 # 패키지 잠금 파일
└── src/
    └── wepscraping_git/    # 패키지 소스 디렉터리
```
