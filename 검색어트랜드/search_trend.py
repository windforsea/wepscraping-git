"""
네이버 통합 검색어 트렌드 수집기 (도서 인기 검색어 개별 비교)

네이버 데이터랩의 도서 부문 인기 키워드 10개를 5개씩 나누어 조회한 후,
각 키워드의 최근 일간 검색 추이를 하나의 CSV 파일로 저장합니다.
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# Windows 터미널 한글 출력 지원
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 🎯 [사용자 설정] 여기서 검색 키워드와 조회 기간을 손쉽게 수정하세요!
# ==============================================================================

# 1. 수집 대상 도서 키워드 목록
BOOK_KEYWORDS = [
    "안녕피터팬",
    "베스트셀러",
    "베스트셀러순위",
    "수족관책",
    "원소원정대",
    "브레인악셀",
    "옥스브리지의철학수업",
    "니체의초월자",
    "테오책",
    "찰리멍거바이블",
]

# 2. 조회 기간 설정 (형식: "YYYY-MM-DD")
# 원하는 시작일과 종료일을 직접 적어주세요.
# 만약 둘 다 비워두면("") 자동으로 '최근 30일'을 조회합니다.
START_DATE: str = "2026-09-01"     # 시작 날짜 (예: "2026-08-01")
END_DATE: str = "2026-09-06"       # 종료 날짜 (예: "2026-09-06")

# 3. 구간 단위 설정: 'date'(일간), 'week'(주간), 'month'(월간)
TIME_UNIT: str = "date"

# ==============================================================================


def load_environment_keys():
    """
    .env 파일에서 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 읽어옵니다.
    """
    env_paths = [
        ".env",
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]

    for path in env_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            break

    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    if not client_id:
        client_id = os.getenv("NAVER_CLIENT_KEY", "").strip()

    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()
    return client_id, client_secret


def split_keywords_into_chunks(keyword_list, chunk_size=5):
    """
    키워드 리스트를 지정한 개수(기본 5개) 단위로 나누어 리스트로 반환합니다.
    (네이버 API의 1회 최대 요청 제한이 5개 그룹이기 때문입니다.)
    """
    chunks = []
    for i in range(0, len(keyword_list), chunk_size):
        chunk = keyword_list[i : i + chunk_size]
        chunks.append(chunk)
    return chunks


def make_keyword_groups(keywords):
    """
    키워드 리스트를 네이버 API 요청 양식(keywordGroups)으로 변환합니다.
    각 키워드가 독립된 하나의 주제어 그룹이 됩니다.
    """
    keyword_groups = []
    for keyword in keywords:
        group_item = {
            "groupName": keyword,
            "keywords": [keyword],
        }
        keyword_groups.append(group_item)
    return keyword_groups


def request_search_trend(client_id, client_secret, start_date, end_date, time_unit, keyword_groups):
    """
    네이버 클라우드(NCP) 네이버 API 허브 검색어 트렌드 API를 호출하여 응답을 가져옵니다.
    """
    api_url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
        "Content-Type": "application/json",
    }

    request_body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "keywordGroups": keyword_groups,
    }

    response = requests.post(api_url, headers=headers, data=json.dumps(request_body))

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ API 호출 실패 (코드: {response.status_code}): {response.text}")
        return None


def extract_trend_records(api_response):
    """
    API 응답 JSON에서 날짜, 키워드명, 검색 비율(ratio) 데이터를 추출하여 리스트로 만듭니다.
    """
    records = []
    if not api_response or "results" not in api_response:
        return records

    for item in api_response["results"]:
        keyword_name = item.get("title", "")
        for daily_data in item.get("data", []):
            period = daily_data.get("period", "")
            ratio = daily_data.get("ratio", 0.0)
            records.append({
                "date": period,
                "keyword": keyword_name,
                "ratio": ratio,
            })
    return records


def save_trend_to_csv(dataframe, output_path):
    """
    수집된 데이터프레임을 엑셀에서 바로 열기 쉬운 utf-8-sig 인코딩 CSV 파일로 저장합니다.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ CSV 저장 완료: {output_path}")


def determine_search_dates(start_date_input, end_date_input):
    """
    사용자가 입력한 조회 기간을 확인하고, 비어있으면 최근 30일을 자동으로 계산합니다.
    """
    if start_date_input and end_date_input:
        return start_date_input.strip(), end_date_input.strip()

    today = datetime.today()
    default_end = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    default_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    return default_start, default_end


def main():
    print("=" * 60)
    print("📚 네이버 데이터랩 도서 인기 검색어 트렌드 수집기 시작")
    print("=" * 60)

    # 1. API 키 불러오기
    client_id, client_secret = load_environment_keys()
    if not client_id or not client_secret:
        print("❌ 오류: .env 파일에 NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 없습니다.")
        print("프로젝트 루트의 .env 파일을 확인하고 키를 입력해 주세요.")
        return

    # 2. 조회 기간 결정
    start_date, end_date = determine_search_dates(START_DATE, END_DATE)
    print(f"📅 조회 기간: {start_date} ~ {end_date} (구간 단위: {TIME_UNIT})")

    # 3. 키워드를 5개씩 2묶음으로 분할
    keyword_chunks = split_keywords_into_chunks(BOOK_KEYWORDS, chunk_size=5)
    print(f"총 {len(BOOK_KEYWORDS)}개 키워드를 {len(keyword_chunks)}회로 나누어 수집합니다.")

    all_records = []

    # 4. 5개씩 나누어 API 호출
    for index, chunk in enumerate(keyword_chunks, start=1):
        print(f"\n[{index}/{len(keyword_chunks)}] 그룹 조회 중: {chunk}")
        keyword_groups = make_keyword_groups(chunk)
        api_result = request_search_trend(
            client_id=client_id,
            client_secret=client_secret,
            start_date=start_date,
            end_date=end_date,
            time_unit=TIME_UNIT,
            keyword_groups=keyword_groups,
        )

        if api_result:
            chunk_records = extract_trend_records(api_result)
            all_records.extend(chunk_records)
            print(f"  -> {len(chunk_records)}건 데이터 수집 완료")

    if not all_records:
        print("\n❌ 수집된 데이터가 없습니다.")
        return

    # 5. 데이터프레임 변환 및 정렬
    trend_df = pd.DataFrame(all_records)
    trend_df = trend_df.sort_values(by=["date", "keyword"]).reset_index(drop=True)

    # 6. CSV 파일로 저장
    save_file_path = os.path.join("data", f"book_trend_{start_date}_{end_date}.csv")
    save_trend_to_csv(trend_df, save_file_path)

    print("\n🎉 모든 키워드의 검색어 트렌드 수집 및 저장이 완료되었습니다!")
    print(f"📊 수집된 총 데이터 행 수: {len(trend_df)}행")
    print("=" * 60)


if __name__ == "__main__":
    main()
