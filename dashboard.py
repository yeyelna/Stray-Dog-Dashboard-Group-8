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
# CSS: BORDER JELAS & TEKS GELAP (FIX)
# =========================
st.markdown(
    f"""
<style>
/* 1. Paksa Background App jadi Kelabu Cair (supaya kad putih nampak jelas) */
.stApp {{
    background-color: #f1f5f9 !important;
}}

/* 2. TEKS HITAM/GELAP (Wajib) */
/* Paksa semua teks dalam app jadi warna gelap */
.stApp, .stApp p, .stApp div, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp label, .stApp small {{
    color: #0f172a !important; /* Warna biru gelap hampir hitam */
}}
/* Teks secondary (caption) warna kelabu sikit tapi masih gelap */
[data-testid="stCaptionContainer"] *, .small-muted {{
    color: #475569 !important;
}}

/* 3. BORDER UNTUK KAD (Outer Container) */
/* Ini setting untuk st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: #ffffff !important;   /* Kad Warna Putih */
    border: 2px solid #94a3b8 !important;   /* BORDER TEBAL WARNA KELABU (VISIBLE) */
    border-radius: 12px !important;         /* Bucu bulat sikit */
    box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; /* Shadow sikit */
    padding: 20px !important;
    margin-bottom: 20px !important;
}}

/* 4. BUANG BORDER DALAM (Supaya tak jadi kotak dalam kotak) */
/* Jika ada container border di dalam container border lain, buang border dia */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* 5. Header Bar Style */
.headerbar {{
    background: #ffffff;
    border: 2px solid #94a3b8;
    border-radius: 12px;
    padding: 15px 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}}
.big-title {{
    font-size: 32px !important;
    font-weight: 900 !important;
    color: #0f172a !important;
}}
.subtitle {{
    font-size: 16px !important;
    color: #475569 !important;
}}

/* 6. Button 'Bright' */
.stButton > button {{
    background-color: #2563eb !important; /* Biru terang */
    color: #ffffff !important;            /* Teks putih */
    border: 1px solid #1d4ed8 !important;
    font-weight: 700 !important;
}}
.stButton > button:hover {{
    background-color: #1d4ed8 !important;
}}

/* Badge Styles */
.sev-badge {{ padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 800; border: 1px solid rgba(0,0,0,0.1); }}
.sev-low {{ background: #dbeafe; color: #1e40af !important; }}
.sev-med {{ background: #fef3c7; color: #92400e !important; }}
.sev-high {{ background: #ffedd5; color: #9a3412 !important; }}
.sev-crit {{ background: #ffe4e6; color: #9f1239 !important; }}

/* Thumbnails */
.thumb {{ 
    border: 1px solid #cbd5e1; 
    border-radius: 10px; 
    overflow: hidden;
    background: #f8fafc;
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
    return pd.to_numeric(s, errors="coerce").fillna(default).clip(lower=0).astype(int)

def normalize_confidence(series):
    x = pd.to_numeric(series, errors="coerce")
    if x.notna().sum() == 0: return x
    med = np.nanmedian(x.values.astype(float))
    if med <= 1.0: x = x * 100.0
    return x.clip(0, 100)

def severity_badge(sev):
    sev = str(sev).strip().upper()
    if sev == "LOW": return "sev-badge sev-low", "LOW"
    if sev == "MEDIUM": return "sev-badge sev-med", "MEDIUM"
    if sev == "HIGH": return "sev-badge sev-high", "HIGH"
    if sev == "CRITICAL": return "sev-badge sev-crit", "CRITICAL"
    return "sev-badge sev-med", (sev if sev else "MEDIUM")

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

def compute_peak_2hr(hourly_dogs_dict):
    arr = np.zeros(24)
    for h in range(24): arr[h] = hourly_dogs_dict.get(h, 0)
    best_h, best_sum = 0, -1
    for h in range(24):
        s = arr[h] + arr[(h + 1) % 24]
        if s > best_sum: best_sum, best_h = s, h
    return f"{best_h:02d}:00 - {(best_h+2)%24:02d}:00"

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
        <div class="big-title">🐕 Smart City Stray Dog Control</div>
        <div class="subtitle">Real-Time AI Detection & Monitoring Dashboard</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# ROW 1: KPI (ADA BORDER)
# =========================
k1, k2, k3 = st.columns(3, gap="large") 

with k1:
    with st.container(border=True): # Outer border
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:30px">⛔</span>
            <span class="sev-badge sev-low">ALERTS</span>
        </div>
        <div style="font-size:38px; font-weight:900; margin-top:5px;">{new_today}</div>
        <div style="font-weight:700; color:#475569;">NEW ALERTS TODAY</div>
        """, unsafe_allow_html=True)

