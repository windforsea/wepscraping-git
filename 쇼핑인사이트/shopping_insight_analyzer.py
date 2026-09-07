"""
네이버 쇼핑 전체 인기 물품 TOP 10 고객군별 클릭 데이터 분석기 (shopping_insight_analyzer.py)

단일 카테고리에 한정하지 않고, 네이버 쇼핑 전체 주요 분야(의류, 잡화, 가전, 식품 등)를
아우르는 대표 인기 물품 TOP 10을 선별하여, 최근 2일간의 연령, 성별, 기기(PC/모바일)
고객군별 클릭 데이터를 단 하나의 통합 CSV 파일로 수집/저장합니다.
"""

import os
import sys
import time
from datetime import datetime, timedelta
import requests
import pandas as pd

# Windows 콘솔 유니코드 호환성
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# 🎯 [설정] 네이버 쇼핑 전체를 아우르는 10개 대표 분야 및 기본 인기 물품
# ==============================================================================
SHOPPING_SECTORS = [
    {"cid": "50000000", "cname": "패션의류", "fallback_kw": "원피스"},
    {"cid": "50000001", "cname": "패션잡화", "fallback_kw": "크록스"},
    {"cid": "50000002", "cname": "화장품/미용", "fallback_kw": "ahc아이크림"},
    {"cid": "50000003", "cname": "디지털/가전", "fallback_kw": "냉장고"},
    {"cid": "50000004", "cname": "가구/인테리어", "fallback_kw": "식탁의자"},
    {"cid": "50000005", "cname": "출산/육아", "fallback_kw": "물티슈"},
    {"cid": "50000006", "cname": "식품", "fallback_kw": "추석선물세트"},
    {"cid": "50000007", "cname": "스포츠/레저", "fallback_kw": "텐트"},
    {"cid": "50000008", "cname": "생활/건강", "fallback_kw": "마스크"},
    {"cid": "50000003", "cname": "디지털/IT", "fallback_kw": "노트북"},
]

TIME_UNIT = "date"         # 수집 단위: 일간('date')
REQUEST_DELAY = 0.2        # API 호출 간격 (서버 부하 및 차단 방지)
# ==============================================================================

# 고객군 코드 한글 매핑 딕셔너리
LABEL_MAP = {
    # 기기
    "pc": "PC",
    "mo": "모바일",
    # 성별
    "m": "남성",
    "f": "여성",
    # 연령대
    "10": "10대",
    "20": "20대",
    "30": "30대",
    "40": "40대",
    "50": "50대",
    "60": "60대 이상",
}


def load_credentials():
    """
    .env 파일에서 네이버 API 키를 로드합니다.
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
        raise ValueError("[오류] .env 파일에 NAVER_CLIENT_ID 및 NAVER_CLIENT_SECRET이 필요합니다.")

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


def get_realtime_top_keyword(category_id: str, fallback_keyword: str) -> str:
    """
    특정 분야의 실시간 1위 인기 검색어를 조회합니다. (실패 시 기본 대표 키워드 사용)
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
        "count": 1,
    }

    try:
        res = requests.post(url, headers=headers, data=data, timeout=3)
        if res.status_code == 200:
            ranks = res.json().get("ranks", [])
            if ranks and "keyword" in ranks[0]:
                return ranks[0]["keyword"]
    except Exception:
        pass

    return fallback_keyword


