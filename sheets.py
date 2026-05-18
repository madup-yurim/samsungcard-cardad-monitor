"""
Google Sheets 업데이트 모듈

사전 준비:
  1. pip install gspread google-auth
  2. Google Cloud Console → 서비스 계정 생성 → JSON 키 다운로드
  3. 키 파일을 이 프로젝트 폴더에 credentials.json 으로 저장
  4. 해당 서비스 계정 이메일을 스프레드시트에 편집자 권한으로 공유
     (또는 아래 create 시 drive 권한으로 자동 공유)
"""

import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CREDS_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsungcard-cardad-monitor-6634054d5073.json")
SPREADSHEET_ID   = "1TkqSvqlpUjyQ2oyWmj9f5ABJw7hHW_oDph-StrzCnG4"
SHEET_LATEST     = "latest"
SHEET_HISTORY    = "history"

FIELDNAMES = [
    "collected_at", "keyword", "benefit_category_ids", "device",
    "page", "rank", "card_ad_id", "card_name", "company_code",
    "biz_type", "annual_fee_domestic", "annual_fee_foreign",
    "title_desc", "total_size",
]


def _get_client():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_spreadsheet(gc):
    return gc.open_by_key(SPREADSHEET_ID)


def _ensure_sheet(ss, title: str):
    try:
        return ss.worksheet(title)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=title, rows=1, cols=len(FIELDNAMES))


def update_sheets(rows: list[dict]):
    """
    collect_all() 반환값을 받아 두 시트를 업데이트합니다.
    - latest  : 이번 수집분으로 전체 덮어쓰기
    - history : 이번 수집분을 뒤에 추가 (헤더 중복 없음)
    """
    if not rows:
        print("[sheets] 업데이트할 데이터 없음")
        return

    if not os.path.exists(CREDS_PATH):
        print(f"[sheets] credentials.json 없음 → 시트 업데이트 건너뜀")
        print(f"         경로: {CREDS_PATH}")
        return

    try:
        gc = _get_client()
        ss = _get_spreadsheet(gc)

        data_rows = [[str(r.get(f, "")) for f in FIELDNAMES] for r in rows]

        # latest: 헤더 + 전체 데이터로 덮어쓰기
        ws_latest = _ensure_sheet(ss, SHEET_LATEST)
        ws_latest.clear()
        ws_latest.update([FIELDNAMES] + data_rows)
        print(f"[sheets] latest 시트 업데이트 완료 ({len(rows)}행)")

        # history: 없으면 헤더 포함 생성, 있으면 데이터만 추가
        ws_history = _ensure_sheet(ss, SHEET_HISTORY)
        existing = ws_history.get_all_values()
        if not existing:
            ws_history.update([FIELDNAMES] + data_rows)
        else:
            ws_history.append_rows(data_rows, value_input_option="USER_ENTERED")
        print(f"[sheets] history 시트 추가 완료 ({len(rows)}행)")

        print(f"[sheets] URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

    except Exception as e:
        print(f"[sheets] 오류 → {e}")
