"""
네이버 신용카드검색 순위 모니터링 — Streamlit 대시보드
데이터 소스: Google Sheets (history 시트)
실행: streamlit run app.py
"""

import os
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1TkqSvqlpUjyQ2oyWmj9f5ABJw7hHW_oDph-StrzCnG4"
SCOPES         = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS_PATH     = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "samsungcard-cardad-monitor-6634054d5073.json",
)

COMPANY_META = {
    "SS": {"name": "삼성카드",    "color": "#1B3F8B"},
    "KB": {"name": "KB국민카드",  "color": "#9A6F00"},
    "SH": {"name": "신한카드",    "color": "#1E5FA8"},
    "LO": {"name": "롯데카드",    "color": "#B83232"},
    "WR": {"name": "우리카드",    "color": "#2E72A8"},
    "HY": {"name": "현대카드",    "color": "#2C3E50"},
    "HD": {"name": "현대카드",    "color": "#2C3E50"},
    "NH": {"name": "NH농협카드",  "color": "#1A7A4C"},
    "HA": {"name": "하나카드",    "color": "#0B6E6E"},
    "BC": {"name": "BC카드",      "color": "#C0392B"},
    "IB": {"name": "IBK기업은행", "color": "#005BAC"},
    "SK": {"name": "SK카드",      "color": "#E0003C"},
    "HC": {"name": "현대커머셜",  "color": "#4A5568"},
}

