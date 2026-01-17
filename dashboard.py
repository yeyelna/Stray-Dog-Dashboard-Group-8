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
SCROLLABLE_AREA_HEIGHT = 420  

st_autorefresh(interval=REFRESH_SEC * 1000, key="auto_refresh")

# =========================
# CSS: FLOATING CARDS WITH SHADOWS (ALL SIDES)
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

/* 3. THE FLOATING CARD STYLE */
/* Targets every st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"]{{
  background-color: #ffffff !important; /* White Card */
  border: 1px solid #e2e8f0 !important; /* Very thin border */
  border-radius: 15px !important;
  
  /* SHADOW ON ALL SIDES (Atas, Bawah, Kiri, Kanan) */
  box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1) !important; 
  
  padding: 20px !important;
  margin-bottom: 20px !important;
}}

/* 4. PREVENT DOUBLE SHADOWS */
/* If a card is inside another (like the scroll area), remove its shadow/border */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"]{{
  box-shadow: none !important;
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
}}

/* 5. Header Bar */
.headerbar{{
  background:#ffffff;
  border-radius:15px;
  /* Shadow all sides */
  box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1); 
  padding:14px 20px;
  margin-bottom:20px;
  border: 1px solid #e2e8f0;
}}
.title{{font-size:24px;font-weight:900;margin-bottom:2px}}
.subtitle{{font-size:14px;color:#64748b !important;margin-top:-2px}}

/* 6. Buttons */
.stButton > button{{
  width:100%;
  background:#ffffff !important;
  color:#0f172a !important;
  border:1px solid #cbd5e1 !important;
  border-radius:10px !important;
  font-weight:700 !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
}}
.stButton > button:hover{{
  background:#f8fafc !important;
  border-color:#64748b !important;
}}

/* Badges/Pills */
.pill{{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:12px;border:1px solid #cbd5e1;background:#ffffff;font-weight:800}}
.pill-red{{background:#fee2e2 !important;border-color:#fecaca !important;color:#991b1b !important}}
.kpi-ico{{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:18px}}
.kpi-top{{display:flex;align-items:center;justify-content:space-between}}
.kpi-val{{font-size:38px;font-weight:900;margin-top:5px;color:#0f172a !important}}
.kpi-lab{{font-size:13px;color:#64748b !important;margin-top:-2px;font-weight:700;text-transform:uppercase}}
.delta{{font-size:12px;font-weight:800;padding:4px 8px;border-radius:99px;display:inline-block}}
.delta-pos{{background:#fee2e2 !important;color:#991b1b !important}}
.delta-neg{{background:#dcfce7 !important;color:#166534 !important}}

/* Thumbnails */
.thumb{{
  border-radius:12px;
  overflow:hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  background:#f8fafc;
  position:relative;
  margin-bottom:12px;
}}
.thumb img{{display:block;width:100%;height:220px;object-fit:cover}}
.overlay{{position:absolute;left:10px;top:10px;display:flex;gap:8px}}
.ov-pill{{background:#16a34a;color:#ffffff !important;font-weight:900;font-size:11px;padding:4px 10px;border-radius:8px}}
.ov-rec{{background:#ef4444}}
.ov-cam{{background:rgba(15,23,42,.80);color:#ffffff !important;font-weight:900;font-size:11px;padding:4px 10px;border-radius:8px}}
.ov-det{{position:absolute;left:10px;bottom:10px;background:#f59e0b;color:#0f172a !important;font-weight:900;font-size:11px;padding:4px 10px;border-radius:8px}}
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
    if sev == "LOW": return "background:#dbeafe;color:#1d4ed8", "LOW"
    if sev == "MEDIUM": return "background:#fef3c7;color:#92400e", "MEDIUM"
    if sev == "HIGH": return "background:#ffedd5;color:#9a3412", "HIGH"
    if sev == "CRITICAL": return "background:#ffe4e6;color:#9f1239", "CRITICAL"
    return "background:#fef3c7;color:#92400e", (sev if sev else "MEDIUM")

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
# ROW 1: KPI CARDS (FLOATING WITH SHADOW)
# =========================
k1, k2, k3 = st.columns(3, gap="medium")

with k1:
    with st.container(border=True): # This creates the Floating Card
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#fee2e2;color:#b91c1c">⛔</div>{delta_chip(pct_change(new_today, new_yday))}</div><div class="kpi-val">{new_today}</div><div class="kpi-lab">New Alerts</div>""",
            unsafe_allow_html=True,
        )
with k2:
    with st.container(border=True):
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#e0f2fe;color:#075985">📊</div>{delta_chip(pct_change(dogs_today, dogs_yday))}</div><div class="kpi-val">{dogs_today}</div><div class="kpi-lab">Total Dogs Detected</div>""",
            unsafe_allow_html=True,
        )
with k3:
    with st.container(border=True):
        st.markdown(
            f"""<div class="kpi-top"><div class="kpi-ico" style="background:#ffedd5;color:#9a3412">🚨</div>{delta_chip(pct_change(hp_today, hp_yday))}</div><div class="kpi-val">{hp_today}</div><div class="kpi-lab">High Priority</div>""",
            unsafe_allow_html=True,
        )

st.markdown('<div class="row-gap"></div>', unsafe_allow_html=True)

# =========================
# ROW 2: FEATURES (FLOATING WITH SHADOW)
# =========================
left, mid, right = st.columns([1.05, 0.95, 1.05], gap="medium")

# --- LEFT CARD ---
with left:
    with st.container(border=True):
        st.subheader("📷 Camera Feeds & Snapshots")
        st.caption("Latest detection (single feed)")
        
        # Inner scroll area (NO BORDER/SHADOW)
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No detection records.")
            else:
                r = df_sorted.iloc[0]
                uid = row_uid(r)
                ts_txt = r["ts"].strftime("%d/%m/%Y %H:%M")
                mins_ago = max(0, int((now - r["ts"]).total_seconds() // 60))
                dogs = int(r[col_dogs])
                cam = str(r[col_cam])
                loc = str(r[col_loc])

                img_ok = (col_img is not None) and str(r.get(col_img, "")).startswith("http")
                if img_ok:
                    st.markdown(f"""
                    <div class="thumb">
                      <img src="{str(r[col_img])}" />
                      <div class="overlay">
                        <div class="ov-pill">● ONLINE</div>
                        <div class="ov-pill ov-rec">● REC</div>
                        <div class="ov-cam">{cam}</div>
                      </div>
                      <div class="ov-det">📸 Detection {mins_ago}m ago • {dogs} dogs</div>
                    </div>
                    <div class="thumb-title">{loc}</div>
                    <div class="thumb-sub">{cam} • {ts_txt}</div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="thumb" style="height:220px;display:flex;align-items:center;justify-content:center;color:#64748b;font-weight:900">No Snapshot URL</div>""", unsafe_allow_html=True)
                    st.markdown(f"**{loc}**")
                    st.caption(f"{cam} • {ts_txt}")

                if st.button("Select this detection", key=f"single_select__{uid}", use_container_width=True):
                    st.session_state.selected_alert_uid = uid

# --- MIDDLE CARD ---
with mid:
    with st.container(border=True):
        st.subheader("⛔ Active Alerts")
        st.caption("Scroll to view older detections")

        # Inner scroll area (NO BORDER/SHADOW)
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            if len(df_sorted) == 0:
                st.info("No alerts.")
            else:
                lim = min(len(df_sorted), 150)
                for i in range(lim):
                    r = df_sorted.iloc[i]
                    uid = row_uid(r)
                    sev_style, sev_txt = severity_badge(r[col_sev])
                    conf = r[col_conf]
                    conf_txt = f"{conf:.0f}%" if pd.notna(conf) else "—"
                    ts_txt = r["ts"].strftime("%H:%M")
                    dogs = int(r[col_dogs])
                    ago_txt = time_ago(r["ts"], now)

                    st.markdown(f"""
                    <div style="padding:14px;border-radius:12px;border:1px solid #cbd5e1;background:#f8fafc;margin-bottom:10px">
                      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
                        <span style="font-weight:900;font-size:15px">{dogs} Dog(s)</span>
                        <span style="font-size:11px;font-weight:800;padding:2px 8px;border-radius:6px;{sev_style}">{sev_txt}</span>
                      </div>
                      <div style="display:flex;align-items:center;justify-content:space-between;color:#64748b;font-size:12px">
                        <span>📍 {str(r[col_loc])} • {ts_txt}</span>
                        <span style="background:white;padding:2px 6px;border-radius:4px;border:1px solid #e2e8f0;color:#0f172a">{ago_txt}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"View • {str(r[col_id])}", key=f"view__{uid}", use_container_width=True):
                        st.session_state.selected_alert_uid = uid

# --- RIGHT CARD ---
with right:
    with st.container(border=True):
        st.subheader("🖼️ Active Alert Picture")
        
        # Inner scroll area (NO BORDER/SHADOW)
        with st.container(height=SCROLLABLE_AREA_HEIGHT, border=False):
            sel = get_selected_row()
            if sel is None:
                st.info("Please select an alert to view the snapshot.")
            else:
                sev_style, sev_txt = severity_badge(sel[col_sev])
                ts_txt = sel["ts"].strftime("%d/%m %H:%M")
                conf_txt = f"{sel[col_conf]:.0f}%" if pd.notna(sel[col_conf]) else "—"

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                  <span style="font-weight:900;font-size:18px">{str(sel[col_id])}</span>
                  <span style="font-size:11px;font-weight:800;padding:2px 8px;border-radius:6px;{sev_style}">{sev_txt}</span>
                </div>
                """, unsafe_allow_html=True)

                img_ok = (col_img is not None) and str(sel.get(col_img, "")).startswith("http")
                if img_ok:
                    st.image(str(sel[col_img]), use_container_width=True)
                else:
                    st.markdown("""<div style="height:260px;border-radius:12px;border:1px dashed #cbd5e1;display:flex;align-items:center;justify-content:center;color:#64748b;font-weight:900">No Image</div>""", unsafe_allow_html=True)

                st.markdown(f"**📍 Location:** {str(sel[col_loc])}")
                st.markdown(f"**📷 Camera:** {str(sel[col_cam])}")
                st.markdown(f"**🕒 Time:** {ts_txt}")
                st.markdown(f"**🎯 Confidence:** {conf_txt}")

st.markdown('<div class="row-gap"></div>', unsafe_allow_html=True)

# =========================
# ROW 3: Trends
# =========================
with st.container(border=True):
    st.subheader("📈 Detection Trends & Analytics")
    mode = st.radio("Time Range", ["24 Hours", "7 Days", "Severity"], horizontal=True)

    if mode == "24 Hours":
        start = now - timedelta(hours=24)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        hourly = d.groupby("hour").agg(detections=(col_id, "count"), dogs=(col_dogs, "sum")).reset_index()
        hours = list(range(24))
        hourly = hourly.set_index("hour").reindex(hours, fill_value=0).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["detections"], mode="lines+markers", name="Detections"))
        fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["dogs"], mode="lines+markers", name="Dogs"))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
        peak = compute_peak_2hr(hourly.set_index("hour")["dogs"].to_dict())
        avg_daily = int(hourly["detections"].sum())

    elif mode == "7 Days":
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        d["day"] = d["ts"].dt.date
        daily = d.groupby("day").agg(detections=(col_id, "count"), dogs=(col_dogs, "sum")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["detections"], name="Detections"))
        fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["dogs"], name="Dogs"))
        fig.update_layout(barmode="group", margin=dict(l=10, r=10, t=10, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
        peak = compute_peak_2hr(d.groupby(d["ts"].dt.hour)[col_dogs].sum().to_dict())
        avg_daily = int(round(daily["detections"].mean())) if len(daily) else 0

    else:
        start = now - timedelta(days=7)
        d = df_sorted[df_sorted["ts"] >= start].copy()
        sev = d[col_sev].astype(str).str.upper().replace({"": "MEDIUM"}).fillna("MEDIUM")
        counts = sev.value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).fillna(0).astype(int)
        fig = go.Figure(data=[go.Pie(labels=list(counts.index), values=list(counts.values), hole=0.55)])
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
        peak = compute_peak_2hr(d.groupby(d["ts"].dt.hour)[col_dogs].sum().to_dict())
        d["day"] = d["ts"].dt.date
        daily = d.groupby("day").agg(detections=(col_id, "count")).reset_index()
        avg_daily = int(round(daily["detections"].mean())) if len(daily) else 0

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f"<div style='text-align:center;padding:14px 0 4px 0'><div class='small-muted'>Peak Hour</div><div style='font-weight:900;font-size:22px;color:#0f172a !important'>{peak}</div></div>", unsafe_allow_html=True)
    with b2:
        st.markdown(f"<div style='text-align:center;padding:14px 0 4px 0'><div class='small-muted'>Avg Daily Detections</div><div style='font-weight:900;font-size:22px;color:#0f172a !important'>{avg_daily}</div></div>", unsafe_allow_html=True)

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
    show["Confidence"] = np.where(pd.notna(recent[col_conf]), recent[col_conf].round(0).astype(int).astype(str) + "%", "—")
    st.dataframe(show, use_container_width=True, height=380)
