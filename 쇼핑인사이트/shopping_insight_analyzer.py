"""
네이버 쇼핑인사이트 인기검색어 TOP 10 고객군별 클릭 데이터 분석기 (shopping_insight_analyzer.py)

NAVER API HUB 쇼핑인사이트 API를 활용하여:
1. 쇼핑 카테고리별 실시간 인기 검색어 TOP 10을 자동 추출하고
2. 각 검색어(1위~10위)에 대해 최근 2일간의 기기(PC/모바일), 성별(남/여), 연령대별(10대~60대) 클릭 데이터를 수집하여
3. 단 하나의 CSV 파일(utf-8-sig)로 통합 저장합니다.
"""

import os
import sys
import time
from datetime import datetime, timedelta
import requests
import pandas as pd

# Windows 터미널 한글 출력 호환성 보장
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# 🎯 [사용자 설정] 대상 카테고리 및 수집 설정
# ==============================================================================
# 카테고리 ID (cat_id):
# 50000000: 패션의류, 50000001: 패션잡화, 50000002: 화장품/미용,
# 50000003: 디지털/가전, 50000004: 가구/인테리어, 50000005: 출산/육아,
# 50000006: 식품, 50000007: 스포츠/레저, 50000008: 생활/건강
DEFAULT_CATEGORY_ID = "50000000"     # 기본: 패션의류
DEFAULT_CATEGORY_NAME = "패션의류"
TOP_KEYWORD_COUNT = 10               # 수집할 인기 검색어 순위 개수 (1위 ~ 10위)
ANALYSIS_DAYS = 2                    # 수집 기간: 최근 2일치
TIME_UNIT = "date"                   # 시간 단위: 일간('date')
REQUEST_DELAY = 0.15                 # API 호출 딜레이(초, 부하 방지)
# ==============================================================================

# 고객군 코드 한글 라벨 맵
LABEL_MAP = {
    # 기기
    "pc": "PC",
    "mo": "모바일",
    # 성별
    "m": "남성",
    "f": "여성",
    # 연령
    "10": "10대",
    "20": "20대",
    "30": "30대",
    "40": "40대",
    "50": "50대",
    "60": "60대 이상",
}


def load_credentials():
    """
    .env 파일에서 네이버 API 키를 로드하고 환경에 맞게 URL 및 헤더를 반환합니다.
    """
    candidates = [
        ".env",
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        r"C:\projects\wepscraping\.env",
    ]
    for path in candidates:
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
            "[오류] .env 파일에 NAVER_CLIENT_ID 및 NAVER_CLIENT_SECRET이 설정되어 있지 않습니다."
        )

    # NCP (NAVER API HUB) vs Developers 자동 분기
    if len(client_id) == 10 and client_id.islower():
        base_url = "https://naverapihub.apigw.ntruss.com/shopping/v1"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
            "Content-Type": "application/json",
        }
    else:
        base_url = "https://openapi.naver.com/v1/datalab/shopping"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json",
        }

    return base_url, headers


def get_popular_keywords(category_id: str, count: int = 10) -> list[str]:
    """
    해당 쇼핑 카테고리의 최근 인기 검색어 순위 목록을 조회합니다.
    """
    url = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://datalab.naver.com/shoppingInsight/sCategory.naver",
    }
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    data = {
        "cid": category_id,
        "timeUnit": "date",
        "startDate": start_date,
        "endDate": end_date,
        "page": 1,
        "count": count,
    }

    try:
        res = requests.post(url, headers=headers, data=data, timeout=5)
        if res.status_code == 200:
            ranks = res.json().get("ranks", [])
            keywords = [item["keyword"] for item in ranks]
            if keywords:
                return keywords[:count]
    except Exception as e:
        print(f"[안내] 실시간 인기검색어 조회 예외: {e}")

    # 기본 예시 키워드 10개 (오프라인/대체용)
    fallback = ["원피스", "블라우스", "올리비아로렌", "바람막이", "에고이스트",
                "트위드자켓", "잇미샤원피스", "모조에스핀", "스웨이드자켓", "지고트원피스"]
    return fallback[:count]