with k2:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:30px">📊</span>
            <span class="sev-badge sev-med">COUNT</span>
        </div>
        <div style="font-size:38px; font-weight:900; margin-top:5px;">{dogs_today}</div>
        <div style="font-weight:700; color:#475569;">TOTAL DOGS DETECTED</div>
        """, unsafe_allow_html=True)

with k3:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:30px">🚨</span>
            <span class="sev-badge sev-crit">RISK</span>
        </div>
        <div style="font-size:38px; font-weight:900; margin-top:5px;">{hp_today}</div>
        <div style="font-weight:700; color:#475569;">HIGH PRIORITY</div>
        """, unsafe_allow_html=True)

# =========================
# ROW 2: MAIN FEATURES (ADA BORDER)
# =========================
left, mid, right = st.columns([1, 1, 1], gap="large")

# --- CARD 1: CAMERA ---
with left:
    with st.container(border=True): # Border Luar Jelas
        st.subheader("📷 Camera Feed")
        st.caption("Live monitoring view")
        
        # Scroll dalam tanpa border
        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No data.")
            else:
                r = df_sorted.iloc[0]
                uid = row_uid(r)
                mins_ago = max(0, int((now - r["ts"]).total_seconds() // 60))
                
                img_ok = (col_img is not None) and str(r.get(col_img, "")).startswith("http")
                if img_ok:
                    st.markdown(f"""
                    <div class="thumb">
                        <img src="{str(r[col_img])}" style="width:100%; height:220px; object-fit:cover; display:block;" />
                        <div style="position:absolute; top:10px; left:10px;">
                           <span style="background:#22c55e; color:white !important; padding:4px 8px; border-radius:6px; font-size:11px; font-weight:800;">LIVE</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;color:#94a3b8; background:#f1f5f9;">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown(f"<div style='margin-top:12px; font-weight:700; font-size:16px;'>{str(r[col_loc])}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#475569; font-size:13px;'>{mins_ago}m ago • {int(r[col_dogs])} dogs</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                
                if st.button("Analyze This Detection", key=f"sel_{uid}"):
                    st.session_state.selected_alert_uid = uid

# --- CARD 2: ALERTS LIST ---
with mid:
    with st.container(border=True): # Border Luar Jelas
        st.subheader("⛔ Active Alerts")
        st.caption("Real-time detections list")

        # Scroll dalam tanpa border
        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No alerts.")
            else:
                lim = min(len(df_sorted), 100)
                for i in range(lim):
                    r = df_sorted.iloc[i]
                    uid = row_uid(r)
                    sev_class, sev_txt = severity_badge(r[col_sev])
                    
                    st.markdown(f"""
                    <div style="padding:12px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="font-weight:800; font-size:15px; color:#0f172a;">{int(r[col_dogs])} Dog(s) Detected</span>
                            <span class="{sev_class}">{sev_txt}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:#475569; font-size:13px;">{str(r[col_loc])}</span>
                            <span style="font-size:11px; color:#475569; font-weight:600;">{time_ago(r["ts"], now)}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"View Details ({str(r[col_id])})", key=f"btn_{uid}"):
                        st.session_state.selected_alert_uid = uid

# --- CARD 3: DETAILS ---
with right:
    with st.container(border=True): # Border Luar Jelas
        st.subheader("🖼️ Event Details")
        st.caption("Selected alert analysis")

        # Scroll dalam tanpa border
        with st.container(height=SCROLL_AREA_HEIGHT, border=False):
            sel = get_selected_row()
            if sel is None:
                st.info("Select an alert to view details.")
            else:
                sev_class, sev_txt = severity_badge(sel[col_sev])
                
                st.markdown(f"""
                <div style="margin-bottom:15px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px; font-weight:900; color:#0f172a;">{str(sel[col_id])}</span>
                    <span class="{sev_class}">{sev_txt}</span>
                </div>
                """, unsafe_allow_html=True)

                img_ok = (col_img is not None) and str(sel.get(col_img, "")).startswith("http")
                if img_ok:
                    st.image(str(sel[col_img]), use_container_width=True)
                else:
                    st.markdown("""<div class="thumb" style="height:200px;display:flex;align-items:center;justify-content:center;color:#94a3b8; background:#f1f5f9;">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown(f"**📍 Location:** {str(sel[col_loc])}")
                st.markdown(f"**📷 Camera:** {str(sel[col_cam])}")
                st.markdown(f"**🕒 Time:** {sel['ts'].strftime('%d/%m %H:%M')}")
                st.markdown(f"**🎯 Confidence:** {sel.get(col_conf, 0)}%")

# =========================
# ROW 3: TRENDS (ADA BORDER)
# =========================
with st.container(border=True):
    st.subheader("📈 Detection Trends & Analytics")
    mode = st.radio("Analytics View", ["24 Hours", "7 Days", "Severity Distribution"], horizontal=True)

    if mode == "24 Hours":
        start = now - timedelta(hours=24)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        hourly = d.groupby("hour").agg(detections=(col_id, "count"), dogs=(col_dogs, "sum")).reset_index()
        hours = list(range(24))
        hourly = hourly.set_index("hour").reindex(hours, fill_value=0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["detections"], mode="lines+markers", name="Detections", line=dict(color='#2563eb', width=3)))
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["dogs"], mode="lines+markers", name="Dogs", line=dict(color='#f59e0b', width=3)))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#0f172a'))
        st.plotly_chart(fig, use_container_width=True)

    elif mode == "7 Days":
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        d["day"] = d["ts"].dt.date
        daily = d.groupby("day").agg(detections=(col_id, "count"), dogs=(col_dogs, "sum")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["detections"], name="Detections", marker_color='#2563eb'))
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["dogs"], name="Dogs", marker_color='#f59e0b'))
        fig.update_layout(barmode="group", margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#0f172a'))
        st.plotly_chart(fig, use_container_width=True)

    else:
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        sev = d[col_sev].astype(str).str.upper().replace({"": "MEDIUM"}).fillna("MEDIUM")
        counts = sev.value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).fillna(0).astype(int)
        fig = go.Figure(data=[go.Pie(labels=list(counts.index), values=list(counts.values), hole=0.6, marker=dict(colors=['#991b1b', '#9a3412', '#92400e', '#1d4ed8']))])
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#0f172a'))
        st.plotly_chart(fig, use_container_width=True)

# =========================
# ROW 4: RECENT (ADA BORDER)
# =========================
with st.container(border=True):
    st.subheader("🧾 Recent Detection Events")
    recent = df_sorted.head(50).copy()
    show = recent[[col_id, col_dogs, col_conf, col_sev, col_status]].copy()
    show.insert(0, "Timestamp", recent["ts"].dt.strftime("%b %d, %H:%M"))
    show.columns = ["Time", "ID", "Dogs", "Conf", "Severity", "Status"]
    st.dataframe(show, use_container_width=True, height=300)
