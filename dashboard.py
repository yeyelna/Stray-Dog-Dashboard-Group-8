import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Smart City Stray Dog Control System", layout="wide")
TZ = ZoneInfo("Asia/Kuala_Lumpur")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_SEC = 8

SINGLE_CAMERA_NAME = "WEBCAM"
SINGLE_LOCATION_NAME = "WEBCAM"
SCROLL_AREA_HEIGHT = 440  

st_autorefresh(interval=REFRESH_SEC * 1000, key="auto_refresh")

# =========================
# CSS: THE "FLOATING CARD" STYLE
# =========================
st.markdown(
    f"""
<style>
/* 1. Set Main Background to Light Gray */
.stApp {{
    background-color: #f1f5f9; /* Slate-100 */
}}

/* 2. Style the "Cards" (The border=True containers) */
/* Instead of a line border, we give it a White Background + Shadow */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important; /* Very subtle border */
    border-radius: 16px !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important; /* The "Float" effect */
    padding: 20px !important;
    margin-bottom: 20px !important;
}}

/* 3. Remove Inner "Ghost" Borders */
/* Ensures the internal scroll area is invisible, just content */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}}

/* General Typography & Headers */
html,body,[class*="css"]{{font-family:Inter,system-ui,sans-serif}}
.stApp, .stApp *{{color:#0f172a !important}}
.headerbar{{
  background:#ffffff;
  border-radius:16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding:16px 24px;
  margin-bottom:24px;
  border-left: 6px solid #3b82f6; /* Accent line on header */
}}
.title{{font-size:24px;font-weight:900;margin-bottom:4px}}
.subtitle{{font-size:14px;color:#64748b !important}}

/* KPI & Badges */
.kpi-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.kpi-val{{font-size:38px;font-weight:900;color:#0f172a !important;line-height:1}}
.kpi-lab{{font-size:14px;color:#64748b !important;font-weight:600}}
.pill-red{{background:#fee2e2 !important;border-color:#fecaca !important;color:#991b1b !important; padding:4px 12px; border-radius:99px; font-weight:bold; font-size:12px; border:1px solid}}

/* Thumbnails & Lists */
.thumb{{border-radius:12px;overflow:hidden;background:#f8fafc;position:relative;border:1px solid #e2e8f0}}
.thumb img{{display:block;width:100%;height:220px;object-fit:cover}}
.thumb-title{{font-weight:900;margin-top:12px;font-size:16px}}
.thumb-sub{{margin-top:2px;color:#64748b !important;font-size:13px}}

/* List Item Style */
.list-item {{
    padding:12px;
    border-radius:12px;
    background:#f8fafc; /* Slightly darker than card */
    border:1px solid #e2e8f0;
    margin-bottom:10px;
    transition: all 0.2s;
}}
.list-item:hover {{
    border-color: #cbd5e1;
    background: #f1f5f9;
}}

/* Badges */
.badge{{font-size:11px;font-weight:800;padding:4px 8px;border-radius:6px;display:inline-block}}
.badge-low{{background:#dbeafe !important;color:#1e40af !important}}
.badge-med{{background:#fef3c7 !important;color:#92400e !important}}
.badge-high{{background:#ffedd5 !important;color:#9a3412 !important}}
.badge-crit{{background:#ffe4e6 !important;color:#9f1239 !important}}
.badge-time{{background:#ffffff !important;color:#64748b !important;border:1px solid #e2e8f0; border-radius:12px; padding:2px 8px; font-size:11px}}

/* Buttons */
.stButton > button{{width:100%;border-radius:10px !important;font-weight:700 !important;}}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HELPERS & DATA
# =========================
def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def parse_ts(x):
    if pd.isna(x): return pd.NaT
    s = str(x).strip()
    if s == "": return pd.NaT
    try:
        if "/" in s and ":" in s and "t" not in s.lower():
            dt = datetime.strptime(s, "%d/%m/%Y %H:%M")
            return dt.replace(tzinfo=TZ)
    except: pass
    try:
        dt = parser.isoparse(s)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except: return pd.NaT

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns: return c
    return None

def coerce_int_series(s, default=1):
    return pd.to_numeric(s, errors="coerce").fillna(default).clip(lower=0).astype(int)

def normalize_confidence(series):
    x = pd.to_numeric(series, errors="coerce")
    if x.notna().sum() == 0: return x
    med = np.nanmedian(x.values.astype(float))
    if med <= 1.0: x = x * 100.0
    return x.clip(0, 100)

def severity_badge(sev):
    sev = str(sev).strip().upper()
    if sev == "LOW": return "badge badge-low", "LOW"
    if sev == "MEDIUM": return "badge badge-med", "MEDIUM"
    if sev == "HIGH": return "badge badge-high", "HIGH"
    if sev == "CRITICAL": return "badge badge-crit", "CRITICAL"
    return "badge badge-med", (sev if sev else "MEDIUM")

def pct_change(today_val, yday_val):
    if yday_val == 0: return 0.0 if today_val == 0 else 100.0
    return ((today_val - yday_val) / yday_val) * 100.0

def time_ago(ts: datetime, now_: datetime) -> str:
    secs = int(max(0, (now_ - ts).total_seconds()))
    if secs < 60: return "just now"
    mins = secs // 60
    if mins < 60: return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 24: return f"{hrs}h ago"
    days = hrs // 24
    return f"{days}d ago"

@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data(url):
    df = pd.read_csv(url, dtype=str, engine="python", on_bad_lines="skip")
    return _clean_cols(df)

raw = load_data(SHEET_CSV_URL)
if raw.empty: st.stop()

col_ts = pick_col(raw, ["timestamp", "time", "datetime", "date_time"])
col_id = pick_col(raw, ["detection_id", "det_id", "id", "event_id"])
col_loc = pick_col(raw, ["location", "area", "zone"])
col_cam = pick_col(raw, ["camera", "camera_id", "cam"])
col_camtype = pick_col(raw, ["camera_type", "type"])
col_dogs = pick_col(raw, ["dogs", "dog_count", "num_dogs"])
col_conf = pick_col(raw, ["confidence", "conf", "score"])
col_sev = pick_col(raw, ["severity", "priority", "level"])
col_status = pick_col(raw, ["status", "alert_status"])
img_candidates = [c for c in raw.columns if ("url" in c or "image" in c or "snapshot" in c or "photo" in c)]
col_img = pick_col(raw, ["snapshot_url", "image_url", "url"]) or (img_candidates[0] if img_candidates else None)

if col_ts is None: st.stop()

df = raw.copy()
df["ts"] = df[col_ts].apply(parse_ts)
df = df.dropna(subset=["ts"]).copy()

if col_id is None: df["detection_id"] = ["DET-" + str(i).zfill(6) for i in range(1, len(df) + 1)]; col_id = "detection_id"
if col_cam is None: df["camera"] = SINGLE_CAMERA_NAME; col_cam = "camera"
if col_camtype is None: df["camera_type"] = SINGLE_CAMERA_NAME; col_camtype = "camera_type"
if col_loc is None: df["location"] = SINGLE_LOCATION_NAME; col_loc = "location"
if col_dogs is None: df["dogs"] = 1; col_dogs = "dogs"
if col_conf is None: df["confidence"] = np.nan; col_conf = "confidence"
if col_status is None: df["status"] = "NEW"; col_status = "status"

df[col_dogs] = coerce_int_series(df[col_dogs], default=1)
df[col_conf] = normalize_confidence(df[col_conf])
if col_sev is None:
    dnum = df[col_dogs].astype(int)
    df["severity"] = np.where(dnum >= 4, "CRITICAL", np.where(dnum >= 3, "HIGH", np.where(dnum >= 2, "MEDIUM", "LOW")))
    col_sev = "severity"

df[col_cam] = SINGLE_CAMERA_NAME
df[col_camtype] = SINGLE_CAMERA_NAME
df[col_loc] = SINGLE_LOCATION_NAME
df["date_local"] = df["ts"].dt.date
df["hour"] = df["ts"].dt.hour
df_sorted = df.sort_values("ts", ascending=False).reset_index(drop=True)

def row_uid(r): return f"{str(r[col_id])}__{r['ts'].isoformat()}"
if "selected_alert_uid" not in st.session_state: st.session_state.selected_alert_uid = ""
if st.session_state.selected_alert_uid == "" and len(df_sorted) > 0:
    st.session_state.selected_alert_uid = row_uid(df_sorted.iloc[0])

def get_selected_row():
    uid = st.session_state.selected_alert_uid
    if uid == "": return None
    m = df_sorted.apply(lambda rr: row_uid(rr) == uid, axis=1)
    if m.sum() == 0: return None
    return df_sorted[m].iloc[0]

now = datetime.now(TZ)
today = now.date()
yday = (now - timedelta(days=1)).date()
today_df = df_sorted[df_sorted["date_local"] == today]
yday_df = df_sorted[df_sorted["date_local"] == yday]
new_today = int((today_df[col_status].astype(str).str.upper() == "NEW").sum())
dogs_today = int(today_df[col_dogs].sum())
hp_today = int(today_df[col_sev].astype(str).str.upper().isin(["HIGH", "CRITICAL"]).sum())

# =========================
# HEADER
# =========================
st.markdown(
    f"""
<div class="headerbar">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
    <div>
        <div class="title">🐕 Smart City Stray Dog Control</div>
        <div class="subtitle">Real-Time AI Detection Monitoring Dashboard</div>
    </div>
    <div class="pill pill-red">🔔 <span>{new_today} New Alerts Today</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# ROW 1: KPI CARDS (Shadow Style)
# =========================
# gap="large" helps separation
k1, k2, k3 = st.columns(3, gap="large") 

with k1:
    with st.container(border=True): # This creates the White Shadow Card
        st.markdown(f"""
        <div class="kpi-top"><span style="font-size:24px">⛔</span><small class="badge-med">New</small></div>
        <div class="kpi-val">{new_today}</div>
        <div class="kpi-lab">New Alerts</div>
        """, unsafe_allow_html=True)

with k2:
    with st.container(border=True):
        st.markdown(f"""
        <div class="kpi-top"><span style="font-size:24px">📊</span><small class="badge-low">Total</small></div>
        <div class="kpi-val">{dogs_today}</div>
        <div class="kpi-lab">Total Dogs Detected</div>
        """, unsafe_allow_html=True)

with k3:
    with st.container(border=True):
        st.markdown(f"""
        <div class="kpi-top"><span style="font-size:24px">🚨</span><small class="badge-crit">Priority</small></div>
        <div class="kpi-val">{hp_today}</div>
        <div class="kpi-lab">High Priority</div>
        """, unsafe_allow_html=True)

# =========================
# ROW 2: MAIN FEATURES (Floating Cards)
# =========================
left, mid, right = st.columns([1, 1, 1], gap="large")

# --- CARD 1: CAMERA ---
with left:
    # This outer container is the WHITE CARD with SHADOW
    with st.container(border=True):
        st.subheader("📷 Camera Feed")
        st.caption("Live monitoring view")
        
        # This inner container allows scrolling but has NO visible border
        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No data.")
            else:
                r = df_sorted.iloc[0]
                uid = row_uid(r)
                mins_ago = max(0, int((now - r["ts"]).total_seconds() // 60))
                dogs = int(r[col_dogs])
                
                img_ok = (col_img is not None) and str(r.get(col_img, "")).startswith("http")
                if img_ok:
                    st.markdown(f"""
                    <div class="thumb">
                        <img src="{str(r[col_img])}" />
                        <div class="overlay">
                           <div class="ov-pill">● REC</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;color:#94a3b8">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="thumb-title">{str(r[col_loc])}</div>
                <div class="thumb-sub">{mins_ago}m ago • {dogs} dogs detected</div>
                """, unsafe_allow_html=True)

                if st.button("Select Event", key=f"sel_{uid}"):
                    st.session_state.selected_alert_uid = uid

# --- CARD 2: ALERTS ---
with mid:
    with st.container(border=True):
        st.subheader("⛔ Active Alerts")
        st.caption("Recent detections list")

        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No alerts.")
            else:
                lim = min(len(df_sorted), 100)
                for i in range(lim):
                    r = df_sorted.iloc[i]
                    uid = row_uid(r)
                    sev_class, sev_txt = severity_badge(r[col_sev])
                    ts_txt = r["ts"].strftime("%H:%M")
                    dogs = int(r[col_dogs])
                    ago = time_ago(r["ts"], now)

                    # List Item Styling
                    st.markdown(f"""
                    <div class="list-item">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span style="font-weight:700">{dogs} Dog(s)</span>
                            <span class="{sev_class}">{sev_txt}</span>
                        </div>
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <small style="color:#64748b">📍 {str(r[col_loc])} • {ts_txt}</small>
                            <small class="badge-time">{ago}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"View {str(r[col_id])}", key=f"btn_{uid}"):
                        st.session_state.selected_alert_uid = uid

# --- CARD 3: DETAILS ---
with right:
    with st.container(border=True):
        st.subheader("🖼️ Event Details")
        st.caption("Selected alert analysis")

        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            sel = get_selected_row()
            if sel is None:
                st.info("Select an alert to view details.")
            else:
                sev_class, sev_txt = severity_badge(sel[col_sev])
                ts_txt = sel["ts"].strftime("%d/%m %H:%M")
                
                st.markdown(f"""
                <div style="margin-bottom:12px">
                    <span style="font-size:20px;font-weight:900">{str(sel[col_id])}</span>
                    <span class="{sev_class}" style="vertical-align:middle;margin-left:8px">{sev_txt}</span>
                </div>
                """, unsafe_allow_html=True)

                img_ok = (col_img is not None) and str(sel.get(col_img, "")).startswith("http")
                if img_ok:
                    st.image(str(sel[col_img]), use_container_width=True)
                else:
                    st.markdown("""<div class="thumb" style="height:200px;display:flex;align-items:center;justify-content:center;color:#94a3b8">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown(f"**Location:** {str(sel[col_loc])}")
                st.markdown(f"**Camera:** {str(sel[col_cam])}")
                st.markdown(f"**Time:** {ts_txt}")
                st.markdown(f"**Confidence:** {sel.get(col_conf, 0)}%")
