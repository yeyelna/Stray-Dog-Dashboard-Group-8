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
TZ=ZoneInfo("Asia/Kuala_Lumpur")
SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_SEC=8

# =========================
# THEME / CSS
# =========================
st.markdown("""
<style>
html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial}
.stApp{background:#f7f4ef}
.block-container{padding-top:1rem;padding-bottom:1.2rem}
.card{background:#faf7f2;border:1px solid rgba(30,41,59,.10);border-radius:16px;box-shadow:0 6px 18px rgba(15,23,42,.06);padding:14px}
.card-tight{background:#faf7f2;border:1px solid rgba(30,41,59,.10);border-radius:16px;box-shadow:0 6px 18px rgba(15,23,42,.06);padding:12px}
.hrow{display:flex;gap:14px}
.kpi{height:120px}
.row2box{height:560px}
.row3box{height:560px}
.row4box{height:460px}
.kpi-top{display:flex;align-items:center;justify-content:space-between}
.kpi-ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center}
.kpi-val{font-size:32px;font-weight:800;margin-top:6px;color:#0f172a}
.kpi-lab{font-size:13px;color:#475569;margin-top:-2px}
.delta{font-size:12px;font-weight:700;padding:4px 8px;border-radius:10px;display:inline-block}
.delta-pos{background:#fee2e2;color:#991b1b}
.delta-neg{background:#dcfce7;color:#166534}
.badge{font-size:12px;font-weight:800;padding:6px 10px;border-radius:10px;display:inline-block}
.badge-low{background:#dbeafe;color:#1d4ed8}
.badge-med{background:#fef3c7;color:#92400e}
.badge-high{background:#ffedd5;color:#9a3412}
.badge-crit{background:#ffe4e6;color:#9f1239}
.badge-new{background:#ffe4e6;color:#b91c1c}
.badge-ack{background:#e0f2fe;color:#075985}
.badge-dis{background:#dcfce7;color:#166534}
.small-muted{font-size:12px;color:#64748b}
.title{font-size:22px;font-weight:900;color:#0f172a;margin-bottom:2px}
.subtitle{font-size:13px;color:#475569;margin-top:-2px}
.headerbar{background:#ffffff;border:1px solid rgba(30,41,59,.10);border-radius:16px;box-shadow:0 6px 18px rgba(15,23,42,.06);padding:14px 16px;margin-bottom:12px}
.pill{display:inline-flex;align-items:center;gap:8px;padding:9px 12px;border-radius:14px;border:1px solid rgba(30,41,59,.12);background:#ffffff;font-weight:800}
.pill-green{background:#ecfdf5;border-color:#bbf7d0;color:#166534}
.pill-yellow{background:#fffbeb;border-color:#fde68a;color:#92400e}
.seg-wrap{display:flex;justify-content:flex-end;gap:10px}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPERS
# =========================
def _clean_cols(df: pd.DataFrame)->pd.DataFrame:
    df=df.copy()
    df.columns=[str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def parse_ts(x):
    if pd.isna(x): 
        return pd.NaT
    s=str(x).strip()
    if s=="":
        return pd.NaT
    # dd/mm/yyyy HH:MM (Malaysia local)
    try:
        if "/" in s and ":" in s and "t" not in s.lower():
            dt=datetime.strptime(s, "%d/%m/%Y %H:%M")
            return dt.replace(tzinfo=TZ)
    except:
        pass
    # ISO / general parser (keeps timezone if present)
    try:
        dt=parser.isoparse(s)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except:
        return pd.NaT

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def to_num(s):
    if s is None:
        return None
    try:
        return pd.to_numeric(s, errors="coerce")
    except:
        return pd.Series([np.nan]*len(s))

def severity_badge(sev):
    sev=str(sev).strip().upper()
    if sev=="LOW": 
        return "badge badge-low", "LOW"
    if sev=="MEDIUM": 
        return "badge badge-med", "MEDIUM"
    if sev=="HIGH": 
        return "badge badge-high", "HIGH"
    if sev=="CRITICAL": 
        return "badge badge-crit", "CRITICAL"
    return "badge badge-med", sev if sev!="" else "MEDIUM"

def status_badge(sts):
    s=str(sts).strip().upper()
    if s=="NEW": 
        return "badge badge-new", "NEW"
    if s=="ACKNOWLEDGED": 
        return "badge badge-ack", "ACKNOWLEDGED"
    if s=="DISPATCHED": 
        return "badge badge-dis", "DISPATCHED"
    return "badge badge-new", s if s!="" else "NEW"

def delta_chip(pct):
    if pct is None or np.isnan(pct):
        return '<span class="delta delta-pos">+0%</span>'
    if pct>=0:
        return f'<span class="delta delta-pos">+{pct:.0f}%</span>'
    return f'<span class="delta delta-neg">{pct:.0f}%</span>'

def compute_peak_2hr(hourly_dogs):
    # hourly_dogs: index 0..23, values dogs count
    if hourly_dogs is None or len(hourly_dogs)==0:
        return "—"
    arr=np.zeros(24)
    for h in range(24):
        arr[h]=hourly_dogs.get(h, 0)
    best_h=0
    best_sum=-1
    for h in range(24):
        s=arr[h]+arr[(h+1)%24]
        if s>best_sum:
            best_sum=s
            best_h=h
    return f"{best_h:02d}:00 - {(best_h+2)%24:02d}:00"

@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data(url):
    # robust CSV loading even if some rows have extra commas/fields
    df=pd.read_csv(url, dtype=str, engine="python", on_bad_lines="skip")
    df=_clean_cols(df)
    return df

# =========================
# AUTO REFRESH
# =========================
st_autorefresh(interval=REFRESH_SEC*1000, key="auto_refresh")

# =========================
# LOAD DATA
# =========================
raw=load_data(SHEET_CSV_URL)
if raw.empty:
    st.error("No data loaded from Google Sheets CSV.")
    st.stop()

# =========================
# STANDARDIZE COLUMNS
# =========================
col_ts=pick_col(raw, ["timestamp","time","datetime","date_time","detected_time"])
col_id=pick_col(raw, ["detection_id","det_id","id","event_id"])
col_loc=pick_col(raw, ["location","area","zone","site","place"])
col_cam=pick_col(raw, ["camera","camera_id","cam","camera_name"])
col_camtype=pick_col(raw, ["camera_type","type"])
col_dogs=pick_col(raw, ["dogs","dog_count","num_dogs","count"])
col_breed=pick_col(raw, ["breed","dog_breed"])
col_conf=pick_col(raw, ["confidence","conf","score"])
col_sev=pick_col(raw, ["severity","priority","level"])
col_status=pick_col(raw, ["status","alert_status","state"])
# any likely image url column
img_candidates=[c for c in raw.columns if ("url" in c or "image" in c or "snapshot" in c or "photo" in c)]
col_img=pick_col(raw, ["snapshot_url","image_url","img_url","photo_url","snapshot","image","url"]) or (img_candidates[0] if len(img_candidates)>0 else None)

df=raw.copy()
if col_ts is None:
    st.error("Your sheet must have a timestamp column (e.g., 'timestamp').")
    st.stop()

df["ts"]=df[col_ts].apply(parse_ts)
df=df.dropna(subset=["ts"])
df["date_local"]=df["ts"].dt.date
df["hour"]=df["ts"].dt.hour

if col_id is None:
    df["detection_id"]=["DET-"+str(i).zfill(6) for i in range(1, len(df)+1)]
    col_id="detection_id"
if col_loc is None:
    df["location"]="Unknown"
    col_loc="location"
if col_cam is None:
    df["camera"]="CAM-000"
    col_cam="camera"
if col_camtype is None:
    df["camera_type"]="WEBCAM"
    col_camtype="camera_type"
if col_dogs is None:
    df["dogs"]=1
    col_dogs="dogs"
if col_conf is None:
    df["confidence"]=np.nan
    col_conf="confidence"
if col_sev is None:
    # fallback severity from dogs count
    dnum=pd.to_numeric(df[col_dogs], errors="coerce").fillna(1)
    sev=np.where(dnum>=4, "CRITICAL", np.where(dnum>=3, "HIGH", np.where(dnum>=2, "MEDIUM", "LOW")))
    df["severity"]=sev
    col_sev="severity"
if col_status is None:
    df["status"]="NEW"
    col_status="status"
if col_breed is None:
    df["breed"]="Mixed"
    col_breed="breed"

df[col_dogs]=pd.to_numeric(df[col_dogs], errors="coerce").fillna(0).astype(int)
df[col_conf]=pd.to_numeric(df[col_conf], errors="coerce")

# =========================
# HEADER
# =========================
now=datetime.now(TZ)
today=now.date()
yesterday=(now-timedelta(days=1)).date()
kpi_today=df[df["date_local"]==today]
kpi_yday=df[df["date_local"]==yesterday]

def pct_change(today_val, yday_val):
    try:
        if yday_val==0:
            return 0.0 if today_val==0 else 100.0
        return ((today_val-yday_val)/yday_val)*100.0
    except:
        return 0.0

new_today=int((kpi_today[col_status].astype(str).str.upper()=="NEW").sum())
new_yday=int((kpi_yday[col_status].astype(str).str.upper()=="NEW").sum())
dogs_today=int(kpi_today[col_dogs].sum())
dogs_yday=int(kpi_yday[col_dogs].sum())
hp_today=int(kpi_today[col_sev].astype(str).str.upper().isin(["HIGH","CRITICAL"]).sum())
hp_yday=int(kpi_yday[col_sev].astype(str).str.upper().isin(["HIGH","CRITICAL"]).sum())

st.markdown(f"""
<div class="headerbar">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px">
    <div style="display:flex;align-items:center;gap:12px">
      <div class="kpi-ico" style="background:#dbeafe;color:#1d4ed8;font-weight:900">⚠️</div>
      <div>
        <div class="title">Smart City Stray Dog Control System</div>
        <div class="subtitle">Real-Time AI Detection Monitoring</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px">
      <div class="pill pill-green">📈 <span>System Active</span></div>
      <div class="pill pill-yellow">🔔 <span>{new_today} New Alerts</span></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# ROW 1: KPI CARDS (same height)
# =========================
c1,c2,c3=st.columns(3)
with c1:
    st.markdown(f"""
    <div class="card kpi">
      <div class="kpi-top">
        <div class="kpi-ico" style="background:#fee2e2;color:#b91c1c">⛔</div>
        {delta_chip(pct_change(new_today,new_yday))}
      </div>
      <div class="kpi-val">{new_today}</div>
      <div class="kpi-lab">New Alerts</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="card kpi">
      <div class="kpi-top">
        <div class="kpi-ico" style="background:#e0f2fe;color:#075985">📊</div>
        {delta_chip(pct_change(dogs_today,dogs_yday))}
      </div>
      <div class="kpi-val">{dogs_today}</div>
      <div class="kpi-lab">Total Dogs Detected</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="card kpi">
      <div class="kpi-top">
        <div class="kpi-ico" style="background:#ffedd5;color:#9a3412">🚨</div>
        {delta_chip(pct_change(hp_today,hp_yday))}
      </div>
      <div class="kpi-val">{hp_today}</div>
      <div class="kpi-lab">High Priority</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# DATASETS FOR LISTS
# =========================
df_sorted=df.sort_values("ts", ascending=False).reset_index(drop=True)
alerts_all=df_sorted.copy()

# =========================
# SESSION STATE (selected alert)
# =========================
if "selected_alert_id" not in st.session_state:
    st.session_state.selected_alert_id=str(df_sorted.loc[0, col_id]) if len(df_sorted)>0 else ""

def get_selected_row():
    if st.session_state.selected_alert_id=="":
        return None
    m=df_sorted[df_sorted[col_id].astype(str)==str(st.session_state.selected_alert_id)]
    if len(m)==0:
        return None
    return m.iloc[0]

# =========================
# ROW 2: CAMERA FEEDS + ACTIVE ALERTS + SELECTED IMAGE (same height)
# =========================
left,mid,right=st.columns([1.15,0.95,1.15])

with left:
    st.markdown('<div class="card row2box">', unsafe_allow_html=True)
    st.markdown("### 📷 Camera Feeds & Snapshots")
    st.caption("Latest detections (gallery)")
    gallery=df_sorted.head(4).copy()
    g1,g2=st.columns(2)
    boxes=[g1,g2,g1,g2]
    for i in range(len(gallery)):
        r=gallery.iloc[i]
        with boxes[i]:
            title=f"{str(r[col_loc])}"
            sub=f"{str(r[col_cam])} • {r['ts'].strftime('%d/%m/%Y %H:%M')}"
            if col_img and str(r.get(col_img,"")).startswith("http"):
                st.image(str(r[col_img]), use_container_width=True)
                st.markdown(f"**{title}**  \n<span class='small-muted'>{sub}</span>", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="height:130px;border-radius:14px;border:1px dashed rgba(30,41,59,.18);
                background:#ffffff;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-weight:800">
                No Snapshot URL
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"**{title}**  \n<span class='small-muted'>{sub}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with mid:
    st.markdown('<div class="card row2box">', unsafe_allow_html=True)
    st.markdown("### ⛔ Active Alerts")
    tab_all,tab_new,tab_ack,tab_dis=st.tabs(["All","New","Acknowledged","Dispatched"])
    def render_alert_list(data):
        with st.container(height=460):
            for i in range(min(len(data), 60)):
                r=data.iloc[i]
                sev_class,sev_txt=severity_badge(r[col_sev])
                sts_class,sts_txt=status_badge(r[col_status])
                conf_val=r[col_conf]
                conf_txt=f"{conf_val:.0f}%" if pd.notna(conf_val) else "—"
                ts_txt=r["ts"].strftime("%d/%m/%Y %H:%M")
                if st.button(f"View • {str(r[col_id])}", key=f"view_{str(r[col_id])}_{i}", use_container_width=True):
                    st.session_state.selected_alert_id=str(r[col_id])
                st.markdown(f"""
                <div style="padding:10px 10px;margin:10px 0;border-radius:14px;border:1px solid rgba(30,41,59,.10);background:#ffffff">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
                    <div style="min-width:0">
                      <div style="font-weight:900;color:#0f172a">{int(r[col_dogs])} Dogs Detected <span class="{sev_class}" style="margin-left:8px">{sev_txt}</span></div>
                      <div class="small-muted">{str(r[col_camtype])} • {str(r[col_cam])}</div>
                      <div class="small-muted">📍 {str(r[col_loc])}</div>
                      <div class="small-muted">🕒 {ts_txt} • 🎯 {conf_txt}</div>
                    </div>
                    <div style="text-align:right">
                      <div class="{sts_class}">{sts_txt}</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
    with tab_all:
        render_alert_list(alerts_all)
    with tab_new:
        render_alert_list(alerts_all[alerts_all[col_status].astype(str).str.upper()=="NEW"])
    with tab_ack:
        render_alert_list(alerts_all[alerts_all[col_status].astype(str).str.upper()=="ACKNOWLEDGED"])
    with tab_dis:
        render_alert_list(alerts_all[alerts_all[col_status].astype(str).str.upper()=="DISPATCHED"])
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card row2box">', unsafe_allow_html=True)
    st.markdown("### 🖼️ Active Alert Picture")
    selected=get_selected_row()
    if selected is None:
        st.info("Please choose any active alerts.")
    else:
        sev_class,sev_txt=severity_badge(selected[col_sev])
        ts_txt=selected["ts"].strftime("%d/%m/%Y %H:%M")
        st.markdown(f"**{str(selected[col_id])}**  \n<span class='{sev_class}'>{sev_txt}</span>  \n<span class='small-muted'>📍 {str(selected[col_loc])} • 🕒 {ts_txt}</span>", unsafe_allow_html=True)
        if col_img and str(selected.get(col_img,"")).startswith("http"):
            st.image(str(selected[col_img]), use_container_width=True)
        else:
            st.markdown("""
            <div style="height:360px;border-radius:16px;border:1px dashed rgba(30,41,59,.18);
            background:#ffffff;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-weight:900">
            No Snapshot URL in Sheet
            </div>
            """, unsafe_allow_html=True)
        conf_val=selected[col_conf]
        conf_txt=f"{conf_val:.0f}%" if pd.notna(conf_val) else "—"
        st.markdown(f"- **Camera:** {str(selected[col_cam])} ({str(selected[col_camtype])})")
        st.markdown(f"- **Dogs:** {int(selected[col_dogs])}")
        st.markdown(f"- **Breed:** {str(selected[col_breed])}")
        st.markdown(f"- **Confidence:** {conf_txt}")
        st.markdown(f"- **Status:** {str(selected[col_status])}")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# ROW 3: DETECTION TRENDS & ANALYTICS (same height)
# =========================
st.markdown('<div class="card row3box">', unsafe_allow_html=True)
topL,topR=st.columns([0.55,0.45])
with topL:
    st.markdown("### 📈 Detection Trends & Analytics")
with topR:
    mode=st.radio(" ", ["24 Hours","7 Days","Severity"], horizontal=True, label_visibility="collapsed")

if mode=="24 Hours":
    start=now-timedelta(hours=24)
    d=df[df["ts"]>=start].copy()
    hourly=d.groupby("hour").agg(detections=(col_id,"count"), dogs=(col_dogs,"sum")).reset_index()
    hours=list(range(24))
    hourly=hourly.set_index("hour").reindex(hours, fill_value=0).reset_index()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["detections"], mode="lines+markers", name="Detections"))
    fig.add_trace(go.Scatter(x=hourly["hour"], y=hourly["dogs"], mode="lines+markers", name="Dogs"))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=380, xaxis_title="", yaxis_title="")
    fig.update_xaxes(dtick=1, tickmode="linear")
    st.plotly_chart(fig, use_container_width=True)
    hourly_dogs=hourly.set_index("hour")["dogs"].to_dict()
    peak=compute_peak_2hr(hourly_dogs)
    avg_daily=int(hourly["detections"].sum())
