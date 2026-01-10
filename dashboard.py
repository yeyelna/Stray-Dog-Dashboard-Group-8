import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_MS=8000
TIME_WINDOW_MIN=10

st.set_page_config(page_title="Smart City Stray Dog Control System",layout="wide")
st_autorefresh(interval=REFRESH_MS,key="dash_refresh")

st.markdown("""
<style>
body{background-color:#f7f4ef;}
[data-testid="stAppViewContainer"]{
  background:#f7f4ef;
  color:#111827;
}
[data-testid="stSidebar"]{
  background:#f2ece3;
}
.block-container{
  padding-top:1.5rem;
  padding-bottom:1.5rem;
}

/* Generic soft white panel (for the three boxes) */
.panel-box{
  border-radius:1rem;
  background:#ffffff;
  border:1px solid #e5e7eb;
  padding:0.75rem 0.9rem;
  box-shadow:0 1px 3px rgba(15,23,42,0.06);
  height:430px;              /* 🔹 same height for all three */
  display:flex;
  flex-direction:column;
}
.panel-title{
  font-weight:600;
  font-size:0.95rem;
  margin-bottom:0.35rem;
}

/* scroll area inside the panel */
.scroll-panel{
  flex:1;
  overflow-y:auto;
  padding-right:0.3rem;
  margin-top:0.4rem;
}

/* Alert item styling (each row in the log) */
.alert-item{
  border-radius:0.7rem;
  border:1px solid #e5e7eb;
  background:#f9fafb;
  padding:0.5rem 0.6rem;
  margin-bottom:0.4rem;
}
.alert-item-title{
  font-weight:600;
  font-size:0.9rem;
}
.alert-item-sub{
  font-size:0.8rem;
  color:#6b7280;
}

/* badges, KPI styles etc – keep these from your previous CSS */
.badge{
  display:inline-block;
  padding:0.15rem 0.6rem;
  border-radius:999px;
  font-size:0.7rem;
  font-weight:600;
}
.badge-green{background:#dcfce7;color:#166534;}
.badge-yellow{background:#fef9c3;color:#854d0e;}
.badge-red{background:#fee2e2;color:#b91c1c;}

.kpi-card{
  padding:0.9rem 1.1rem;
  border-radius:1rem;
  background:#ffffff;
  border:1px solid #e5e7eb;
  box-shadow:0 1px 3px rgba(15,23,42,0.06);
}
.kpi-top-row{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:0.2rem;
}
.kpi-icon{
  width:32px;
  height:32px;
  border-radius:0.9rem;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:18px;
}
.kpi-icon-red{background:#fee2e2;color:#b91c1c;}
.kpi-icon-blue{background:#dbeafe;color:#1d4ed8;}
.kpi-icon-orange{background:#ffedd5;color:#c05621;}
.kpi-icon-green{background:#dcfce7;color:#166534;}
.kpi-delta{
  font-size:0.7rem;
  padding:0.15rem 0.5rem;
  border-radius:999px;
  font-weight:600;
}
.kpi-delta-red{background:#fee2e2;color:#b91c1c;}
.kpi-delta-green{background:#dcfce7;color:#166534;}
.kpi-value{
  font-size:1.8rem;
  font-weight:700;
  margin-top:0.2rem;
}
.kpi-label{
  font-size:0.85rem;
  color:#6b7280;
}
.metric-label{
  font-size:0.8rem;
  color:#6b7280;
}
</style>
""", unsafe_allow_html=True)

def generate_dummy_data(n=200):
    now=datetime.utcnow()
    cameras=["CAM-023","CAM-047","CAM-089","CAM-105","CAM-132"]
    locations=["Central Park, Zone A3","Market Street, Intersection 5B","Riverside Drive, Block 12","School District 4, Gate C","Industrial Area, Sector 7"]
    rows=[]
    for _ in range(n):
        ts=now-timedelta(minutes=np.random.randint(0,240))
        cam=np.random.choice(cameras)
        loc=np.random.choice(locations)
        cls="dog"
        conf=round(float(np.random.uniform(0.5,0.99)),2)
        image_url=""
        rows.append({"timestamp":ts,"camera_id":cam,"location":loc,"class":cls,"confidence":conf,"image":image_url})
    df=pd.DataFrame(rows)
    df=df.sort_values("timestamp").reset_index(drop=True)
    return df

@st.cache_data(ttl=5)
def load_data():
    try:
        df=pd.read_csv(SHEET_CSV_URL)
        if "timestamp" in df.columns:
            df["timestamp"]=pd.to_datetime(df["timestamp"],errors="coerce")
            df=df.dropna(subset=["timestamp"])
            df=df.sort_values("timestamp")
    except Exception:
        df=generate_dummy_data()
    return df

df=load_data()
if df.empty:
    st.error("No detection data available yet.")
    st.stop()

now_utc=datetime.utcnow()
total_dogs=len(df)
last_ts=df["timestamp"].max()

