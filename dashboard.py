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
st.set_page_config(page_title="Smart City Stray Dog Control", layout="wide")
TZ = ZoneInfo("Asia/Kuala_Lumpur")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_SEC = 8

# Constants
SINGLE_CAMERA_NAME = "WEBCAM"
SINGLE_LOCATION_NAME = "WEBCAM"
SCROLLABLE_AREA_HEIGHT = 420  

st_autorefresh(interval=REFRESH_SEC * 1000, key="auto_refresh")

# =========================
# CSS: BOX SHADOWS (UNDER CARDS)
# =========================
st.markdown(
    f"""
<style>
/* 1. Global Background */
html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}
.stApp {{
    background-color: #f7f4ef !important;
}}
.block-container {{
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}}

/* 2. CARD STYLE: WHITE BOX + STRONG SHADOW */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: #ffffff !important;
    border: none !important; 
    border-radius: 12px !important;
    
    /* SHADOW UNDER THE BOX (Card) */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
    
    padding: 20px !important;
    margin-bottom: 0px !important; 
}}

/* 3. CLEAN UP INNER CONTENT */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {{
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
}}

/* 4. Text & Headers */
.stApp, .stApp * {{ color: #0f172a !important; }}
.small-muted {{ color: #64748b !important; }}

/* 5. Header Title Area: WHITE BOX + SHADOW */
.header-area {{
    margin-bottom: 30px;
    padding: 20px;
    background-color: #ffffff;
    border-left: 6px solid #2563eb;
    border-radius: 12px;
    
    /* SHADOW UNDER THE HEADER BOX */
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}}
.main-title {{ font-size: 32px; font-weight: 900; }}

/* 6. Buttons */
.stButton > button {{
    width: 100%;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #0f172a !important;
    font-weight: 700;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}}
.stButton > button:hover {{
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
}}

/* 7. Thumbnails */
.thumb {{
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}
.thumb img {{ width: 100%; height: 220px; object-fit: cover; }}

/* 8. Badges */
.sev-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; }}

/* 9. Light Mode Table */
table.custom-table {{ width: 100%; border-collapse: collapse; color: #0f172a; font-size: 14px; }}
table.custom-table th {{ background-color: #f1f5f9; color: #0f172a; font-weight: 800; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; }}
table.custom-table td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
table.custom-table tr:hover {{ background-color: #f8fafc; }}
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
    if sev == "LOW": return "sev-badge", "LOW", "#dbeafe", "#1d4ed8"
    if sev == "MEDIUM": return "sev-badge", "MEDIUM", "#fef3c7", "#92400e"
    if sev == "HIGH": return "sev-badge", "HIGH", "#ffedd5", "#9a3412"
    if sev == "CRITICAL": return "sev-badge", "CRITICAL", "#ffe4e6", "#9f1239"
    return "sev-badge", (sev if sev else "MEDIUM"), "#fef3c7", "#92400e"

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
    if mins < 60: return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 24: return f"{hrs}h ago"
    days = hrs // 24
    return f"{days}d ago"

def delta_chip(pct):
    if pct is None or np.isnan(pct): return '<span style="color:#16a34a; font-weight:bold; font-size:12px">+0%</span>'
    if pct >= 0: return f'<span style="color:#b91c1c; font-weight:bold; font-size:12px">+{pct:.0f}%</span>'
    return f'<span style="color:#16a34a; font-weight:bold; font-size:12px">{pct:.0f}%</span>'

@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data(url):
    df = pd.read_csv(url, dtype=str, engine="python", on_bad_lines="skip")
    return _clean_cols(df)

# =========================
# DATA LOADING
# =========================
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
new_yday = int((yday_df[col_status].astype(str).str.upper() == "NEW").sum())
dogs_today = int(today_df[col_dogs].sum())
dogs_yday = int(yday_df[col_dogs].sum())
hp_today = int(today_df[col_sev].astype(str).str.upper().isin(["HIGH", "CRITICAL"]).sum())
hp_yday = int(yday_df[col_sev].astype(str).str.upper().isin(["HIGH", "CRITICAL"]).sum())

# =========================
# HEADER (SHADOW BOX)
# =========================
st.markdown(
    f"""
    <div class="header-area">
        <div class="main-title">🐕 Smart City Stray Dog Control</div>
        <div style="font-size:16px; color:#475569;">Real-Time AI Detection Monitoring</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# ROW 1: 3 KPI CARDS (SHADOW BOXES)
# =========================
k1, k2, k3 = st.columns(3, gap="large")

# CARD 1
with k1:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:28px;">⛔</div>
            {delta_chip(pct_change(new_today, new_yday))}
        </div>
        <div style="font-size:42px; font-weight:900; margin-top:5px;">{new_today}</div>
        <div style="font-weight:bold; color:#64748b; font-size:14px;">NEW ALERTS</div>
        """, unsafe_allow_html=True)

# CARD 2
with k2:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:28px;">📊</div>
            {delta_chip(pct_change(dogs_today, dogs_yday))}
        </div>
        <div style="font-size:42px; font-weight:900; margin-top:5px;">{dogs_today}</div>
        <div style="font-weight:bold; color:#64748b; font-size:14px;">TOTAL STRAY DOGS DETECTED</div>
        """, unsafe_allow_html=True)