elif mode=="7 Days":
    start=now-timedelta(days=7)
    d=df[df["ts"]>=start].copy()
    d["day"]=d["ts"].dt.date
    daily=d.groupby("day").agg(detections=(col_id,"count"), dogs=(col_dogs,"sum")).reset_index()
    fig=go.Figure()
    fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["detections"], name="Detections"))
    fig.add_trace(go.Bar(x=daily["day"].astype(str), y=daily["dogs"], name="Dogs"))
    fig.update_layout(barmode="group", margin=dict(l=10,r=10,t=10,b=10), height=380, xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    hourly_dogs=d.groupby(d["ts"].dt.hour)[col_dogs].sum().to_dict()
    peak=compute_peak_2hr(hourly_dogs)
    avg_daily=int(round(daily["detections"].mean())) if len(daily)>0 else 0
else:
    start=now-timedelta(days=7)
    d=df[df["ts"]>=start].copy()
    sev=d[col_sev].astype(str).str.upper().replace({"":"MEDIUM"}).fillna("MEDIUM")
    counts=sev.value_counts().reindex(["CRITICAL","HIGH","MEDIUM","LOW"]).fillna(0).astype(int)
    fig=go.Figure(data=[go.Pie(labels=list(counts.index), values=list(counts.values), hole=0.55)])
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=380)
    st.plotly_chart(fig, use_container_width=True)
    hourly_dogs=d.groupby(d["ts"].dt.hour)[col_dogs].sum().to_dict()
    peak=compute_peak_2hr(hourly_dogs)
    d["day"]=d["ts"].dt.date
    daily=d.groupby("day").agg(detections=(col_id,"count")).reset_index()
    avg_daily=int(round(daily["detections"].mean())) if len(daily)>0 else 0

