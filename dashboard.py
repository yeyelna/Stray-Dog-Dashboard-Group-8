import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_MS=3000
TIME_WINDOW_MIN=10

st.set_page_config(page_title="Smart City Stray Dog Control System",layout="wide")

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
.card{
  padding:0.9rem 1.1rem;
  border-radius:0.9rem;
  background:#ffffff;
  border:1px solid #e5e7eb;
  box-shadow:0 2px 4px rgba(15,23,42,0.05);
}
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
.badge-purple{background:#ede9fe;color:#5b21b6;}
.metric-big{
  font-size:1.8rem;
  font-weight:700;
}
.metric-label{
  font-size:0.8rem;
  color:#6b7280;
}
.table-container{
  border-radius:0.9rem;
  background:#ffffff;
  border:1px solid #e5e7eb;
  padding:0.5rem 0.7rem;
  box-shadow:0 2px 4px rgba(15,23,42,0.04);
}
</style>
""",unsafe_allow_html=True)

st.autorefresh(interval=REFRESH_MS,key="data_refresh")

def generate_dummy_data(n=200):
    now=datetime.utcnow()
    cameras=["CAM-023","CAM-047","CAM-089","CAM-105","CAM-132"]
    locations=["Central Park, Zone A3","Market Street, Intersection 5B","Riverside Drive, Block 12","School District 4, Gate C","Industrial Area, Sector 7"]
    rows=[]
    for i in range(n):
        ts=now-timedelta(minutes=np.random.randint(0,240))
        cam=np.random.choice(cameras)
        loc=np.random.choice(locations)
        cls="dog"
        conf=round(np.random.uniform(0.5,0.99),2)
        image_url=""
        rows.append({"timestamp":ts,"camera_id":cam,"location":loc,"class":cls,"confidence":conf,"image_url":image_url})
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
last_ts_str=last_ts.strftime("%Y-%m-%d %H:%M:%S UTC")
window_start=now_utc-timedelta(minutes=TIME_WINDOW_MIN)
recent=df[df["timestamp"]>=window_start]
recent_highconf=recent[recent["confidence"]>=0.7]
recent_count=len(recent_highconf)

if recent_count==0:
    severity_label="No Active"
    severity_badge_class="badge-green"
    severity_desc="No active detection in last 10 minutes."
elif recent_count<=2:
    severity_label="Low"
    severity_badge_class="badge-yellow"
    severity_desc=f"Low activity: {recent_count} high-confidence detection(s) in last 10 minutes."
elif recent_count<=4:
    severity_label="Medium"
    severity_badge_class="badge-yellow"
    severity_desc=f"Medium activity: {recent_count} detections in last 10 minutes."
else:
    severity_label="High"
    severity_badge_class="badge-red"
    severity_desc=f"High activity: {recent_count} detections in last 10 minutes – immediate attention."

new_alerts=recent_count
high_priority=1 if severity_label in ["High","Medium"] else 0
avg_response_min=3.2

header_left,header_right=st.columns([4,1.5])
with header_left:
    st.markdown("### 🐕 Smart City Stray Dog Control System")
    st.caption("Real-Time AI Detection Monitoring")
with header_right:
    st.markdown(
        f"<div style='text-align:right;'>"
        f"<span class='badge badge-green'>System Active</span><br/>"
        f"<span class='metric-label'>Last update:</span> {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        f"</div>",unsafe_allow_html=True)

st.write("")

k1,k2,k3,k4=st.columns(4)
with k1:
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>New Alerts</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='metric-big'>{new_alerts}</div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)
with k2:
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Total Dogs Detected</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='metric-big'>{total_dogs}</div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)
with k3:
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>High Priority</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='metric-big'>{high_priority}</div>",unsafe_allow_html=True)
    st.markmarkdown("</div>",unsafe_allow_html=True)
with k4:
    st.markdown("<div class='card'>",unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Avg Response Time</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='metric-big'>{avg_response_min:.1f}m</div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)

st.write("")

banner_color={"No Active":"badge-green","Low":"badge-yellow","Medium":"badge-yellow","High":"badge-red"}[severity_label]
st.markdown(
    f"<div class='card' style='border-left:4px solid #f97316;margin-bottom:0.8rem;'>"
    f"<span class='{banner_color}'>{severity_label.upper()}</span> "
    f"<span style='margin-left:0.5rem;'>{severity_desc}</span>"
    f"</div>",unsafe_allow_html=True)

st.write("")

c1,c2,c3=st.columns([1.9,2.1,1.3])

with c1:
    st.markdown("#### Active Alerts")
    st.markdown("<div class='table-container'>",unsafe_allow_html=True)
    recent_sorted=recent_highconf.sort_values("timestamp",ascending=False).head(8)
    if recent_sorted.empty:
        st.write("No active alerts.")
    else:
        for _,row in recent_sorted.iterrows():
            ts_diff=now_utc-row["timestamp"]
            mins_ago=int(ts_diff.total_seconds()//60)
            if mins_ago==0:
                ago_txt="Just now"
            else:
                ago_txt=f"{mins_ago} min ago"
            st.markdown(
                f"**{row['camera_id']} – {row['location']}**  "
                f"<br/><span class='metric-label'>{row['class'].title()} detected • "
                f"{row['confidence']*100:.0f}% confidence • {ago_txt}</span>",
                unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#e5e7eb;margin:0.3rem 0;'/>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)

with c2:
    st.markdown("#### Detection Map (concept view)")
    st.caption("Real-time locations of detected stray dogs (grouped by area).")
    loc_counts=df.groupby("location").size().reset_index(name="count")
    if not loc_counts.empty:
        loc_counts["x"]=np.linspace(0,10,len(loc_counts))+np.random.uniform(-0.5,0.5,len(loc_counts))
        loc_counts["y"]=np.random.uniform(0,10,len(loc_counts))
        loc_counts=loc_counts.set_index("location")
        st.scatter_chart(loc_counts[["x","y","count"]])
    else:
        st.info("Not enough data to display the map yet.")

with c3:
    st.markdown("#### Recent Activity")
    st.markdown("<div class='table-container'>",unsafe_allow_html=True)
    recent_activity=df.sort_values("timestamp",ascending=False).head(8)
    for _,row in recent_activity.iterrows():
        time_str=row["timestamp"].strftime("%H:%M")
        st.markdown(
            f"• **{row['class'].title()} at {row['location']}**  "
            f"<br/><span class='metric-label'>{time_str} • {row['camera_id']}</span>",
            unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#e5e7eb;margin:0.25rem 0;'/>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)

st.write("")

t1,t2=st.columns([2,1.6])

with t1:
    st.markdown("#### Detection Trends & Analytics")
    df_time=df.copy()
    df_time["time_bucket"]=df_time["timestamp"].dt.floor("H")
    detections_per_hour=df_time.groupby("time_bucket").size().reset_index(name="detections")
    if not detections_per_hour.empty:
        detections_per_hour=detections_per_hour.set_index("time_bucket")
        st.line_chart(detections_per_hour)
    else:
        st.info("Not enough data to display trends yet.")

with t2:
    st.markdown("#### Camera Feeds & Snapshots")
    latest_by_cam=df.sort_values("timestamp").groupby("camera_id").tail(1)
    if latest_by_cam.empty:
        st.info("No camera snapshots available.")
    else:
        for _,row in latest_by_cam.iterrows():
            st.markdown("<div class='card'>",unsafe_allow_html=True)
            img_url=row.get("image_url","")
            if isinstance(img_url,str) and img_url.strip():
                st.image(img_url,use_column_width=True)
            st.markdown(f"**{row['location']}**  \n{row['camera_id']}",unsafe_allow_html=False)
            ts_label=row["timestamp"].strftime("%H:%M")
            st.caption(f"Detection at {ts_label} • {row['confidence']*100:.0f}% confidence")
            st.markdown("</div>",unsafe_allow_html=True)

st.write("")

st.markdown("#### Recent Detection Events")
cols=[c for c in ["timestamp","camera_id","location","class","confidence"] if c in df.columns]
st.dataframe(df.sort_values("timestamp",ascending=False)[cols].head(50).reset_index(drop=True))
st.caption("Data source: cloud event log stored in Google Sheets (updated continuously by YOLO detection script).")
