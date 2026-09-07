r"""
네이버 뉴스 기사 수집기 (naver_news_scraper.py)

C:\projects\wepscraping 프로젝트의 실습 코드를 바탕으로 제작된 간결한 네이버 뉴스 수집 프로그램입니다.
검색어와 수집 기사 개수를 손쉽게 수정하여 실행할 수 있습니다.
"""

import os
import sys
import re
import html
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Windows 터미널 한글 출력 호환성
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# 🎯 [사용자 설정] 검색어 및 수집 개수를 여기서 간편하게 수정하세요!
# ==============================================================================
KEYWORD: str = "인공지능"       # 1. 검색어 (예: "인공지능", "반도체", "로봇", "부동산")
TARGET_COUNT: int = 20         # 2. 수집할 기사 개수 (1 ~ 1000)
SORT_ORDER: str = "date"       # 정렬 기준: 'date'(최신순) 또는 'sim'(관련도순)
CRAWL_CONTENT: bool = True     # 네이버 뉴스 상세 본문 크롤링 여부 (True / False)
SAVE_CSV: bool = True          # CSV 파일 저장 여부
# ==============================================================================

# 크롤링 차단 방지용 브라우저 헤더
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def load_env_credentials():
    """
    .env 파일에서 네이버 API 키를 읽어옵니다.
    현재 폴더에 없으면 C:\\projects\\wepscraping\\.env 파일도 자동으로 탐색합니다.
    """
    env_paths = [".env", os.path.join(os.path.dirname(__file__), ".env"), r"C:\projects\wepscraping\.env"]
    for path in env_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        raise ValueError(
            "[오류] .env 파일에 NAVER_CLIENT_ID 및 NAVER_CLIENT_SECRET이 설정되어 있지 않습니다.\n"
            "네이버 개발자 센터(developers.naver.com) 또는 네이버 클라우드 플랫폼(NCP)의 인증키를 .env에 입력해주세요."
        )

    # 네이버 클라우드 플랫폼(NCP) vs 네이버 개발자 센터(Developers) 키 자동 분기
    if len(client_id) == 10 and client_id.islower():
        api_url = "https://naverapihub.apigw.ntruss.com/search/v1/news"
        req_headers = {
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
        }
    else:
        api_url = "https://openapi.naver.com/v1/search/news.json"
        req_headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    return api_url, req_headers


def clean_text(raw_text: str) -> str:
    """HTML 특수문자 디코딩 및 태그(<b> 등)를 제거하는 함수"""
    if not isinstance(raw_text, str):
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def fetch_article_body(link: str, fallback_summary: str = "") -> str:
    """
    네이버 뉴스 본문(#dic_area, #newsct_article)을 BeautifulSoup으로 크롤링합니다.
    언론사 자체 페이지거나 크롤링이 불가능한 경우 요약문(fallback_summary)을 반환합니다.
    """
    if not link or "news.naver.com" not in link:
        return fallback_summary

    try:
        res = requests.get(link, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            body_tag = soup.select_one("#dic_area, #newsct_article")
            if body_tag:
                for tag in body_tag.find_all(["script", "style", "iframe", "noscript"]):
                    tag.decompose()
                text = body_tag.get_text(separator="\n", strip=True)
                if text:
                    return text
    except Exception:
        pass

    return fallback_summary


def scrape_naver_news(
    query: str = KEYWORD,
    count: int = TARGET_COUNT,
    sort: str = SORT_ORDER,
    crawl_content: bool = CRAWL_CONTENT,
    save_csv: bool = SAVE_CSV,
    delay: float = 0.1,
) -> pd.DataFrame:
    """
    지정한 검색어(query)와 수집 개수(count)에 맞춰 네이버 뉴스를 수집합니다.

    :param query: 검색 키워드
    :param count: 수집할 기사 개수 (최대 1,000건)
    :param sort: 정렬 기준 ('date': 최신순, 'sim': 관련도순)
    :param crawl_content: 본문 상세 크롤링 여부
    :param save_csv: CSV 파일 저장 여부
    :param delay: 요청 간 딜레이(초)
    :return: 수집 결과 DataFrame
    """
    api_url, req_headers = load_env_credentials()

    count = max(1, min(count, 1000))
    results = []
    start_index = 1
    display_per_page = 100

    print(f"\n[네이버 뉴스 수집 시작]")
    print(f"- 검색어: '{query}'")
    print(f"- 목표 수집 건수: {count}건")
    print(f"- 정렬 기준: {'최신순(date)' if sort == 'date' else '관련도순(sim)'}")
    print(f"- 상세 본문 수집: {'포함' if crawl_content else '제외(요약만)'}")

    while len(results) < count and start_index <= 1000:
        fetch_size = min(display_per_page, count - len(results))
        params = {
            "query": query,
            "display": fetch_size,
            "start": start_index,
            "sort": sort,
        }

        try:
            res = requests.get(api_url, headers=req_headers, params=params, timeout=10)
        except Exception as e:
            print(f"\n[오류] API 호출 중 오류 발생: {e}")
            break

        if res.status_code != 200:
            print(f"\n[오류] API 응답 에러 (코드: {res.status_code}): {res.text}")
            break

        items = res.json().get("items", [])
        if not items:
            print("\n[안내] 더 이상 검색된 뉴스가 없습니다.")
            break

        for item in items:
            title = clean_text(item.get("title", ""))
            summary = clean_text(item.get("description", ""))
            link = item.get("link", "")
            pub_date = item.get("pubDate", "")

            # 본문 수집
            if crawl_content:
                content = fetch_article_body(link, fallback_summary=summary)
                time.sleep(delay)
            else:
                content = summary

            results.append({
                "title": title,
                "summary": summary,
                "content": content,
                "pubDate": pub_date,
                "link": link,
            })

            print(f"\r- 진행률: {len(results)}/{count}건 완료", end="", flush=True)

            if len(results) >= count:
                break

        start_index += len(items)
        time.sleep(delay)

    print(f"\n[완료] 총 {len(results)}건의 뉴스 기사를 수집했습니다.")

    df = pd.DataFrame(results)

    if save_csv and not df.empty:
        os.makedirs("data", exist_ok=True)
        # 파일명에 사용할 수 없는 특수문자 제거
        safe_keyword = re.sub(r'[\/:*?"<>|]', '_', query)
        filename = os.path.join("data", f"naver_news_{safe_keyword}.csv")
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"[저장] CSV 파일 저장 완료: {filename}")

    return df


if __name__ == "__main__":
    # 터미널 실행 인자(sys.argv)가 주어지면 인자를 우선 적용합니다.
    # 사용법 예: python naver_news_scraper.py "반도체" 30
    user_query = sys.argv[1] if len(sys.argv) > 1 else KEYWORD
    user_count = int(sys.argv[2]) if len(sys.argv) > 2 else TARGET_COUNT

    df_news = scrape_naver_news(query=user_query, count=user_count)
    if not df_news.empty:
        print("\n--- [수집 결과 미리보기 (상위 2건)] ---")
        for i, row in df_news.head(2).iterrows():
            print(f"[{i + 1}] {row['title']}")
            print(f"    - 작성일: {row['pubDate']}")
            print(f"    - 링크: {row['link']}")
            print(f"    - 본문 일부: {row['content'][:100]}...\n")
