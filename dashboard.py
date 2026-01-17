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

# Single deployment assumption
SINGLE_CAMERA_NAME = "WEBCAM"
SINGLE_LOCATION_NAME = "WEBCAM"

# ROW 2: HEIGHT CONFIG
SCROLLABLE_AREA_HEIGHT = 420  

st_autorefresh(interval=REFRESH_SEC * 1000, key="auto_refresh")

# =========================
# CSS: STRICT CARD SEPARATION
# =========================
st.markdown(
    f"""
<style>
/* 1. Global Background (Beige) */
html,body,[class*="css"]{{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}}
.stApp{{background:#f7f4ef !important}}
.block-container{{padding-top:1rem;padding-bottom:1.2rem;max-width:1400px}}

/* 2. Text Colors */
.stApp, .stApp *{{color:#0f172a !important}}
[data-testid="stCaptionContainer"] *{{color:#64748b !important}}
.small-muted, small{{color:#64748b !important}}
*{{overflow-wrap:anywhere;word-break:break-word}}

/* 3. CARD STYLE: Targets specific st.container(border=True) */
/* This makes every card White with a THICK DARK GREY BORDER */
[data-testid="stVerticalBlockBorderWrapper"]{{
  background-color: #ffffff !important;
  
  /* THICK DARK BORDER - 100% VISIBLE */
  border: 2px solid #475569 !important; 
  
  border-radius: 16px !important;
  
  /* SHADOW FOR LIFT */
  box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
  
  padding: 16px !important;
  margin-bottom: 0px !important; 
}}

/* 4. PREVENT DOUBLE BORDERS */
/* If a bordered container is INSIDE another, hide its border */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"]{{
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 0 !important;
}}

/* 5. Header Bar */
.headerbar{{
  background:#ffffff;
  border: 2px solid #475569;
  border-radius:16px;
  box-shadow:0 4px 6px rgba(0,0,0,0.05);
  padding:14px 16px;
  margin-bottom:20px;
}}
.title{{font-size:22px;font-weight:900;margin-bottom:2px}}
.subtitle{{font-size:13px;color:#64748b !important;margin-top:-2px}}

/* Chips & Pills */
.pill{{
  display:inline-flex;align-items:center;gap:8px;
  padding:9px 12px;border-radius:14px;
  border:1px solid rgba(30,41,59,.18);
  background:#ffffff;font-weight:900
}}
.pill-red{{background:#fee2e2 !important;border-color:#fecaca !important;color:#991b1b !important}}
.pill-red *{{color:#991b1b !important}}
.row-gap{{height:18px}}

/* KPI Cards */
.kpi-ico{{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:900}}
.kpi-top{{display:flex;align-items:center;justify-content:space-between}}
.kpi-val{{font-size:34px;font-weight:900;margin-top:6px;color:#0f172a !important}}
.kpi-lab{{font-size:13px;color:#0f172a !important;margin-top:-2px;font-weight:800}}
.delta{{font-size:12px;font-weight:900;padding:4px 8px;border-radius:999px;display:inline-block}}
.delta-pos{{background:#fee2e2 !important;color:#991b1b !important}}
.delta-neg{{background:#dcfce7 !important;color:#166534 !important}}

/* Badges */
.badge{{font-size:12px;font-weight:900;padding:6px 10px;border-radius:10px;display:inline-block}}
.badge-low{{background:#dbeafe !important;color:#1d4ed8 !important}}
.badge-med{{background:#fef3c7 !important;color:#92400e !important}}
.badge-high{{background:#ffedd5 !important;color:#9a3412 !important}}
.badge-crit{{background:#ffe4e6 !important;color:#9f1239 !important}}
.badge-time{{background:#f1f5f9 !important;color:#0f172a !important;border:1px solid rgba(30,41,59,.12) !important}}

/* Thumbnails */
.thumb{{border-radius:16px;overflow:hidden;border:1px solid rgba(30,41,59,.16);background:#ffffff;position:relative}}
.thumb img{{display:block;width:100%;height:220px;object-fit:cover}}
.overlay{{position:absolute;left:10px;top:10px;display:flex;gap:8px}}
.ov-pill{{background:#16a34a;color:#ffffff !important;font-weight:900;font-size:12px;padding:6px 10px;border-radius:10px;display:flex;align-items:center;gap:6px}}
.ov-rec{{background:#ef4444}}
.ov-cam{{background:rgba(15,23,42,.80);color:#ffffff !important;font-weight:900;font-size:12px;padding:6px 10px;border-radius:10px}}
.ov-det{{position:absolute;left:10px;bottom:10px;background:#f59e0b;color:#0f172a !important;font-weight:900;font-size:12px;padding:6px 10px;border-radius:10px;display:flex;align-items:center;gap:6px}}
.thumb-title{{font-weight:900;margin-top:10px}}
.thumb-sub{{margin-top:-2px;color:#64748b !important}}

/* Buttons */
.stButton > button{{
  width:100%;
  background:#ffffff !important;
  color:#0f172a !important;
  border:1px solid rgba(30,41,59,.18) !important;
  border-radius:12px !important;
  font-weight:900 !important;
  box-shadow:none !important;
}}
.stButton > button:hover{{
  background:#f8fafc !important;
  border-color:rgba(30,41,59,.30) !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HELPERS
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
    x = pd.to_numeric(s, errors="coerce").fillna(default)
    return x.clip(lower=0).astype(int)

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

def delta_chip(pct):
    if pct is None or np.isnan(pct): return '<span class="delta delta-pos">+0%</span>'
    if pct >= 0: return f'<span class="delta delta-pos">+{pct:.0f}%</span>'
    return f'<span class="delta delta-neg">{pct:.0f}%</span>'

def pct_change(today_val, yday_val):
    if yday_val == 0: return 0.0 if today_val == 0 else 100.0
    return ((today_val - yday_val) / yday_val) * 100.0

def compute_peak_2hr(hourly_dogs_dict):
    arr = np.zeros(24)
    for h in range(24): arr[h] = hourly_dogs_dict.get(h, 0)
    best_h, best_sum = 0, -1
    for h in range(24):
        s = arr[h] + arr[(h + 1) % 24]
        if s > best_sum: best_sum, best_h = s, h
    return f"{best_h:02d}:00 - {(best_h+2)%24:02d}:00"

def time_ago(ts: datetime, now_: datetime) -> str:
    secs = int(max(0, (now_ - ts).total_seconds()))
    if secs < 60: return "just now"
    mins = secs // 60
    if mins < 60: return f"{mins} min ago" if mins == 1 else f"{mins} mins ago"
    hrs = mins // 60
    if hrs < 24: return f"{hrs} hour ago" if hrs == 1 else f"{hrs} hours ago"
    days = hrs // 24
    return f"{days} day ago" if days == 1 else f"{days} days ago"

@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data(url):
    df = pd.read_csv(url, dtype=str, engine="python", on_bad_lines="skip")
    return _clean_cols(df)

# =========================
# DATA LOADING
# =========================
raw = load_data(SHEET_CSV_URL)
if raw.empty:
    st.error("No data loaded from Google Sheets CSV.")
    st.stop()

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

if col_ts is None:
    st.error("Sheet must have a timestamp column.")
    st.stop()

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

# State
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

# Metrics
now = datetime.now(TZ)
today = now.date()
yday = (now - timedelta(days=1)).date()
today_df = df_sorted[df_sorted["date_local"] == today]
yday_df = df_sorted[df_sorted["date_local"] == yday]
new_today = int((today_df[col_status].astype(str).str.upper() == "NEW").sum())
new_yday = int((yday_df[col_status].astype(str).str.upper() == "NEW").sum())
dogs_today = int(today_df[col_dogs].sum())
dogs_yday = int(yday_df[col_dogs].sum())
hp_today = int(today_df[col_sev].astype(str).str.upper().isin(["HIGH", "CRITICAL"]).sum())
hp_yday = int(yday_df[col_sev].astype(str).str.upper().isin(["HIGH", "CRITICAL"]).sum())

# =========================
# HEADER
# =========================
st.markdown(
    f"""
<div class="headerbar">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
    <div style="display:flex;align-items:center;gap:12px;min-width:260px">
      <div class="kpi-ico" style="background:#dbeafe;color:#1d4ed8">🐕</div>
      <div>
        <div class="title">Smart City Stray Dog Control System</div>
        <div class="subtitle">Real-Time AI Detection Monitoring</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <div class="pill pill-red">🔔 <span>{new_today} New Alerts</span></div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# ROW 1: THE 3 KPI CARDS (SEPARATED)
# =========================
k1, k2, k3 = st.columns(3, gap="medium")

# Card 1
with k1:
    with st.container(border=True):
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#fee2e2;color:#b91c1c">⛔</div>{delta_chip(pct_change(new_today, new_yday))}</div><div class="kpi-val">{new_today}</div><div class="kpi-lab">New Alerts</div>""",
            unsafe_allow_html=True,
        )