st.set_page_config(
    page_title="신용카드검색 순위 모니터링",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stSidebar"] { background: #f8fafc; }
.block-container { padding-top: 1.5rem !important; }
.rank-rows {
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    overflow: hidden;
    background: #fff;
    box-shadow: 0 4px 24px -8px rgba(0,0,0,0.06);
}
.rank-header {
    padding: 16px 20px 12px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: baseline;
    gap: 10px;
}
.rank-title  { font-size:15px; font-weight:600; color:#0f172a; letter-spacing:-0.2px; }
.rank-sub    { font-size:12px; color:#94a3b8; font-family:monospace; }
.rank-row {
    display: grid;
    grid-template-columns: 44px 1fr auto;
    align-items: center;
    padding: 10px 20px;
    gap: 10px;
    border-top: 1px solid #f1f5f9;
}
.rank-row:first-child { border-top: none; }
.rank-row:hover { background: #f8fafc; }
.rank-badge {
    width:30px; height:30px; border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:700; font-family:monospace; flex-shrink:0;
}
.r1 { background:#fef3c7; color:#b45309; }
.r2 { background:#f1f5f9; color:#64748b; }
.r3 { background:#fdf4ff; color:#9333ea; }
.rn { background:#f8fafc; color:#94a3b8; font-weight:500; }
.card-name-txt { font-size:14px; font-weight:500; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card-co { display:inline-flex; align-items:center; gap:5px; margin-top:2px; font-size:11px; font-weight:500; color:#94a3b8; }
.co-dot  { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.fee      { font-size:12px; font-family:monospace; color:#94a3b8; white-space:nowrap; }
.fee-free { color:#16a34a; font-weight:500; }
.sidebar-label { font-size:11px; font-weight:600; letter-spacing:0.5px; text-transform:uppercase; color:#94a3b8; margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)


def _get_creds():
    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES
        )
    return Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)


@st.cache_data(ttl=300)
def load_from_sheets() -> pd.DataFrame:
    gc = gspread.authorize(_get_creds())
    ws = gc.open_by_key(SPREADSHEET_ID).worksheet("history")
    values = ws.get_all_values()
    if len(values) < 2:
        return pd.DataFrame()
    headers, rows = values[0], values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["annual_fee_domestic"] = pd.to_numeric(df["annual_fee_domestic"], errors="coerce")
    df["total_size"] = pd.to_numeric(df["total_size"], errors="coerce")
    return df


df_all = load_from_sheets()

if df_all.empty:
    st.error("시트에 데이터가 없습니다. `python collect.py`를 먼저 실행해주세요.")
    st.stop()

# ── Sidebar ────────────────────────────────────
with st.sidebar:
    st.markdown("## 신용카드검색 모니터링")
    st.markdown("---")

    st.markdown('<div class="sidebar-label">수집 시각</div>', unsafe_allow_html=True)
    timestamps = sorted(df_all["collected_at"].unique(), reverse=True)
    selected_ts = st.selectbox("수집 시각", timestamps, label_visibility="collapsed")

    df_snap = df_all[df_all["collected_at"] == selected_ts]

    st.markdown('<div class="sidebar-label" style="margin-top:12px;">키워드</div>', unsafe_allow_html=True)
    keywords = df_snap["keyword"].unique().tolist()
    selected_kw = st.selectbox("키워드", keywords, label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:12px;">디바이스</div>', unsafe_allow_html=True)
    selected_device = st.radio(
        "디바이스", ["mobile", "pc"],
        format_func=lambda x: "모바일" if x == "mobile" else "PC",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-label" style="margin-top:12px;">카드명 검색</div>', unsafe_allow_html=True)
    search_q = st.text_input("검색", placeholder="카드명 또는 카드사", label_visibility="collapsed")

    st.markdown("---")
    if st.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Filter ─────────────────────────────────────
mask = (
    (df_all["collected_at"] == selected_ts) &
    (df_all["keyword"] == selected_kw) &
    (df_all["device"] == selected_device)
)
df = df_all[mask].sort_values("rank").reset_index(drop=True)

df["company_name"]  = df["company_code"].map(lambda c: COMPANY_META.get(c, {}).get("name", c))
df["company_color"] = df["company_code"].map(lambda c: COMPANY_META.get(c, {}).get("color", "#888"))

df_display = df.copy()
if search_q:
    q = search_q.lower()
    df_display = df_display[
        df_display["card_name"].str.lower().str.contains(q, na=False) |
        df_display["company_name"].str.lower().str.contains(q, na=False) |
        df_display["company_code"].str.lower().str.contains(q, na=False)
    ]

# ── Header ─────────────────────────────────────
total_size  = int(df["total_size"].iloc[0]) if len(df) > 0 else 0
n_collected = len(df)
n_companies = df["company_code"].nunique()
dev_label   = "모바일" if selected_device == "mobile" else "PC"

st.markdown(f"""
<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:16px;">
  <h2 style="margin:0;font-size:20px;font-weight:700;color:#0f172a;letter-spacing:-0.5px;">
    {selected_kw} · {dev_label} 순위
  </h2>
  <span style="color:#94a3b8;font-size:12px;font-family:monospace;">{selected_ts}</span>
</div>
""", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("전체 광고 카드", f"{total_size:,}개")
m2.metric("수집 순위",      f"{n_collected:,}위")
m3.metric("노출 카드사",    f"{n_companies}개")

st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

# ── Two-column layout ──────────────────────────
rank_col, side_col = st.columns([3, 2], gap="large")

with rank_col:
    sub_text = (
        f"검색 결과 {len(df_display):,}개"
        if search_q
        else f"전체 {total_size:,}개 · 수집 {n_collected:,}위"
    )

    rows_html = ""
    for _, r in df_display.iterrows():
        rank = int(r["rank"])
        rc = "r1" if rank == 1 else "r2" if rank == 2 else "r3" if rank == 3 else "rn"
        fee_val = r.get("annual_fee_domestic", "")
        try:
            fee_int = int(fee_val)
            fee_html = '<span class="fee fee-free">무료</span>' if fee_int == 0 else f'<span class="fee">{fee_int:,}원</span>'
        except (ValueError, TypeError):
            fee_html = '<span class="fee fee-free">무료</span>'

        rows_html += f"""
        <div class="rank-row">
          <div class="rank-badge {rc}">{rank}</div>
          <div style="min-width:0;">
            <div class="card-name-txt">{r["card_name"]}</div>
            <div class="card-co">
              <span class="co-dot" style="background:{r["company_color"]}"></span>
              {r["company_name"]}
            </div>
          </div>
          {fee_html}
        </div>"""

    if not rows_html:
        rows_html = '<div style="padding:32px;text-align:center;color:#94a3b8;font-size:13px;">검색 결과가 없습니다.</div>'

    st.markdown(f"""
    <div class="rank-rows">
      <div class="rank-header">
        <span class="rank-title">{selected_kw} · {dev_label}</span>
        <span class="rank-sub">{sub_text}</span>
      </div>
      <div style="max-height:600px;overflow-y:auto;">{rows_html}</div>
    </div>
    """, unsafe_allow_html=True)

with side_col:
    # Company bars
    co_counts = df.groupby(["company_code", "company_name"]).size().reset_index(name="cnt")
    co_counts = co_counts.sort_values("cnt", ascending=False)
    co_counts["color"] = co_counts["company_code"].map(lambda c: COMPANY_META.get(c, {}).get("color", "#888"))
    co_counts["pct"]   = (co_counts["cnt"] / len(df) * 100).round(1)
    max_cnt = co_counts["cnt"].max() if len(co_counts) > 0 else 1

    bars_html = ""
    for _, row in co_counts.iterrows():
        w = row["cnt"] / max_cnt * 100
        bars_html += f"""
        <div style="margin-bottom:9px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
            <span style="font-size:13px;font-weight:500;color:#0f172a;">{row["company_name"]}</span>
            <span style="font-size:11px;color:#64748b;font-family:monospace;">{int(row["cnt"])}개 <span style="color:#94a3b8;">({row["pct"]}%)</span></span>
          </div>
          <div style="height:5px;background:#f1f5f9;border-radius:999px;overflow:hidden;">
            <div style="width:{w:.1f}%;height:100%;background:{row["color"]};border-radius:999px;"></div>
          </div>
        </div>"""

    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
                padding:20px 22px;box-shadow:0 4px 24px -8px rgba(0,0,0,0.06);margin-bottom:16px;">
      <div style="font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;
                  color:#94a3b8;margin-bottom:14px;">카드사별 점유</div>
      {bars_html}
    </div>
    """, unsafe_allow_html=True)

    # Top 10 pips
    top10_df = df[df["rank"] <= 10]
    pips_html = ""
    if len(top10_df) > 0:
        top10_grp = top10_df.groupby(["company_code", "company_name"])["rank"].apply(list).reset_index()
        top10_grp["n"] = top10_grp["rank"].apply(len)
        top10_grp = top10_grp.sort_values("n", ascending=False)

        for _, row in top10_grp.iterrows():
            color = COMPANY_META.get(row["company_code"], {}).get("color", "#888")
            pips = "".join(
                f'<span style="display:inline-block;width:13px;height:13px;border-radius:3px;background:{color};margin:1px;"></span>'
                if i in row["rank"] else
                '<span style="display:inline-block;width:13px;height:13px;border-radius:3px;background:#f1f5f9;border:1px solid #e2e8f0;margin:1px;"></span>'
                for i in range(1, 11)
            )
            pips_html += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:6px 0;border-bottom:1px solid #f8fafc;">
              <span style="font-size:13px;color:#0f172a;">{row["company_name"]}</span>
              <div style="line-height:1;">{pips}</div>
            </div>"""

    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
                padding:20px 22px;box-shadow:0 4px 24px -8px rgba(0,0,0,0.06);">
      <div style="font-size:11px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;
                  color:#94a3b8;margin-bottom:14px;">Top 10 슬롯</div>
      {pips_html if pips_html else '<div style="color:#94a3b8;font-size:13px;">데이터 없음</div>'}
    </div>
    """, unsafe_allow_html=True)
