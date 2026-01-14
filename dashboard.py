# app.py
# Smart City Stray Dog Control System (Streamlit Cloud ready)
# Data source: Google Sheets (published to CSV) with columns:
# timestamp, camera_id, location, class, confidence, image

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# =========================
# CONFIG (edit if needed)
# =========================
TZ = ZoneInfo("Asia/Kuala_Lumpur")
ACTIVE_SEC = 120               # system "active" if last record within 2 minutes
NEW_ALERTS_LIVE_MIN = 10       # header "XX new alerts" window (last 10 minutes)
ALERT_CONF_TH = 0.70           # "New Alerts" threshold
HIGH_PRIORITY_CONF_TH = 0.90   # "High Priority" threshold

# Prefer Streamlit secrets on Cloud:
# - Streamlit Cloud -> App settings -> Secrets:
#   SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv"
DEFAULT_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"

st.set_page_config(page_title="Stray Dog Detection Dashboard", page_icon="🐶", layout="wide")

# =========================
# STYLES
# =========================
st.markdown('<div class="page-wrap">', unsafe_allow_html=True)

status_pill = "pill-ok" if system_active else "pill-bad"
status_text = "SYSTEM ACTIVE" if system_active else "SYSTEM INACTIVE"

st.markdown(
    f"""
    <div class="header-row">
      <div class="title-wrap">
        <h1>🐶 Smart City Stray Dog Control System</h1>
        <p>Real-Time AI Detection Monitoring</p>
      </div>

      <div class="status-wrap">

        <!-- System Status box (NO TIMESTAMP PILL) -->
        <div class="mini-box">
          <div class="mini-top">
            <span class="pill {status_pill}">{status_text}</span>
          </div>
          <p class="mini-label">Last update</p>
          <p class="mini-value">{("—" if pd.isna(last_seen) else last_seen.strftime("%d/%m/%Y %H:%M"))}</p>
        </div>

        <!-- New Alerts box (RED, NO "10 min") -->
        <div class="mini-box mini-box-alert">
          <div class="mini-top">
            <span class="pill pill-alert">NEW ALERTS</span>
          </div>
          <p class="mini-label">Incoming alerts</p>
          <p class="mini-value">{new_alerts_live}</p>
        </div>

      </div>
    </div>

    <div class="header-divider"></div>
    """,
    unsafe_allow_html=True,
)


# =========================
# HELPERS
# =========================
def _to_kl(dt: pd.Timestamp) -> pd.Timestamp:
    if pd.isna(dt):
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.tz_convert(TZ)

def parse_mixed_timestamp(series: pd.Series) -> pd.Series:
    # Handles both:
    # 1) ISO with timezone: 2025-11-27T01:18:13.160678+00:00
    # 2) dd/mm/yyyy hh:mm: 05/12/2025 17:44
    s = series.astype(str).str.strip()
    dt_iso = pd.to_datetime(s, errors="coerce", utc=True)  # catches ISO (+00:00, Z, etc.)
    mask = dt_iso.isna()
    dt_dmy = pd.to_datetime(s[mask], errors="coerce", dayfirst=True)  # catches dd/mm/yyyy hh:mm
    dt_iso.loc[mask] = dt_dmy
    # If dt is timezone-aware (from utc=True), convert to KL; if naive, localize as KL
    out = dt_iso.apply(_to_kl)
    return out

