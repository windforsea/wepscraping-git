import sys
from naver_news_scraper import scrape_naver_news, KEYWORD, TARGET_COUNT

def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else KEYWORD
    count = int(sys.argv[2]) if len(sys.argv) > 2 else TARGET_COUNT
    scrape_naver_news(query=query, count=count)

__all__ = ["scrape_naver_news", "main"]