def request_demographic_data(
    base_url: str,
    headers: dict,
    dimension: str,
    category_id: str,
    category_name: str,
    keyword: str,
    rank: int,
    start_date: str,
    end_date: str,
    time_unit: str = "date",
) -> list[dict]:
    """
    특정 상품 키워드에 대한 기기/성별/연령 클릭 비율 데이터를 API로 요청합니다.
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

        results = res.json().get("results", [])
        if not results:
            return []

        records = []
        for item in results:
            for d in item.get("data", []):
                group_code = d.get("group", "")
                records.append({
                    "순번": rank,
                    "카테고리명": category_name,
                    "카테고리ID": category_id,
                    "물품검색어": keyword,
                    "날짜": d.get("period"),
                    "분석구분": dimension.upper(),
                    "고객군코드": group_code,
                    "고객군명": LABEL_MAP.get(group_code, group_code),
                    "클릭비율지수": d.get("ratio"),
                })
        return records
    except Exception:
        return []


def analyze_all_shopping_top10(save_csv: bool = True) -> pd.DataFrame:
    """
    네이버 쇼핑 전체 분야별 대표 인기 물품 TOP 10에 대해 최근 2일치 고객군별 클릭 데이터를 수집합니다.
    """
    base_url, headers = load_credentials()

    today = datetime.now()
    end_date_str = today.strftime("%Y-%m-%d")
    start_date_str = (today - timedelta(days=2)).strftime("%Y-%m-%d")

    print("\n" + "=" * 75)
    print("🛒 [네이버 쇼핑 전체] 대표 인기 물품 TOP 10 고객군별 클릭 데이터 분석 (2일치)")
    print("=" * 75)
    print(f"- 수집 기간 범위: {start_date_str} ~ {end_date_str} (최근 2일치)")
    print("-" * 75)

    # 1. 쇼핑 전체 각 분야별 실시간 1위 인기 물품 조회
    print("🔍 [1단계] 네이버 쇼핑 전체 10개 주요 분야별 1위 인기 물품 선별 중...")
    target_items = []
    for idx, sec in enumerate(SHOPPING_SECTORS, 1):
        kw = get_realtime_top_keyword(sec["cid"], sec["fallback_kw"])
        target_items.append({
            "rank": idx,
            "cid": sec["cid"],
            "cname": sec["cname"],
            "keyword": kw,
        })
        print(f"  {idx:2d}번 | [{sec['cname']}] 대표 인기 물품: '{kw}'")
        time.sleep(0.1)

    # 2. 선별된 10개 대표 물품에 대해 2일치 고객군별(기기, 성별, 연령) 데이터 수집
    print("\n🚀 [2단계] TOP 10 물품별 다차원 고객군(기기/성별/연령) 데이터 수집 시작...")
    all_records = []

    for item in target_items:
        r = item["rank"]
        cid = item["cid"]
        cname = item["cname"]
        kw = item["keyword"]

        print(f"  [{r:2d}/10] '{cname}' > '{kw}' 수집 중...", end="", flush=True)

        # 기기별
        dev_data = request_demographic_data(
            base_url, headers, "device", cid, cname, kw, r, start_date_str, end_date_str, TIME_UNIT
        )
        time.sleep(REQUEST_DELAY)

        # 성별
        gen_data = request_demographic_data(
            base_url, headers, "gender", cid, cname, kw, r, start_date_str, end_date_str, TIME_UNIT
        )
        time.sleep(REQUEST_DELAY)

        # 연령대별
        age_data = request_demographic_data(
            base_url, headers, "age", cid, cname, kw, r, start_date_str, end_date_str, TIME_UNIT
        )
        time.sleep(REQUEST_DELAY)

        count = len(dev_data) + len(gen_data) + len(age_data)
        all_records.extend(dev_data)
        all_records.extend(gen_data)
        all_records.extend(age_data)

        print(f" 완료 ({count}건)")

    if not all_records:
        print("[오류] 수집된 데이터가 없습니다.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    # 최근 2일치 데이터 필터링 보장
    dates = sorted(df["날짜"].unique())
    latest_2_dates = dates[-2:] if len(dates) >= 2 else dates
    df = df[df["날짜"].isin(latest_2_dates)].copy()

    # 정렬: 순번, 카테고리명, 날짜, 분석구분
    df.sort_values(by=["순번", "날짜", "분석구분", "고객군코드"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print("\n" + "=" * 75)
    print(f"📈 [분석 완료] 수집 날짜: {', '.join(latest_2_dates)} (총 {len(df)}개 관측 데이터)")
    print("=" * 75)

    # 요약 리포트 테이블 출력
    print(f"\n[네이버 쇼핑 전체 TOP 10 물품별 주요 관심 고객층 요약]")
    print(f"{'순번':<4} | {'분야명':<9} | {'물품검색어':<12} | {'주 이용 기기':<15} | {'주 성별':<14} | {'핵심 연령층'}")
    print("-" * 75)

    for rank in sorted(df["순번"].unique()):
        sub = df[df["순번"] == rank]
        cname = sub["카테고리명"].iloc[0]
        kw = sub["물품검색어"].iloc[0]

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

        print(f"{rank:2d}번  | {cname:<9} | {kw:<12} | {dev_str:<15} | {gen_str:<14} | {age_str}")

    print("-" * 75)

    # 단일 통합 CSV 파일 저장
    if save_csv:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(output_dir, exist_ok=True)
        filename = "shopping_insight_전체쇼핑_TOP10물품_고객군분석_2일치.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"\n💾 [저장 완료] 단일 CSV 파일 생성: {filepath}")
        print(f"   - 총 행(Row) 수: {len(df)}행 (쇼핑 전체 10개 대표 물품 전체 통합)")

    return df


if __name__ == "__main__":
    analyze_all_shopping_top10(save_csv=True)
