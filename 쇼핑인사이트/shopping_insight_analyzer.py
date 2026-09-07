"""
네이버 쇼핑인사이트 고객군별 클릭 데이터 분석기 (shopping_insight_analyzer.py)

NAVER API HUB 쇼핑인사이트 API를 활용하여:
1. 네이버 쇼핑 인기 검색어를 확인하고
2. 특정 키워드에 대해 연령, 성별, 기기(PC/모바일) 기준으로 클릭 데이터를 나누어 분석하며
3. 주요 관심 고객층과 이용 패턴을 파악하여 CSV(utf-8-sig) 파일로 저장합니다.
"""

import os
import sys
import json
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
# 🎯 [사용자 설정] 분석 대상 카테고리, 키워드, 기간을 손쉽게 수정하세요!
# ==============================================================================
# 카테고리 ID (cat_id):
# 50000000: 패션의류, 50000001: 패션잡화, 50000002: 화장품/미용,
# 50000003: 디지털/가전, 50000004: 가구/인테리어, 50000005: 출산/육아,
# 50000006: 식품, 50000007: 스포츠/레저, 50000008: 생활/건강
DEFAULT_CATEGORY_ID = "50000000"     # 기본: 패션의류
DEFAULT_CATEGORY_NAME = "패션의류"
DEFAULT_KEYWORD = "원피스"           # 분석할 검색어 (비워두면 1위 인기검색어 자동 선택)
ANALYSIS_DAYS = 30                   # 분석 기간 (최근 N일)
TIME_UNIT = "date"                   # 시간 단위 ('date': 일간, 'week': 주간, 'month': 월간)
# ==============================================================================

# 고객군 코드 한글 매핑 딕셔너리
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
    .env 파일에서 네이버 클라우드 플랫폼(NCP) 또는 개발자 센터 API 키를 로드합니다.
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

    # NCP (NAVER API HUB) vs Developers 자동 판별
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
            return [item["keyword"] for item in ranks]
    except Exception as e:
        print(f"[안내] 인기검색어 실시간 조회 생략 ({e})")

    return ["원피스", "트위드자켓", "가디건", "슬랙스", "맨투맨"]


def request_insight_demographics(
    dimension: str,
    category_id: str,
    keyword: str,
    start_date: str,
    end_date: str,
    time_unit: str = "date",
) -> list[dict]:
    """
    특정 기준(device / gender / age)에 대한 클릭 추이를 API로 호출합니다.
    """
    base_url, headers = load_credentials()
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
            print(f"[경고] {dimension} API 호출 실패 ({res.status_code}): {res.text}")
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
                    "날짜": d.get("period"),
                    "분석구분": dimension.upper(),
                    "고객군코드": group_code,
                    "고객군명": LABEL_MAP.get(group_code, group_code),
                    "클릭비율지수": d.get("ratio"),
                    "검색어": keyword,
                    "카테고리ID": category_id,
                })
        return records
    except Exception as e:
        print(f"[오류] {dimension} 데이터 요청 에러: {e}")
        return []


def analyze_shopping_insight(
    keyword: str = DEFAULT_KEYWORD,
    category_id: str = DEFAULT_CATEGORY_ID,
    category_name: str = DEFAULT_CATEGORY_NAME,
    days: int = ANALYSIS_DAYS,
    time_unit: str = TIME_UNIT,
    save_csv: bool = True,
) -> pd.DataFrame:
    """
    쇼핑 검색어에 대해 고객군별(기기, 성별, 연령) 클릭 데이터를 수집 및 분석하고 CSV로 저장합니다.
    """
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    print("\n" + "=" * 65)
    print("📊 [네이버 쇼핑인사이트] 고객군별 클릭 데이터 분석")
    print("=" * 65)
    print(f"- 대상 카테고리: {category_name} (ID: {category_id})")
    print(f"- 분석 검색어: '{keyword}'")
    print(f"- 분석 기간: {start_date} ~ {end_date} (최근 {days}일간, 단위: {time_unit})")
    print("-" * 65)

    all_records = []

    # 1. 기기별 (PC vs 모바일)
    print("1. 기기별(PC/모바일) 클릭 데이터 수집 중...")
    device_data = request_insight_demographics("device", category_id, keyword, start_date, end_date, time_unit)
    all_records.extend(device_data)

    # 2. 성별 (여성 vs 남성)
    print("2. 성별(남성/여성) 클릭 데이터 수집 중...")
    gender_data = request_insight_demographics("gender", category_id, keyword, start_date, end_date, time_unit)
    all_records.extend(gender_data)

    # 3. 연령별 (10대 ~ 60대)
    print("3. 연령대별(10대~60대) 클릭 데이터 수집 중...")
    age_data = request_insight_demographics("age", category_id, keyword, start_date, end_date, time_unit)
    all_records.extend(age_data)

    if not all_records:
        print("[알림] 수집된 데이터가 없습니다.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    # --- 고객군별 요약 분석 및 콘솔 리포트 ---
    print("\n" + "=" * 65)
    print(f"📈 ['{keyword}'] 고객군별 이용 패턴 분석 리포트 요약")
    print("=" * 65)

    for dim, dim_name in [("DEVICE", "기기별"), ("GENDER", "성별"), ("AGE", "연령대별")]:
        sub_df = df[df["분석구분"] == dim]
        if not sub_df.empty:
            avg_ratios = sub_df.groupby("고객군명")["클릭비율지수"].mean().sort_values(ascending=False)
            total_sum = avg_ratios.sum()
            shares = (avg_ratios / total_sum * 100).round(1) if total_sum > 0 else avg_ratios

            print(f"\n[{dim_name} 비중]")
            summary_list = []
            for name, share in shares.items():
                summary_list.append(f"{name}: {share}%")
            print(" | ".join(summary_list))

    print("-" * 65)

    # CSV 파일 저장
    if save_csv:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"shopping_insight_{category_id}_{keyword}_고객군분석.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"💾 [저장 완료] CSV 파일: {filepath}")

    return df


if __name__ == "__main__":
    # 1. 쇼핑 인기 검색어 상위 10개 조회 및 출력
    print("\n🔍 [오늘의 네이버 쇼핑 인기 검색어 TOP 10 확인]")
    top_keywords = get_popular_keywords(DEFAULT_CATEGORY_ID, count=10)
    for idx, kw in enumerate(top_keywords, 1):
        print(f"  {idx:2d}위: {kw}")

    # 2. 실행 인자 처리 (인자가 없으면 기본 설정 또는 1위 키워드 활용)
    target_kw = sys.argv[1] if len(sys.argv) > 1 else (DEFAULT_KEYWORD or top_keywords[0])
    target_cat = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CATEGORY_ID
    target_days = int(sys.argv[3]) if len(sys.argv) > 3 else ANALYSIS_DAYS

    # 3. 고객군별 클릭 데이터 분석 실행
    df_result = analyze_shopping_insight(
        keyword=target_kw,
        category_id=target_cat,
        days=target_days,
        save_csv=True,
    )