b1,b2=st.columns(2)
with b1:
    st.markdown(f"<div style='text-align:center;padding-top:6px'><div class='small-muted'>Peak Hour</div><div style='font-weight:900;font-size:22px;color:#7c3aed'>{peak}</div></div>", unsafe_allow_html=True)
with b2:
    st.markdown(f"<div style='text-align:center;padding-top:6px'><div class='small-muted'>Avg Daily Detections</div><div style='font-weight:900;font-size:22px;color:#2563eb'>{avg_daily}</div></div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# ROW 4: RECENT DETECTION EVENTS (last 50, scrollable fixed height)
# =========================
st.markdown('<div class="card row4box">', unsafe_allow_html=True)
st.markdown("### 🧾 Recent Detection Events")
st.caption("Last 50 records (scrollable)")
recent=df_sorted.head(50).copy()
recent_show=recent[[col_ts,col_id,col_loc,col_cam,col_dogs,col_breed,col_conf,col_sev,col_status]].copy()
recent_show.columns=["Timestamp","Detection ID","Location","Camera","Dogs","Breed","Confidence","Severity","Status"]
recent_show["Timestamp"]=recent["ts"].dt.strftime("%b %d, %I:%M %p")
recent_show["Confidence"]=np.where(pd.notna(recent[col_conf]), (recent[col_conf].round(0)).astype(int).astype(str)+"%", "—")
st.dataframe(recent_show, use_container_width=True, height=350)
st.markdown("</div>", unsafe_allow_html=True)