window_start=now_utc-timedelta(minutes=TIME_WINDOW_MIN)
prev_window_start=window_start-timedelta(minutes=TIME_WINDOW_MIN)
recent=df[df["timestamp"]>=window_start]
prev=df[(df["timestamp"]>=prev_window_start)&(df["timestamp"]<window_start)]
recent_highconf=recent[recent.get("confidence",0)>=0.7]
prev_highconf=prev[prev.get("confidence",0)>=0.7]
recent_count=len(recent_highconf)

def pct_change(curr,prev):
    if prev<=0:
        return "+0%"
    change=(curr-prev)/prev*100.0
    sign="+" if change>=0 else ""
    return f"{sign}{change:.0f}%"

delta_new_alerts=pct_change(len(recent_highconf),len(prev_highconf))
delta_total_dogs=pct_change(total_dogs,max(total_dogs-len(recent),0))
delta_high_priority=pct_change(recent_count,len(prev_highconf))
delta_response="-5%"

if recent_count==0:
    severity_label="No Active"
    severity_color="badge-green"
    severity_desc="No active detection in last 10 minutes."
elif recent_count<=2:
    severity_label="Low"
    severity_color="badge-yellow"
    severity_desc=f"Low activity: {recent_count} high-confidence detection(s) in last 10 minutes."
elif recent_count<=4:
    severity_label="Medium"
    severity_color="badge-yellow"
    severity_desc=f"Medium activity: {recent_count} detections in last 10 minutes."
else:
    severity_label="High"
    severity_color="badge-red"
    severity_desc=f"High activity: {recent_count} detections in last 10 minutes – immediate attention."

new_alerts=recent_count
high_priority=1 if severity_label in ["High","Medium"] else 0
avg_response_min=3.2

image_col=None
for c in ["image","image_url","snapshot_url"]:
    if c in df.columns:
        image_col=c
        break

header_left,header_right=st.columns([4,2])
with header_left:
    st.markdown("### 🐕 Smart City Stray Dog Control System")
    st.caption("Real-Time AI Detection Monitoring")