@st.cache_data(ttl=10)
def load_gsheets_csv(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = [c.strip().lower() for c in df.columns]
    expected = ["timestamp", "camera_id", "location", "class", "confidence", "image"]
    for c in expected:
        if c not in df.columns:
            df[c] = None
    df["timestamp"] = parse_mixed_timestamp(df["timestamp"])
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    return df

def pct_change(today: int, yesterday: int):
    if yesterday is None or pd.isna(yesterday):
        return None
    if yesterday == 0:
        return None if today == 0 else float("inf")
    return ((today - yesterday) / yesterday) * 100.0

def render_delta(val):
    if val is None:
        return ("—", "delta")
    if val == float("inf"):
        return ("+∞", "delta-up")
    if abs(val) < 0.0001:
        return ("0%", "delta-flat")
    sign = "+" if val > 0 else ""
    cls = "delta-up" if val > 0 else "delta-down"
    return (f"{sign}{val:.0f}%", cls)

def kpi_card(icon, title, value, delta_text, delta_class):
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon">{icon}</div>
            <div class="delta {delta_class}">{delta_text}</div>
          </div>
          <p class="kpi-number">{value}</p>
          <p class="kpi-label">{title}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# LOAD DATA
# =========================
sheet_url = st.secrets.get("SHEET_CSV_URL", DEFAULT_SHEET_CSV_URL)
if not sheet_url or "PASTE_YOUR_PUBLISHED_CSV_URL_HERE" in sheet_url:
    st.warning("Set your Google Sheets published CSV URL in Streamlit secrets (SHEET_CSV_URL) or replace DEFAULT_SHEET_CSV_URL in code.")
    st.stop()

try:
    df = load_gsheets_csv(sheet_url)
except Exception as e:
    st.error("Failed to load Google Sheets CSV. Check the URL and that the sheet is published to CSV.")
    st.caption(f"Error: {e}")
    st.stop()

df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

# =========================
# TIME WINDOWS (FIXED)
# =========================
now = datetime.now(TZ)

# FIX: don't pass tz=ZoneInfo into pd.Timestamp here
live_start = pd.Timestamp(now - timedelta(minutes=NEW_ALERTS_LIVE_MIN))

# keep these timezone-safe (use tz string, not ZoneInfo)
today_start = pd.Timestamp(datetime.combine(now.date(), time(0, 0)), tz="Asia/Kuala_Lumpur")
yday_date = (now - timedelta(days=1)).date()
yday_start = pd.Timestamp(datetime.combine(yday_date, time(0, 0)), tz="Asia/Kuala_Lumpur")
yday_end = today_start

last_seen = df["timestamp"].max() if len(df) else pd.NaT
system_active = False if pd.isna(last_seen) else (pd.Timestamp(now) - last_seen) <= pd.Timedelta(seconds=ACTIVE_SEC)

df_live = df[df["timestamp"] >= live_start]
df_today = df[(df["timestamp"] >= today_start) & (df["timestamp"] < today_start + pd.Timedelta(days=1))]
df_yday = df[(df["timestamp"] >= yday_start) & (df["timestamp"] < yday_end)]

# Metrics (you can tweak definitions)
new_alerts_live = int((df_live["confidence"] >= ALERT_CONF_TH).sum())
new_alerts_today = int((df_today["confidence"] >= ALERT_CONF_TH).sum())
new_alerts_yday = int((df_yday["confidence"] >= ALERT_CONF_TH).sum())

total_dogs_today = int((df_today["class"].astype(str).str.lower() == "dog").sum()) if len(df_today) else 0
total_dogs_yday = int((df_yday["class"].astype(str).str.lower() == "dog").sum()) if len(df_yday) else 0

high_today = int((df_today["confidence"] >= HIGH_PRIORITY_CONF_TH).sum())
high_yday = int((df_yday["confidence"] >= HIGH_PRIORITY_CONF_TH).sum())

# Deltas vs yesterday
d_new = pct_change(new_alerts_today, new_alerts_yday)
d_tot = pct_change(total_dogs_today, total_dogs_yday)
d_high = pct_change(high_today, high_yday)
d_new_txt, d_new_cls = render_delta(d_new)
d_tot_txt, d_tot_cls = render_delta(d_tot)
d_high_txt, d_high_cls = render_delta(d_high)

# =========================
# HEADER
# =========================
st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
status_pill = "pill-ok" if system_active else "pill-bad"
status_text = "SYSTEM ACTIVE" if system_active else "SYSTEM INACTIVE"
st.markdown(
    f"""
    <div class="header-row">
      <div class="title-wrap">
        <h1>🐶 Smart City Stray Dog Control System</h1>
        <p>Real-Time AI Detection Monitoring</p>
      </div>
      <div class="status-wrap">
        <div class="mini-box">
          <div class="mini-top">
            <span class="pill {status_pill}">{status_text}</span>
            <span class="pill">{now.strftime("%d/%m/%Y %H:%M")}</span>
          </div>
          <p class="mini-label">Last update</p>
          <p class="mini-value">{("—" if pd.isna(last_seen) else last_seen.strftime("%d/%m/%Y %H:%M"))}</p>
        </div>
        <div class="mini-box">
          <div class="mini-top">
            <span class="pill">NEW ALERTS</span>
            <span class="pill">{NEW_ALERTS_LIVE_MIN} min</span>
          </div>
          <p class="mini-label">Incoming alerts</p>
          <p class="mini-value">{new_alerts_live}</p>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# KPI CARDS (3)
# =========================
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    kpi_card("🚨", "New Alerts", new_alerts_today, d_new_txt, d_new_cls)
with c2:
    kpi_card("📈", "Total Dogs Detected (Today)", total_dogs_today, d_tot_txt, d_tot_cls)
with c3:
    kpi_card("⚠️", "High Priority", high_today, d_high_txt, d_high_cls)

st.markdown("</div>", unsafe_allow_html=True)

# OPTIONAL: Uncomment if you want auto refresh on Streamlit Cloud
# st.rerun() is not suitable; use streamlit-autorefresh instead (add to requirements.txt)
# from streamlit_autorefresh import st_autorefresh
# st_autorefresh(interval=8000, key="refresh")
