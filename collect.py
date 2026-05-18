"""
네이버 신용카드검색 광고 순위 수집기
더보기 페이지 전체 순위 수집 (totalSize 기준 자동 페이지네이션)
"""

import urllib.request
import json
import csv
import math
import os
from datetime import datetime

# ── 설정 ──────────────────────────────────────────
# label: 대시보드 표시명
# benefit_category_ids: FilterData 쿼리에서 확인한 fkey 값 (빈 리스트 = 전체)
# sub_benefit_category_ids: 서브카테고리 fkey (옵션)
KEYWORDS = [
    {"label": "신용카드",    "benefit_category_ids": [],      "sub_benefit_category_ids": []},
    {"label": "주유카드",    "benefit_category_ids": [1],     "sub_benefit_category_ids": []},
    {"label": "쇼핑카드",    "benefit_category_ids": [12],    "sub_benefit_category_ids": []},
    {"label": "대중교통카드","benefit_category_ids": [15],    "sub_benefit_category_ids": []},
    {"label": "외식카드",    "benefit_category_ids": [14],    "sub_benefit_category_ids": []},
    {"label": "마일리지카드","benefit_category_ids": [4],     "sub_benefit_category_ids": []},
    {"label": "통신카드",    "benefit_category_ids": [10],    "sub_benefit_category_ids": []},
    {"label": "체크카드",    "benefit_category_ids": [52],    "sub_benefit_category_ids": []},
    {"label": "법인카드",    "benefit_category_ids": [10034], "sub_benefit_category_ids": []},
    {"label": "할인카드",    "benefit_category_ids": [83],    "sub_benefit_category_ids": []},
]

DEVICES = ["mobile", "pc"]
PAGE_SIZE = 10

ENDPOINTS = {
    "mobile": "https://m-card-search.naver.com/graphql",
    "pc": "https://card-search.naver.com/graphql",
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── GraphQL 쿼리 ───────────────────────────────────
QUERY = """
query smartSearch(
  $pageNo: Int
  $pageSize: Int
  $device: AdDeviceType
  $sortMethod: SortMethod
  $where: String
  $bizType: BizType
  $benefitCategoryIds: [Int]
  $subBenefitCategoryIds: [Int]
) {
  cardAdList(
    pageNo: $pageNo
    pageSize: $pageSize
    device: $device
    sortMethod: $sortMethod
    where: $where
    bizType: $bizType
    benefitCategoryIds: $benefitCategoryIds
    subBenefitCategoryIds: $subBenefitCategoryIds
  ) {
    cardAds {
      cardAdId
      cardName
      companyCode
      bizType
      domesticAnnualFee
      foreignAnnualFee
      titleDescription
      annualBenefitStr
      enableNpayMO
      enableNpayPC
    }
    totalSize
    nvkwd
  }
}
"""

# ── 수집 함수 ──────────────────────────────────────
def fetch_cards(device: str, kw: dict, page_no: int) -> dict:
    endpoint = ENDPOINTS[device]
    payload = json.dumps({
        "operationName": "smartSearch",
        "query": QUERY,
        "variables": {
            "pageNo": page_no,
            "pageSize": PAGE_SIZE,
            "device": device,
            "sortMethod": "ri",
            "where": "nexearch",
            "bizType": "CPC",
            "benefitCategoryIds": kw["benefit_category_ids"] or None,
            "subBenefitCategoryIds": kw["sub_benefit_category_ids"] or None,
        },
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
            if device == "mobile"
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://search.naver.com/",
        "Origin": endpoint.replace("/graphql", ""),
    }

    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def collect_all_pages(device: str, kw: dict, collected_at: str) -> list[dict]:
    """totalSize를 보고 전체 페이지를 순회하며 모든 카드를 수집."""
    label = kw["label"]
    rows = []

    # 1페이지로 totalSize 확인
    first = fetch_cards(device, kw, page_no=1)
    card_list = first.get("data", {}).get("cardAdList", {})
    total = card_list.get("totalSize", 0)
    total_pages = math.ceil(total / PAGE_SIZE) if total else 1

    print(f"  {label} / {device}: 전체 {total}개 → {total_pages}페이지 수집")

    for page_no in range(1, total_pages + 1):
        try:
            if page_no == 1:
                data = first
            else:
                data = fetch_cards(device, kw, page_no=page_no)

            cards = data.get("data", {}).get("cardAdList", {}).get("cardAds", [])
            if not cards:
                break

            for rank_in_page, card in enumerate(cards, start=1):
                absolute_rank = (page_no - 1) * PAGE_SIZE + rank_in_page
                rows.append({
                    "collected_at": collected_at,
                    "keyword": label,
                    "benefit_category_ids": ",".join(map(str, kw["benefit_category_ids"])),
                    "device": device,
                    "page": page_no,
                    "rank": absolute_rank,
                    "card_ad_id": card["cardAdId"],
                    "card_name": card["cardName"],
                    "company_code": card["companyCode"],
                    "biz_type": card["bizType"],
                    "annual_fee_domestic": card.get("domesticAnnualFee", ""),
                    "annual_fee_foreign": card.get("foreignAnnualFee", ""),
                    "title_desc": card.get("titleDescription", ""),
                    "total_size": total,
                })
        except Exception as e:
            print(f"    ERR page={page_no} → {e}")
            break

    return rows


def collect_all() -> list[dict]:
    rows = []
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for kw in KEYWORDS:
        for device in DEVICES:
            rows.extend(collect_all_pages(device, kw, collected_at))

    return rows


def save_csv(rows: list[dict], path: str):
    if not rows:
        print("저장할 데이터 없음")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n저장 완료: {path}  ({len(rows)}행)")


# ── 진입점 ─────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTPUT_DIR, f"card_rank_{ts}.csv")

    print(f"수집 시작: {ts}")
    print(f"키워드 {len(KEYWORDS)}개 × 디바이스 {len(DEVICES)}개 (전체 페이지 자동 수집)\n")

    rows = collect_all()
    save_csv(rows, out_path)

    # Google Sheets 업데이트 (credentials.json 있을 때만 동작)
    try:
        from sheets import update_sheets
        update_sheets(rows)
    except ImportError:
        print("[sheets] gspread 미설치 → pip install gspread google-auth")