# Card 2
with k2:
    with st.container(border=True):
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#e0f2fe;color:#075985">📊</div>{delta_chip(pct_change(dogs_today, dogs_yday))}</div><div class="kpi-val">{dogs_today}</div><div class="kpi-lab">Total Stray Dogs Detected</div>""",
            unsafe_allow_html=True,
        )

# Card 3
with k3:
    with st.container(border=True):
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#ffedd5;color:#9a3412">🚨</div>{delta_chip(pct_change(hp_today, hp_yday))}</div><div class="kpi-val">{hp_today}</div><div class="kpi-lab">High Priority</div>""",
            unsafe_allow_html=True,
        )

st.markdown('<div class="row-gap"></div>', unsafe_allow_html=True)

# =========================
# ROW 2: THE 3 FEATURE CARDS (SEPARATED)
# =========================
left, mid, right = st.columns([1.05, 0.95, 1.05], gap="medium")

# --- CARD 4: CAMERA FEED ---
with left:
    with st.container(border=True):
        st.subheader("📷 Camera Feeds & Snapshots")
        st.caption("Latest detection (single feed)")
        
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No detection records.")
            else:
                r = df_sorted.iloc[0]
                uid = row_uid(r)
                ts_txt = r["ts"].strftime("%d/%m/%Y %H:%M")
                mins_ago = max(0, int((now - r["ts"]).total_seconds() // 60))
                dogs = int(r[col_dogs])
                dog_word = "stray dog" if dogs == 1 else "stray dogs"
                cam = str(r[col_cam])
                loc = str(r[col_loc])

                img_ok = (col_img is not None) and str(r.get(col_img, "")).startswith("http")
                if img_ok:
                    st.markdown(
                        f"""
                        <div class="thumb">
                          <img src="{str(r[col_img])}" />
                          <div class="overlay">
                            <div class="ov-pill">● ONLINE</div>
                            <div class="ov-pill ov-rec">● REC</div>
                            <div class="ov-cam">{cam}</div>
                          </div>
                          <div class="ov-det">📸 Detection {mins_ago}m ago • {dogs} {dog_word}</div>
                        </div>
                        <div class="thumb-title">{loc}</div>
                        <div class="thumb-sub">{cam} • {ts_txt}</div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;font-weight:900;color:#64748b">No Snapshot URL</div>""",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{loc}**")
                    st.caption(f"{cam} • {ts_txt}")

                if st.button("Select this detection", key=f"single_select__{uid}", use_container_width=True):
                    st.session_state.selected_alert_uid = uid

# --- CARD 5: ACTIVE ALERTS ---
with mid:
    with st.container(border=True):
        st.subheader("⛔ Active Alerts")
        st.caption("Scroll to view older detections")

        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No alerts.")
            else:
                lim = min(len(df_sorted), 150)
                for i in range(lim):
                    r = df_sorted.iloc[i]
                    uid = row_uid(r)
                    sev_class, sev_txt = severity_badge(r[col_sev])
                    conf = r[col_conf]
                    conf_txt = f"{conf:.0f}%" if pd.notna(conf) else "—"
                    ts_txt = r["ts"].strftime("%d/%m/%Y %H:%M")
                    dogs = int(r[col_dogs])
                    dog_word = "Stray Dog" if dogs == 1 else "Stray Dogs"
                    ago_txt = time_ago(r["ts"], now)

                    st.markdown(
                        f"""
                        <div style="padding:12px;border-radius:16px;border:1px solid rgba(30,41,59,.16);background:#ffffff;margin-bottom:10px">
                          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
                            <div style="min-width:0">
                              <div style="font-weight:900">
                                {dogs} {dog_word} Detected
                                <span class="{sev_class}" style="margin-left:8px">{sev_txt}</span>
                              </div>
                              <div class="small-muted">{str(r[col_camtype])} • {str(r[col_cam])}</div>
                              <div class="small-muted">📍 {str(r[col_loc])}</div>
                              <div class="small-muted">🕒 {ts_txt} • 🎯 {conf_txt}</div>
                            </div>
                            <div style="text-align:right;flex-shrink:0">
                              <span class="badge badge-time" style="display:block;white-space:nowrap">{ago_txt}</span>
                            </div>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(f"View • {str(r[col_id])}", key=f"view__{uid}", use_container_width=True):
                        st.session_state.selected_alert_uid = uid

# --- CARD 6: ACTIVE ALERT PICTURE ---
with right:
    with st.container(border=True):
        st.subheader("🖼️ Active Alert Picture")
        
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            sel = get_selected_row()
            if sel is None:
                st.info("Please select an alert to view the snapshot.")
            else:
                sev_class, sev_txt = severity_badge(sel[col_sev])
                ts_txt = sel["ts"].strftime("%d/%m/%Y %H:%M")
                conf = sel[col_conf]
                conf_txt = f"{conf:.0f}%" if pd.notna(conf) else "—"

                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px">
                      <div style="font-weight:900">{str(sel[col_id])}</div>
                      <span class="{sev_class}">{sev_txt}</span>
                      <span class="small-muted">📍 {str(sel[col_loc])} • 🕒 {ts_txt}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                img_ok = (col_img is not None) and str(sel.get(col_img, "")).startswith("http")
                if img_ok:
                    st.image(str(sel[col_img]), use_container_width=True)
                else:
                    st.markdown(
                        """<div style="height:260px;border-radius:16px;border:1px dashed rgba(30,41,59,.25);background:#ffffff;display:flex;align-items:center;justify-content:center;font-weight:900;color:#64748b">No Snapshot URL in Sheet</div>""",
                        unsafe_allow_html=True,
                    )

                st.markdown(f"- **Camera:** {str(sel[col_cam])} ({str(sel[col_camtype])})")
                st.markdown(f"- **Location:** {str(sel[col_loc])}")
                st.markdown(f"- **Stray Dogs:** {int(sel[col_dogs])}")
                st.markdown(f"- **Confidence:** {conf_txt}")

st.markdown('<div class="row-gap"></div>', unsafe_allow_html=True)

# =========================
# ROW 4: Recent Events
# =========================
with st.container(border=True):
    st.subheader("🧾 Recent Detection Events")
    st.caption("Last 50 records (scrollable)")
    recent = df_sorted.head(50).copy()
    show = recent[[col_id, col_dogs, col_conf, col_sev, col_status]].copy()
    show.insert(0, "Timestamp", recent["ts"].dt.strftime("%b %d, %I:%M %p"))
    show.columns = ["Timestamp", "Detection ID", "Stray Dogs", "Confidence", "Severity", "Status"]
    show["Confidence"] = np.where(
        pd.notna(recent[col_conf]),
        recent[col_conf].round(0).astype(int).astype(str) + "%",
        "—"
    )
    st.dataframe(show, use_container_width=True, height=380)
