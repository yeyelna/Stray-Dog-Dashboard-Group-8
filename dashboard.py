# dashboard.py
# Smart City Stray Dog Control System (Streamlit Cloud ready)
# Reads Google Sheets (published CSV) with columns:
# timestamp, camera_id, location, class, confidence, image

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================
TZ_NAME = "Asia/Kuala_Lumpur"
TZ = ZoneInfo(TZ_NAME)

ACTIVE_SEC = 120               # system "active" if last record within 2 minutes
NEW_ALERTS_LIVE_MIN = 10       # header "new alerts" window (last 10 minutes)
ALERT_CONF_TH = 0.70           # "New Alerts" threshold
HIGH_PRIORITY_CONF_TH = 0.90   # "High Priority" threshold

# Put your CSV URL in Streamlit Cloud Secrets:
# SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv"
DEFAULT_SHEET_CSV_URL = "PASTE_YOUR_PUBLISHED_CSV_URL_HERE"

st.set_page_config(page_title="Stray Dog Dashboard", page_icon="🐶", layout="wide")

# =========================
# STYLES (LIGHT CREAM BACKGROUND)
# =========================
st.markdown(
    """
    <style>
    /* ===== Page background ===== */
    .stApp{ background:#f7f4ef; }

    .page-wrap{max-width:1200px;margin:0 auto;}

    /* ===== Header row ===== */
    .header-row{
      display:flex;align-items:flex-start;justify-content:space-between;
      gap:16px;margin-top:8px;margin-bottom:10px;flex-wrap:wrap;
    }
    .title-wrap{min-width:260px;flex:1 1 420px;}
    .title-wrap h1{margin:0;font-size:34px;line-height:1.15;color:#111827;}
    .title-wrap p{margin:6px 0 0 0;color:#4b5563;font-size:14px;}

    .status-wrap{
      display:flex;gap:10px;align-items:stretch;justify-content:flex-end;
      flex:0 1 520px;flex-wrap:wrap;
    }
    .mini-box{
      border:1px solid #e5e7eb;border-radius:14px;background:#ffffff;
      padding:12px 14px;min-width:220px;box-shadow:0 1px 0 rgba(0,0,0,0.03);
      overflow:hidden;flex:1 1 220px;
    }
    .mini-top{
      display:flex;align-items:center;justify-content:space-between;
      gap:10px;margin-bottom:10px;flex-wrap:wrap;
    }
    .pill{
      font-size:12px;font-weight:700;border-radius:999px;padding:6px 12px;
      border:1px solid #e5e7eb;background:#f9fafb;color:#111827;white-space:nowrap;
    }
    .pill-ok{background:#ecfdf5;border-color:#a7f3d0;color:#065f46;}
    .pill-bad{background:#fef2f2;border-color:#fecaca;color:#991b1b;}

    /* Red NEW ALERTS box */
    .mini-box-alert{border:1px solid #fecaca;background:#fef2f2;}
    .pill-alert{background:#fee2e2;border-color:#fecaca;color:#991b1b;}

    .mini-label{font-size:12px;color:#6b7280;margin:0;overflow-wrap:anywhere;}
    .mini-value{font-size:22px;font-weight:800;margin:4px 0 0 0;color:#111827;overflow-wrap:anywhere;}

    /* Divider line under header */
    .header-divider{border-top:1px solid #e5e7eb;margin:8px 0 14px 0;}

    /* KPI cards */
    .kpi-card{
      border:1px solid #e5e7eb;border-radius:16px;background:#ffffff;
      padding:14px 16px;box-shadow:0 1px 0 rgba(0,0,0,0.03);
      height:110px;overflow:hidden;
    }
    .kpi-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px;flex-wrap:wrap;}
    .kpi-icon{width:34px;height:34px;border-radius:12px;display:flex;align-items:center;justify-content:center;border:1px solid #e5e7eb;background:#f9fafb;font-size:18px;}
    .kpi-number{font-size:30px;font-weight:800;margin:0;color:#111827;line-height:1;overflow-wrap:anywhere;}
    .kpi-label{font-size:13px;color:#6b7280;margin:6px 0 0 0;overflow-wrap:anywhere;}
    .delta{font-size:12px;font-weight:700;border-radius:10px;padding:4px 8px;white-space:nowrap;border:1px solid #e5e7eb;background:#f9fafb;color:#111827;}
    .delta-up{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
    .delta-down{background:#ecfdf5;border-color:#a7f3d0;color:#065f46;}
    .delta-flat{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# HELPERS
# =========================
def _to_kl(dt: pd.Timestamp) -> pd.Timestamp:
    """Convert timezone-aware pandas Timestamp to KL; localize naive to KL."""
    if pd.isna(dt):
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ)
    return dt.tz_convert(TZ)

def parse_mixed_timestamp(series: pd.Series) -> pd.Series:
    """
    Accepts both:
    - ISO with timezone: 2025-11-27T01:18:13.160678+00:00
    - dd/mm/yyyy hh:mm: 05/12/2025 17:44
    Returns timezone-aware timestamps in Asia/Kuala_Lumpur.
    """
    s = series.astype(str).str.strip()

    # Parse ISO strings as UTC
    dt_iso = pd.to_datetime(s, errors="coerce", utc=True)

    # Parse remaining as dd/mm/yyyy hh:mm (naive)
    mask = dt_iso.isna()
    dt_dmy = pd.to_datetime(s[mask], errors="coerce", dayfirst=True)

    # Combine
    dt_iso.loc[mask] = dt_dmy

    # Convert/localize to KL
    out = dt_iso.apply(_to_kl)
    return out

@st.cache_data(ttl=10)
def load_gsheets_csv(url: str) -> pd.DataFrame:
    """Load CSV and normalize columns."""
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
    """Percent change vs yesterday; handles zero gracefully."""
    if yesterday is None or pd.isna(yesterday):
        return None
    if yesterday == 0:
        return None if today == 0 else float("inf")
    return ((today - yesterday) / yesterday) * 100.0

def render_delta(val):
    """Return (text, css_class) for delta badge."""
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
    """Render one KPI card."""
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
    st.warning("Set your Google Sheets published CSV URL in Streamlit secrets (SHEET_CSV_URL).")
    st.stop()

try:
    df = load_gsheets_csv(sheet_url)
except Exception as e:
    st.error("Failed to load Google Sheets CSV. Ensure the sheet is published to CSV and the link is correct.")
    st.caption(f"Error: {e}")
    st.stop()

df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

# =========================
# TIME WINDOWS (CLOUD-SAFE)
# =========================
now = datetime.now(TZ)

# IMPORTANT: don't pass tz=ZoneInfo into pd.Timestamp (can break on Streamlit Cloud)
live_start = pd.Timestamp(now - timedelta(minutes=NEW_ALERTS_LIVE_MIN))

# start of today in KL
today_start = pd.Timestamp(datetime.combine(now.date(), time(0, 0)), tz=TZ_NAME)

# yesterday range
yday_date = (now - timedelta(days=1)).date()
yday_start = pd.Timestamp(datetime.combine(yday_date, time(0, 0)), tz=TZ_NAME)
yday_end = today_start

# =========================
# FILTERS
# =========================
df_live = df[df["timestamp"] >= live_start]
df_today = df[(df["timestamp"] >= today_start) & (df["timestamp"] < today_start + pd.Timedelta(days=1))]
df_yday = df[(df["timestamp"] >= yday_start) & (df["timestamp"] < yday_end)]

# =========================
# METRICS
# =========================
last_seen = df["timestamp"].max() if len(df) else pd.NaT

# IMPORTANT: don't do pd.Timestamp(now, tz=TZ). Just use pd.Timestamp(now).
system_active = False if pd.isna(last_seen) else (pd.Timestamp(now) - last_seen) <= pd.Timedelta(seconds=ACTIVE_SEC)

# Header "Incoming alerts" (live)
new_alerts_live = int((df_live["confidence"] >= ALERT_CONF_TH).sum())

# KPI 1: New Alerts (today) - thresholded by confidence
new_alerts_today = int((df_today["confidence"] >= ALERT_CONF_TH).sum())
new_alerts_yday = int((df_yday["confidence"] >= ALERT_CONF_TH).sum())

# KPI 2: Total Dogs Detected (today) - sum only class == "dog"
total_dogs_today = int((df_today["class"].astype(str).str.lower() == "dog").sum()) if len(df_today) else 0
total_dogs_yday = int((df_yday["class"].astype(str).str.lower() == "dog").sum()) if len(df_yday) else 0

# KPI 3: High Priority (today) - stronger confidence threshold
high_today = int((df_today["confidence"] >= HIGH_PRIORITY_CONF_TH).sum())
high_yday = int((df_yday["confidence"] >= HIGH_PRIORITY_CONF_TH).sum())

# Deltas vs yesterday
d_new_txt, d_new_cls = render_delta(pct_change(new_alerts_today, new_alerts_yday))
d_tot_txt, d_tot_cls = render_delta(pct_change(total_dogs_today, total_dogs_yday))
d_high_txt, d_high_cls = render_delta(pct_change(high_today, high_yday))

# =========================
# HEADER (TOP, WITH DIVIDER LINE)
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
# KPI CARDS (3)
# =========================
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    kpi_card("🚨", "New Alerts", new_alerts_today, d_new_txt, d_new_cls)

with col2:
    kpi_card("📈", "Total Dogs Detected (Today)", total_dogs_today, d_tot_txt, d_tot_cls)

with col3:
    kpi_card("⚠️", "High Priority", high_today, d_high_txt, d_high_cls)

st.markdown("</div>", unsafe_allow_html=True)