# CARD 3
with k3:
    with st.container(border=True):
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:28px;">🚨</div>
            {delta_chip(pct_change(hp_today, hp_yday))}
        </div>
        <div style="font-size:42px; font-weight:900; margin-top:5px;">{hp_today}</div>
        <div style="font-weight:bold; color:#64748b; font-size:14px;">HIGH PRIORITY</div>
        """, unsafe_allow_html=True)

st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

# =========================
# ROW 2: 3 FEATURE CARDS (SHADOW BOXES)
# =========================
left, mid, right = st.columns(3, gap="large")

# --- CARD 4 ---
with left:
    with st.container(border=True):
        st.subheader("📷 Camera Feeds & Snapshots")
        st.caption("Latest detection (single feed)")
        
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
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
                        <img src="{str(r[col_img])}" />
                        <div style="position:absolute; top:10px; left:10px;">
                           <span style="background:#22c55e; color:white; padding:4px 8px; border-radius:6px; font-size:11px; font-weight:bold;">LIVE</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;background:#f1f5f9;color:#64748b;font-weight:bold;">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown(f"<div style='margin-top:10px; font-weight:bold;'>{str(r[col_loc])}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='small-muted'>{mins_ago}m ago • {int(r[col_dogs])} dogs</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                
                if st.button("Select This Event", key=f"sel_{uid}"):
                    st.session_state.selected_alert_uid = uid

# --- CARD 5 ---
with mid:
    with st.container(border=True):
        st.subheader("⛔ Active Alerts")
        st.caption("Scroll for more")

        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No alerts.")
            else:
                lim = min(len(df_sorted), 100)
                for i in range(lim):
                    r = df_sorted.iloc[i]
                    uid = row_uid(r)
                    cls, sev_txt, bg, col = severity_badge(r[col_sev])
                    
                    st.markdown(f"""
                    <div style="padding:12px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="font-weight:bold; font-size:15px;">{int(r[col_dogs])} Dog(s)</span>
                            <span style="background:{bg}; color:{col}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{sev_txt}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="small-muted" style="font-size:12px;">{str(r[col_loc])}</span>
                            <span class="small-muted" style="font-size:11px;">{time_ago(r["ts"], now)}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"View {str(r[col_id])}", key=f"btn_{uid}"):
                        st.session_state.selected_alert_uid = uid