with header_right:
    st.markdown(
        f"<div style='text-align:right;'><span class='badge badge-green'>System Active</span><br/>"
        f"<span class='metric-label'>Last update:</span> {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        f"</div>",unsafe_allow_html=True)

st.write("")

def render_kpi(label,value,icon,delta,icon_class,delta_positive=True):
    delta_class="kpi-delta-red" if delta_positive else "kpi-delta-green"
    html=f"""
    <div class="kpi-card">
      <div class="kpi-top-row">
        <div class="kpi-icon {icon_class}">{icon}</div>
        <div class="kpi-delta {delta_class}">{delta}</div>
      </div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
    </div>
    """
    st.markdown(html,unsafe_allow_html=True)

c1,c2,c3,c4=st.columns(4)
with c1:
    render_kpi("New Alerts",new_alerts,"⚠️",delta_new_alerts,"kpi-icon-red",True)
with c2:
    render_kpi("Total Dogs Detected",total_dogs,"📈",delta_total_dogs,"kpi-icon-blue",True)
with c3:
    render_kpi("High Priority",high_priority,"⚠️",delta_high_priority,"kpi-icon-orange",True)
with c4:
    render_kpi("Avg Response Time",f"{avg_response_min:.1f}m","⏱️",delta_response,"kpi-icon-green",False)

st.write("")

st.markdown(
    f"<div class='card' style='border-left:4px solid #f97316;margin-bottom:0.8rem;'>"
    f"<span class='{severity_color}'>{severity_label.upper()}</span>"
    f"<span style='margin-left:0.5rem;'>{severity_desc}</span>"
    f"</div>",unsafe_allow_html=True)

st.write("")

row2_col1, row2_col2, row2_col3 = st.columns([2,2,1.7])

# 🔹 ACTIVE ALERTS – light panel + scroll log
with row2_col1:
    st.markdown("""
    <div class="panel-box">
      <div class="panel-title">Active Alerts</div>
    """, unsafe_allow_html=True)

    alert_tab = st.radio(
        "Filter alerts",
        options=["All","New"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    base_alerts = df[df.get("confidence",0) >= 0.7].copy()
    base_alerts = base_alerts.sort_values("timestamp", ascending=False)

    if alert_tab == "New":
        alerts = recent_highconf.sort_values("timestamp", ascending=False)
    else:
        alerts = base_alerts.head(50)

    st.markdown('<div class="scroll-panel">', unsafe_allow_html=True)
    if alerts.empty:
        st.write("No alerts to display.")
    else:
        for _, row in alerts.iterrows():
            ts_diff = now_utc - row["timestamp"]
            mins_ago = int(ts_diff.total_seconds() // 60)
            ago_txt = "Just now" if mins_ago == 0 else f"{mins_ago} min ago"
            conf = row.get("confidence",0)
            loc = row.get("location","Unknown location")
            cam = row.get("camera_id","Unknown")
            cls = row.get("class","Dog").title()

            st.markdown(
                f"<div class='alert-item'>"
                f"<div class='alert-item-title'>{cls} detected</div>"
                f"<div class='alert-item-sub'>{loc}</div>"
                f"<div class='alert-item-sub'>{ago_txt} • {conf*100:.0f}% confidence • {cam}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("</div></div>", unsafe_allow_html=True)  # close scroll-panel + panel-box

# 🔹 ALERT DETAILS – light panel, same height
with row2_col2:
    st.markdown("""
    <div class="panel-box">
      <div class="panel-title">Alert Details</div>
    """, unsafe_allow_html=True)

    alerts_all = base_alerts.head(50)
    if alerts_all.empty:
        st.info("No alerts available.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        idx_options = alerts_all.index.tolist()
        selected_idx = st.selectbox(
            "Select alert",
            options=idx_options,
            format_func=lambda i:
                f"{alerts_all.loc[i,'class'].title()} at {alerts_all.loc[i,'location']} "
                f"({alerts_all.loc[i,'timestamp'].strftime('%Y-%m-%d %H:%M')})"
        )

        sel = alerts_all.loc[selected_idx]

        # Optional snapshot
        if image_col and isinstance(sel.get(image_col,""),str) and sel.get(image_col,"").strip():
            st.image(sel[image_col], use_column_width=True)
        else:
            st.info("No snapshot image available for this alert.")

        st.markdown('<div class="scroll-panel">', unsafe_allow_html=True)
        st.markdown("**Detection Information**")
        st.write(f"Class: {sel.get('class','dog').title()}")
        st.write(f"Confidence: {sel.get('confidence',0)*100:.0f}%")
        st.write("")
        st.write(f"**Location:** {sel.get('location','-')}")
        st.write(f"**Camera ID:** {sel.get('camera_id','-')}")
        st.write(f"**Detected At:** {sel.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("</div></div>", unsafe_allow_html=True)

# 🔹 RECENT ACTIVITY – light panel + scroll log
with row2_col3:
    st.markdown("""
    <div class="panel-box">
      <div class="panel-title">Recent Activity</div>
    """, unsafe_allow_html=True)

    recent_activity = df.sort_values("timestamp", ascending=False).head(25)

    st.markdown('<div class="scroll-panel">', unsafe_allow_html=True)
    if recent_activity.empty:
        st.write("No recent activity.")
    else:
        for _, row in recent_activity.iterrows():
            ts = row["timestamp"].strftime("%H:%M")
            loc = row.get("location","Unknown location")
            cam = row.get("camera_id","Unknown")
            cls = row.get("class","Dog").title()

            st.markdown(
                f"<div class='alert-item'>"
                f"<div class='alert-item-title'>{cls} at {loc}</div>"
                f"<div class='alert-item-sub'>{ts} • {cam}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("</div></div>", unsafe_allow_html=True)

st.write("")

row3_col1,row3_col2=st.columns([2,2])

with row3_col1:
    st.markdown("#### Detection Trends & Analytics")
    df_time=df.copy()
    df_time["time_bucket"]=df_time["timestamp"].dt.floor("H")
    detections=df_time.groupby("time_bucket").size()
    if "class" in df_time.columns:
        dogs=df_time[df_time["class"].str.lower()=="dog"].groupby("time_bucket").size()
    else:
        dogs=detections.copy()
    df_line=pd.DataFrame({"Detections":detections,"Dogs":dogs}).fillna(0)
    if not df_line.empty:
        st.line_chart(df_line)
    else:
        st.info("Not enough data to display trends yet.")

with row3_col2:
    st.markdown("#### Camera Feeds & Snapshots")
    if "camera_id" not in df.columns:
        st.info("Camera information not available.")
    else:
        latest_by_cam=df.sort_values("timestamp").groupby("camera_id").tail(1)
        for _,row in latest_by_cam.iterrows():
            st.markdown("<div class='card'>",unsafe_allow_html=True)
            if image_col and isinstance(row.get(image_col,""),str) and row.get(image_col,"").strip():
                st.image(row[image_col],use_column_width=True)
            loc=row.get("location","Unknown")
            cam=row.get("camera_id","-")
            ts_diff=now_utc-row["timestamp"]
            mins_ago=int(ts_diff.total_seconds()//60)
            ago_txt="Just now" if mins_ago==0 else f"{mins_ago} min ago"
            st.markdown(f"**{loc}**  \n{cam}")
            st.caption(f"Detection {ago_txt} • {row.get('confidence',0)*100:.0f}% confidence")
            st.markdown("</div>",unsafe_allow_html=True)

st.write("")
st.markdown("#### Recent Detection Events")
cols=[c for c in ["timestamp","camera_id","location","class","confidence"] if c in df.columns]
st.dataframe(
    df.sort_values("timestamp",ascending=False)[cols].head(50).reset_index(drop=True)
)