def request_demographic_data(
    base_url: str,
    headers: dict,
    dimension: str,
    category_id: str,
    keyword: str,
    rank: int,
    start_date: str,
    end_date: str,
    time_unit: str = "date",
) -> list[dict]:
    """
    단일 검색어에 대한 특정 고객군(device / gender / age) 클릭 데이터를 호출합니다.
    """
    endpoint = f"{base_url}/category/keyword/{dimension}"
    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_id,
        "keyword": keyword,
    }

    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        if res.status_code != 200:
            return []

        data = res.json()
        results = data.get("results", [])
        if not results:
            return []

        records = []
        for item in results:
            for d in item.get("data", []):
                group_code = d.get("group", "")
                records.append({
                    "순위": rank,
                    "검색어": keyword,
                    "날짜": d.get("period"),
                    "분석구분": dimension.upper(),
                    "고객군코드": group_code,
                    "고객군명": LABEL_MAP.get(group_code, group_code),
                    "클릭비율지수": d.get("ratio"),
                    "카테고리ID": category_id,
                })
        return records
    except Exception:
        return []


def analyze_top10_shopping_insights(
    category_id: str = DEFAULT_CATEGORY_ID,
    category_name: str = DEFAULT_CATEGORY_NAME,
    top_count: int = TOP_KEYWORD_COUNT,
    save_csv: bool = True,
) -> pd.DataFrame:
    """
    쇼핑 카테고리의 인기 검색어 TOP 10에 대해 최근 2일치 고객군별(기기, 성별, 연령) 클릭 데이터를
    단일 파일로 통합 수집하고 분석합니다.
    """
    base_url, headers = load_credentials()

    # 최근 2일치 기간 설정 (통계 산출 시점 고려: 오늘 포함 최근 3일 중 집계된 최신 2일)
    today = datetime.now()
    end_date_str = today.strftime("%Y-%m-%d")
    start_date_str = (today - timedelta(days=2)).strftime("%Y-%m-%d")

    print("\n" + "=" * 70)
    print(f"📊 [네이버 쇼핑인사이트] 인기 검색어 TOP {top_count} 2일치 고객군별 클릭 분석")
    print("=" * 70)
    print(f"- 대상 카테고리: {category_name} (ID: {category_id})")
    print(f"- 수집 기간 범위: {start_date_str} ~ {end_date_str} (최근 2일치)")
    print("-" * 70)

    # 1. 인기 검색어 TOP N 조회
    print(f"🔍 [1단계] 쇼핑 인기 검색어 TOP {top_count} 조회 중...")
    keywords = get_popular_keywords(category_id, count=top_count)
    for idx, kw in enumerate(keywords, 1):
        print(f"  {idx:2d}위: {kw}")

    print("\n🚀 [2단계] TOP 10 검색어별 기기/성별/연령 데이터 수집 시작...")
    all_combined_records = []

    for rank, kw in enumerate(keywords, 1):
        print(f"  [{rank:2d}/{top_count}위] '{kw}' 데이터 수집 중...", end="", flush=True)

        # 기기별
        dev_records = request_demographic_data(
            base_url, headers, "device", category_id, kw, rank, start_date_str, end_date_str
        )
        time.sleep(REQUEST_DELAY)

        # 성별
        gen_records = request_demographic_data(
            base_url, headers, "gender", category_id, kw, rank, start_date_str, end_date_str
        )
        time.sleep(REQUEST_DELAY)

        # 연령대별
        age_records = request_demographic_data(
            base_url, headers, "age", category_id, kw, rank, start_date_str, end_date_str
        )
        time.sleep(REQUEST_DELAY)

        kw_total = len(dev_records) + len(gen_records) + len(age_records)
        all_combined_records.extend(dev_records)
        all_combined_records.extend(gen_records)
        all_combined_records.extend(age_records)

        print(f" 완료 ({kw_total}건)")

    if not all_combined_records:
        print("[오류] 수집된 데이터가 없습니다.")
        return pd.DataFrame()

    # 전체 데이터프레임 생성
    df = pd.DataFrame(all_combined_records)

    # 날짜 정렬 및 확인 (최근 2일 필터 보장)
    available_dates = sorted(df["날짜"].unique())
    latest_2_dates = available_dates[-2:] if len(available_dates) >= 2 else available_dates
    df = df[df["날짜"].isin(latest_2_dates)].copy()

    # 정렬: 순위 오름차순, 검색어, 날짜, 분석구분
    df.sort_values(by=["순위", "날짜", "분석구분", "고객군코드"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print("\n" + "=" * 70)
    print(f"📈 [분석 완료] 수집된 날짜: {', '.join(latest_2_dates)} (총 {len(df)}개 데이터)")
    print("=" * 70)

    # TOP 10 키워드별 주요 고객층 요약 리포트
    print(f"\n[인기 검색어 TOP {top_count} 주요 관심 고객층 요약]")
    print(f"{'순위':<4} | {'검색어':<12} | {'주 이용 기기':<15} | {'주 성별':<14} | {'핵심 연령대'}")
    print("-" * 70)

    for rank in sorted(df["순위"].unique()):
        sub = df[df["순위"] == rank]
        kw_name = sub["검색어"].iloc[0]

        # 기기
        dev_sub = sub[sub["분석구분"] == "DEVICE"]
        if not dev_sub.empty:
            top_dev = dev_sub.groupby("고객군명")["클릭비율지수"].mean().sort_values(ascending=False)
            dev_str = f"{top_dev.index[0]} ({(top_dev.iloc[0] / top_dev.sum() * 100):.1f}%)"
        else:
            dev_str = "-"

        # 성별
        gen_sub = sub[sub["분석구분"] == "GENDER"]
        if not gen_sub.empty:
            top_gen = gen_sub.groupby("고객군명")["클릭비율지수"].mean().sort_values(ascending=False)
            gen_str = f"{top_gen.index[0]} ({(top_gen.iloc[0] / top_gen.sum() * 100):.1f}%)"
        else:
            gen_str = "-"

        # 연령
        age_sub = sub[sub["분석구분"] == "AGE"]
        if not age_sub.empty:
            top_age = age_sub.groupby("고객군명")["클릭비율지수"].mean().sort_values(ascending=False)
            age_str = f"{top_age.index[0]} ({(top_age.iloc[0] / age_sub.groupby('고객군명')['클릭비율지수'].mean().sum() * 100):.1f}%)"
            if len(top_age) > 1:
                age_str += f", {top_age.index[1]}"
        else:
            age_str = "-"

        print(f"{rank:2d}위  | {kw_name:<12} | {dev_str:<15} | {gen_str:<14} | {age_str}")

    print("-" * 70)

    # 단일 통합 CSV 파일로 저장
    if save_csv:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(output_dir, exist_ok=True)
        date_tag = f"{latest_2_dates[0]}_{latest_2_dates[-1]}".replace("-", "")
        filename = f"shopping_insight_{category_id}_TOP{top_count}_고객군분석_2일치.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"\n💾 [통합 저장 완료] 단일 CSV 파일 생성: {filepath}")
        print(f"   - 총 행(Row) 수: {len(df)}행 (TOP {top_count}개 키워드 전체 포함)")

    return df


if __name__ == "__main__":
    cat_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CATEGORY_ID
    count = int(sys.argv[2]) if len(sys.argv) > 2 else TOP_KEYWORD_COUNT

    analyze_top10_shopping_insights(category_id=cat_id, top_count=count, save_csv=True)