# --- CARD 6 ---
with right:
    with st.container(border=True):
        st.subheader("🖼️ Active Alert Picture")
        st.caption("Details")

        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            sel = get_selected_row()
            if sel is None:
                st.info("Select an alert.")
            else:
                cls, sev_txt, bg, col = severity_badge(sel[col_sev])
                ts_txt = sel["ts"].strftime("%d/%m/%Y %H:%M")
                conf = sel[col_conf]
                conf_txt = f"{conf:.0f}%" if pd.notna(conf) else "—"

                st.markdown(f"""
                <div style="margin-bottom:10px; display:flex; align-items:center; gap:10px;">
                    <span style="font-size:18px; font-weight:900;">{str(sel[col_id])}</span>
                    <span style="background:{bg}; color:{col}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{sev_txt}</span>
                </div>
                """, unsafe_allow_html=True)

                img_ok = (col_img is not None) and str(sel.get(col_img, "")).startswith("http")
                if img_ok:
                    st.image(str(sel[col_img]), use_container_width=True)
                else:
                    st.markdown("""<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;background:#f1f5f9;color:#64748b;font-weight:bold;">No Image</div>""", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown(f"**Loc:** {str(sel[col_loc])}")
                st.markdown(f"**Cam:** {str(sel[col_cam])}")
                st.markdown(f"**Time:** {ts_txt}")
                st.markdown(f"**Conf:** {conf_txt}")

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# =========================
# ROW 3: TRENDS & ANALYTICS
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
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["detections"], mode="lines+markers", name="Detections"))
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["dogs"], mode="lines+markers", name="Dogs"))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#000000'), xaxis=dict(showgrid=True, gridcolor='#e2e8f0', color='#000000'), yaxis=dict(showgrid=True, gridcolor='#e2e8f0', color='#000000'), legend=dict(font=dict(color='#000000')))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    elif mode == "7 Days":
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        d["day"] = d["ts"].dt.date
        daily = d.groupby("day").agg(detections=(col_id, "count"), dogs=(col_dogs, "sum")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["detections"], name="Detections"))
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["dogs"], name="Dogs"))
        fig.update_layout(template="plotly_white", barmode="group", margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#000000'), xaxis=dict(showgrid=True, gridcolor='#e2e8f0', color='#000000'), yaxis=dict(showgrid=True, gridcolor='#e2e8f0', color='#000000'), legend=dict(font=dict(color='#000000')))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    else:
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        sev = d[col_sev].astype(str).str.upper().replace({"": "MEDIUM"}).fillna("MEDIUM")
        counts = sev.value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).fillna(0).astype(int)
        fig = go.Figure(data=[go.Pie(labels=list(counts.index), values=list(counts.values), hole=0.6)])
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), height=300, paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#000000'), legend=dict(font=dict(color='#000000')))
        st.plotly_chart(fig, use_container_width=True, theme=None)

st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

# =========================
# ROW 4: RECENT EVENTS
# =========================
with st.container(border=True):
    st.subheader("🧾 Recent Detection Events")
    st.caption("Last 50 records (scrollable)")
    recent = df_sorted.head(50).copy()
    show = recent[[col_id, col_dogs, col_conf, col_sev, col_status]].copy()
    show.insert(0, "Timestamp", recent["ts"].dt.strftime("%b %d, %I:%M %p"))
    show.columns = ["Timestamp", "Detection ID", "Stray Dogs", "Confidence", "Severity", "Status"]
    show["Confidence"] = np.where(pd.notna(recent[col_conf]), recent[col_conf].round(0).astype(int).astype(str) + "%", "—")
    def highlight_sev(val):
        return 'color: black'
    styled_df = show.style.set_properties(**{'background-color': '#ffffff', 'color': '#000000', 'border-color': '#e2e8f0'}).map(highlight_sev, subset=['Severity'])
    st.dataframe(styled_df, use_container_width=True, height=380, column_config={"Timestamp": st.column_config.TextColumn("Timestamp", width="medium"), "Detection ID": st.column_config.TextColumn("ID", width="small")})
