# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH=True
except Exception:
    HAS_AUTOREFRESH=False
try:
    import plotly.graph_objects as go
    HAS_PLOTLY=True
except Exception:
    HAS_PLOTLY=False

st.set_page_config(page_title="Smart City Stray Dog Control System",page_icon="🐕",layout="wide")
CREAM_BG="#f7f4ef"

def inject_css():
    st.markdown(f"""
<style>
:root {{
  --cream:{CREAM_BG};
  --card:#ffffff;
  --border:rgba(15,23,42,0.08);
  --shadow:0 10px 30px rgba(15,23,42,0.08);
  --radius:18px;
  --muted:#64748b;
  --text:#0f172a;
}}
html, body, [data-testid="stAppViewContainer"], .stApp {{
  background: var(--cream) !important;
}}
[data-testid="stHeader"], [data-testid="stToolbar"] {{
  background: transparent !important;
}}
.block-container {{
  padding-top: 1.0rem;
  padding-bottom: 2rem;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 16px;
}}
.card-tight {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 12px 14px;
}}
.section-title {{
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  display:flex;
  align-items:center;
  gap:10px;
}}
.section-sub {{
  color: var(--muted);
  font-size: 13px;
  margin-top: 2px;
}}
.kpi-wrap {{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:12px;
}}
.kpi-ico {{
  width:34px;height:34px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;
  border:1px solid var(--border);
}}
.kpi-label {{
  color: var(--muted);
  font-size: 13px;
  margin-top: 2px;
}}
.kpi-value {{
  font-size: 28px;
  font-weight: 800;
  color: var(--text);
  line-height: 1.0;
  margin-top: 6px;
}}
.kpi-delta {{
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
}}
.badge {{
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  display:inline-block;
  border: 1px solid var(--border);
}}
.badge-low {{
  color:#1d4ed8;background:rgba(59,130,246,0.10);
}}
.badge-med {{
  color:#a16207;background:rgba(234,179,8,0.14);
}}
.badge-high {{
  color:#c2410c;background:rgba(249,115,22,0.14);
}}
.badge-crit {{
  color:#b91c1c;background:rgba(239,68,68,0.14);
}}
.badge-new {{
  color:#b91c1c;background:rgba(239,68,68,0.14);
}}
.badge-ack {{
  color:#a16207;background:rgba(234,179,8,0.14);
}}
.badge-dis {{
  color:#1d4ed8;background:rgba(59,130,246,0.12);
}}
.small-muted {{
  color: var(--muted);
  font-size: 12px;
}}
.hr {{
  height:1px;background:rgba(15,23,42,0.06);margin:10px 0 10px 0;
}}
.alert-item {{
  border: 1px solid rgba(15,23,42,0.08);
  border-radius: 16px;
  padding: 12px 12px;
  background: #fff;
}}
.alert-top {{
  display:flex;justify-content:space-between;align-items:center;
}}
.alert-id {{
  font-weight:800;color:var(--text);font-size:13px;
}}
.alert-main {{
  font-weight:800;color:var(--text);font-size:16px;margin-top:8px;
}}
.alert-meta {{
  color:var(--muted);font-size:13px;margin-top:2px;
}}
.pill {{
  font-size:12px;font-weight:800;padding:6px 10px;border-radius:999px;border:1px solid var(--border);
}}
.pill-on {{
  color:#15803d;background:rgba(34,197,94,0.14);
}}
.pill-rec {{
  color:#b91c1c;background:rgba(239,68,68,0.14);
}}
.cam-tag {{
  font-size:12px;font-weight:800;padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,0.35);
  background:rgba(15,23,42,0.65);color:#fff;
}}
.overlay {{
  position:absolute;left:10px;top:10px;display:flex;gap:8px;align-items:center;
}}
.overlay2 {{
  position:absolute;right:10px;top:10px;
}}
.img-wrap {{
  position:relative;border-radius:16px;overflow:hidden;border:1px solid rgba(15,23,42,0.08);
}}
.img-bot {{
  position:absolute;left:10px;bottom:10px;
}}
.det-pill {{
  font-size:12px;font-weight:800;padding:7px 10px;border-radius:999px;border:1px solid rgba(15,23,42,0.10);
  background:rgba(245,158,11,0.16);color:#92400e;
}}
</style>
""",unsafe_allow_html=True)

def parse_ts(x):
    if pd.isna(x):
        return pd.NaT
    s=str(x).strip()
    for fmt in ["%d/%m/%Y %H:%M","%d/%m/%Y %I:%M %p","%b %d, %I:%M:%S %p","%b %d, %I:%M %p"]:
        try:
            return datetime.strptime(s,fmt)
        except Exception:
            pass
    try:
        s2=s.replace("Z","+00:00")
        dt=datetime.fromisoformat(s2)
        if dt.tzinfo is not None:
            dt=dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
        return dt
    except Exception:
        return pd.NaT

def severity_from(dogs,conf):
    if dogs>=3:
        return "CRITICAL"
    if dogs==2 and conf>=0.90:
        return "HIGH"
    if conf>=0.86:
        return "MEDIUM"
    return "LOW"

def status_from(sev,minutes_ago):
    if sev in ["CRITICAL","HIGH"] and minutes_ago<=12:
        return "NEW"
    if minutes_ago<=30:
        return "ACKNOWLEDGED"
    return "DISPATCHED"

def make_demo_events(now):
    rows=[]
    seed=[
        ("DET-055844","West End Avenue","CAM-091",1,"Small breed",0.90,"LOW","NEW"),
        ("DET-001","Central Park, Zone A3","CAM-023",2,"Mixed",0.95,"HIGH","NEW"),
        ("DET-002","Market Street, Intersection 5B","CAM-047",1,"Large breed",0.88,"MEDIUM","ACKNOWLEDGED"),
        ("DET-003","Riverside Drive, Block 12","CAM-089",3,"Pack detected",0.92,"CRITICAL","DISPATCHED"),
        ("DET-004","School District 4, Gate C","CAM-105",1,"Medium breed",0.85,"MEDIUM","ACKNOWLEDGED"),
        ("DET-005","Industrial Area, Sector 7","CAM-132",1,"Small breed",0.78,"LOW","NEW"),
    ]
    mins=[0,2,5,10,15,20]
    for (det,loc,cam,dogs,breed,conf,sev,status),m in zip(seed,mins):
        ts=now-timedelta(minutes=m)
        rows.append({"timestamp":ts,"detection_id":det,"location":loc,"camera":cam,"dogs":dogs,"breed":breed,"confidence":conf,"severity":sev,"status":status})
    return pd.DataFrame(rows).sort_values("timestamp",ascending=False)

def make_demo_timeseries(now):
    hours=pd.date_range(now.replace(minute=0,second=0,microsecond=0)-timedelta(hours=23),periods=24,freq="H")
    detections=np.clip(np.round(10+6*np.sin(np.linspace(0,3*np.pi,24))+np.random.normal(0,2,24)),0,None).astype(int)
    dogs=np.clip(detections+np.random.randint(-3,6,size=24),0,None).astype(int)
    df=pd.DataFrame({"time":hours,"detections":detections,"dogs":dogs})
    return df

def kpi_card(title,value,delta,icon,accent="neutral"):
    if accent=="danger":
        dstyle="color:#b91c1c;background:rgba(239,68,68,0.14);"
    elif accent=="warn":
        dstyle="color:#a16207;background:rgba(234,179,8,0.14);"
    elif accent=="good":
        dstyle="color:#15803d;background:rgba(34,197,94,0.14);"
    else:
        dstyle="color:#0f172a;background:rgba(15,23,42,0.06);"
    st.markdown(f"""
<div class="card-tight">
  <div class="kpi-wrap">
    <div>
      <div class="kpi-ico">{icon}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{title}</div>
    </div>
    <div class="kpi-delta" style="{dstyle}">{delta}</div>
  </div>
</div>
""",unsafe_allow_html=True)

def badge(label,kind):
    cls="badge"
    if kind=="LOW": cls+=" badge-low"
    if kind=="MEDIUM": cls+=" badge-med"
    if kind=="HIGH": cls+=" badge-high"
    if kind=="CRITICAL": cls+=" badge-crit"
    if kind=="NEW": cls+=" badge-new"
    if kind=="ACKNOWLEDGED": cls+=" badge-ack"
    if kind=="DISPATCHED": cls+=" badge-dis"
    return f'<span class="{cls}">{label}</span>'

def human_minutes_ago(ts,now):
    m=int(max(0,round((now-ts).total_seconds()/60)))
    if m==0: return "just now"
    if m==1: return "1m ago"
    return f"{m}m ago"

def plot_line(ts_df):
    if HAS_PLOTLY:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=ts_df["time"],y=ts_df["detections"],mode="lines+markers",name="Detections"))
        fig.add_trace(go.Scatter(x=ts_df["time"],y=ts_df["dogs"],mode="lines+markers",name="Dogs"))
        fig.update_layout(height=360,margin=dict(l=10,r=10,t=10,b=10),legend=dict(orientation="h",yanchor="bottom",y=-0.25,xanchor="center",x=0.5))
        fig.update_xaxes(showgrid=True,gridcolor="rgba(15,23,42,0.08)")
        fig.update_yaxes(showgrid=True,gridcolor="rgba(15,23,42,0.08)")
        st.plotly_chart(fig,use_container_width=True)
    else:
        st.line_chart(ts_df.set_index("time")[["detections","dogs"]],height=360)

def load_events():
    url=st.secrets.get("EVENTS_CSV_URL","").strip() if hasattr(st,"secrets") else ""
    if url:
        try:
            df=pd.read_csv(url)
            if "timestamp" in df.columns:
                df["timestamp"]=df["timestamp"].apply(parse_ts)
            for col in ["detection_id","location","camera","dogs","breed","confidence","severity","status"]:
                if col not in df.columns:
                    df[col]=np.nan
            df=df.dropna(subset=["timestamp"]).sort_values("timestamp",ascending=False)
            df["dogs"]=pd.to_numeric(df["dogs"],errors="coerce").fillna(1).astype(int)
            df["confidence"]=pd.to_numeric(df["confidence"],errors="coerce").fillna(0.85).astype(float)
            df["severity"]=df.apply(lambda r: r["severity"] if pd.notna(r["severity"]) else severity_from(int(r["dogs"]),float(r["confidence"])),axis=1)
            now=datetime.now()
            df["status"]=df.apply(lambda r: r["status"] if pd.notna(r["status"]) else status_from(r["severity"],int((now-r["timestamp"]).total_seconds()/60)),axis=1)
            return df
        except Exception:
            pass
    now=datetime.now()
    return make_demo_events(now)

def camera_image_for(camera):
    cam_map={
        "CAM-023":"https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=80",
        "CAM-047":"https://images.unsplash.com/photo-1526481280695-3c687fd643ed?auto=format&fit=crop&w=1200&q=80",
        "CAM-089":"https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
        "CAM-105":"https://images.unsplash.com/photo-1581092919535-7146f7f403b1?auto=format&fit=crop&w=1200&q=80",
        "CAM-091":"https://images.unsplash.com/photo-1530281700549-e82e7bf110d6?auto=format&fit=crop&w=1200&q=80",
        "CAM-132":"https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?auto=format&fit=crop&w=1200&q=80",
    }
    return cam_map.get(camera,"https://picsum.photos/1200/700")

inject_css()
if HAS_AUTOREFRESH:
    st_autorefresh(interval=8000,key="auto_refresh")

st.markdown('<div class="section-title">🐕 Smart City Stray Dog Control System</div><div class="section-sub">Live monitoring • alerts • response coordination</div>',unsafe_allow_html=True)

events=load_events().copy()
now=datetime.now()

colk1,colk2,colk3=st.columns([1,1,1],gap="large")
new_alerts=int((events["status"]=="NEW").sum())
total_dogs=int(events["dogs"].sum())
high_priority=int(events["severity"].isin(["HIGH","CRITICAL"]).sum())
with colk1:
    kpi_card("New Alerts",new_alerts,"+12%","⚠️","danger" if new_alerts>0 else "neutral")
with colk2:
    kpi_card("Total Dogs Detected",total_dogs,"+8%","📈","neutral")
with colk3:
    kpi_card("High Priority",high_priority,"-5%","⛔","warn" if high_priority>0 else "good")

st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)

c1,c2=st.columns([1.05,2.0],gap="large")
with c1:
    st.markdown('<div class="card"><div class="section-title">ℹ️ Recent Detection Events <span class="small-muted">(Last 6 records)</span></div><div class="hr"></div>',unsafe_allow_html=True)
    show=events.head(6).copy()
    show["Timestamp"]=show["timestamp"].dt.strftime("%b %d, %I:%M:%S %p")
    show["Detection ID"]=show["detection_id"]
    show["Location"]=show["location"]
    show["Camera"]=show["camera"]
    show["Dogs"]=show["dogs"].astype(int)
    show["Breed"]=show["breed"].fillna("Unknown")
    show["Confidence"]=(show["confidence"]*100).round(0).astype(int).astype(str)+"%"
    show["Severity"]=show["severity"].apply(lambda x: x.title())
    show["Status"]=show["status"].apply(lambda x: x.title())
    st.dataframe(show[["Timestamp","Detection ID","Location","Camera","Dogs","Breed","Confidence","Severity","Status"]],use_container_width=True,hide_index=True)
    st.markdown("</div>",unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="kpi-wrap"><div><div class="section-title">📈 Detection Trends & Analytics</div><div class="section-sub">Detections and response patterns</div></div>',unsafe_allow_html=True)
    topa,topb,topc=st.columns([1,1,1],gap="small")
    with topa:
        view=st.segmented_control("Range",options=["24 Hours","7 Days"],default="24 Hours",label_visibility="collapsed")
    with topb:
        metric_mode=st.segmented_control("Metric",options=["Detections","Dogs"],default="Detections",label_visibility="collapsed")
    with topc:
        sev_filter=st.segmented_control("Severity",options=["All","LOW","MEDIUM","HIGH","CRITICAL"],default="All",label_visibility="collapsed")
    st.markdown("</div><div class='hr'></div>",unsafe_allow_html=True)
    ts=make_demo_timeseries(now)
    if view=="7 Days":
        days=pd.date_range(now.date()-timedelta(days=6),periods=7,freq="D")
        detections=np.clip(np.round(140+20*np.sin(np.linspace(0,2*np.pi,7))+np.random.normal(0,10,7)),0,None).astype(int)
        dogs=np.clip(detections+np.random.randint(-20,35,size=7),0,None).astype(int)
        ts=pd.DataFrame({"time":days,"detections":detections,"dogs":dogs})
    if metric_mode=="Detections":
        plot_line(ts[["time","detections","dogs"]])
    else:
        plot_line(ts[["time","detections","dogs"]])
    peak_text="14:00 - 16:00" if view=="24 Hours" else "Fri - Sun"
    avg_daily=int(ts["detections"].mean()) if view=="7 Days" else int(ts["detections"].sum()/1)
    a1,a2=st.columns([1,1])
    with a1:
        st.markdown(f"<div class='small-muted' style='text-align:center;'>Peak Window</div><div style='text-align:center;font-size:22px;font-weight:900;color:#6d28d9;margin-top:4px;'>{peak_text}</div>",unsafe_allow_html=True)
    with a2:
        st.markdown(f"<div class='small-muted' style='text-align:center;'>Avg {( 'Daily' if view=='7 Days' else '24h' )} Detections</div><div style='text-align:center;font-size:22px;font-weight:900;color:#2563eb;margin-top:4px;'>{avg_daily}</div>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)

st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)

left,mid,right=st.columns([1.05,2.0,1.05],gap="large")
if "selected_det" not in st.session_state:
    st.session_state.selected_det=None

with left:
    st.markdown('<div class="card"><div class="section-title">❗ Active Alerts</div><div class="section-sub">Select an alert to view camera & details</div><div class="hr"></div>',unsafe_allow_html=True)
    t_all,t_new,t_ack,t_dis=st.tabs(["All","New","Acknowledged","Dispatched"])
    def alert_list(df):
        if df.empty:
            st.info("No alerts in this view.")
            return
        for _,r in df.iterrows():
            sev=r["severity"]
            stat=r["status"]
            conf=int(round(float(r["confidence"])*100))
            mins=human_minutes_ago(r["timestamp"],now)
            sev_badge=badge(sev,sev)
            stat_badge=badge(stat,stat)
            st.markdown(f"""
<div class="alert-item">
  <div class="alert-top">
    <div class="alert-id">{r["detection_id"]}</div>
    <div style="display:flex;gap:6px;align-items:center;">{sev_badge}{stat_badge}</div>
  </div>
  <div class="alert-main">{int(r["dogs"])} Dogs Detected</div>
  <div class="alert-meta">{r["breed"]}</div>
  <div class="alert-meta">📍 {r["location"]}</div>
  <div class="alert-meta">🕒 {mins} • {conf}% confidence</div>
</div>
""",unsafe_allow_html=True)
            btn_key=f"sel_{r['detection_id']}"
            if st.button("View",key=btn_key,use_container_width=True):
                st.session_state.selected_det=r["detection_id"]
                st.session_state.selected_cam=r["camera"]
                st.session_state.selected_loc=r["location"]
                st.session_state.selected_sev=r["severity"]
                st.session_state.selected_stat=r["status"]
                st.session_state.selected_dogs=int(r["dogs"])
                st.session_state.selected_conf=conf
                st.session_state.selected_breed=r["breed"]
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
    with t_all:
        df=events.copy()
        if sev_filter!="All":
            df=df[df["severity"]==sev_filter]
        alert_list(df.head(12))
    with t_new:
        df=events[events["status"]=="NEW"].copy()
        if sev_filter!="All":
            df=df[df["severity"]==sev_filter]
        alert_list(df.head(12))
    with t_ack:
        df=events[events["status"]=="ACKNOWLEDGED"].copy()
        if sev_filter!="All":
            df=df[df["severity"]==sev_filter]
        alert_list(df.head(12))
    with t_dis:
        df=events[events["status"]=="DISPATCHED"].copy()
        if sev_filter!="All":
            df=df[df["severity"]==sev_filter]
        alert_list(df.head(12))
    st.markdown("</div>",unsafe_allow_html=True)

with mid:
    st.markdown('<div class="card"><div class="kpi-wrap"><div><div class="section-title">📷 Camera Feeds & Snapshots</div><div class="section-sub">Gallery view • select an alert to open single view</div></div>',unsafe_allow_html=True)
    v1,v2=st.columns([1,1],gap="small")
    with v1:
        view_mode=st.segmented_control("View",options=["Gallery","Single"],default="Gallery",label_visibility="collapsed")
    with v2:
        st.write("")
    st.markdown("</div><div class='hr'></div>",unsafe_allow_html=True)
    top4=events.head(4).copy()
    if view_mode=="Gallery":
        g1,g2=st.columns(2,gap="large")
        cards=[top4.iloc[0],top4.iloc[1],top4.iloc[2],top4.iloc[3]] if len(top4)>=4 else [r for _,r in top4.iterrows()]
        for i,r in enumerate(cards):
            target=g1 if i%2==0 else g2
            with target:
                img=camera_image_for(r["camera"])
                mins=human_minutes_ago(r["timestamp"],now)
                st.markdown('<div class="img-wrap">',unsafe_allow_html=True)
                st.image(img,use_container_width=True)
                st.markdown(f"""
<div class="overlay">
  <span class="pill pill-on">● ONLINE</span>
  <span class="pill pill-rec">● REC</span>
</div>
<div class="overlay2">
  <span class="cam-tag">{r["camera"]}</span>
</div>
<div class="img-bot">
  <span class="det-pill">📸 Detection {mins}</span>
</div>
""",unsafe_allow_html=True)
                st.markdown("</div>",unsafe_allow_html=True)
                st.markdown(f"<div style='font-weight:900;font-size:16px;margin-top:10px;color:#0f172a;'>{r['location'].split(',')[0]}</div>",unsafe_allow_html=True)
                st.markdown(f"<div class='small-muted' style='margin-top:-2px;'>{r['location']}</div>",unsafe_allow_html=True)
                if st.button("Open",key=f"open_{r['detection_id']}",use_container_width=True):
                    st.session_state.selected_det=r["detection_id"]
                    st.session_state.selected_cam=r["camera"]
                    st.session_state.selected_loc=r["location"]
                    st.session_state.selected_sev=r["severity"]
                    st.session_state.selected_stat=r["status"]
                    st.session_state.selected_dogs=int(r["dogs"])
                    st.session_state.selected_conf=int(round(float(r["confidence"])*100))
                    st.session_state.selected_breed=r["breed"]
                st.markdown("<div style='height:14px'></div>",unsafe_allow_html=True)
    else:
        if st.session_state.selected_det is None:
            st.info("Choose any active alerts to open the single camera view.")
        else:
            cam=st.session_state.selected_cam
            img=camera_image_for(cam)
            st.markdown('<div class="img-wrap">',unsafe_allow_html=True)
            st.image(img,use_container_width=True)
            st.markdown(f"""
<div class="overlay">
  <span class="pill pill-on">● ONLINE</span>
  <span class="pill pill-rec">● REC</span>
</div>
<div class="overlay2">
  <span class="cam-tag">{cam}</span>
</div>
""",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
            st.markdown(f"<div style='font-weight:900;font-size:18px;margin-top:12px;color:#0f172a;'>Alert {st.session_state.selected_det}</div>",unsafe_allow_html=True)
            st.markdown(f"<div class='small-muted'>📍 {st.session_state.selected_loc}</div>",unsafe_allow_html=True)
            s1,s2,s3,s4=st.columns([1,1,1,1],gap="small")
            with s1:
                st.markdown(f"<div class='card-tight'><div class='small-muted'>Dogs</div><div style='font-size:20px;font-weight:900;color:#0f172a;margin-top:4px;'>{st.session_state.selected_dogs}</div></div>",unsafe_allow_html=True)
            with s2:
                st.markdown(f"<div class='card-tight'><div class='small-muted'>Breed</div><div style='font-size:14px;font-weight:900;color:#0f172a;margin-top:6px;'>{st.session_state.selected_breed}</div></div>",unsafe_allow_html=True)
            with s3:
                st.markdown(f"<div class='card-tight'><div class='small-muted'>Confidence</div><div style='font-size:20px;font-weight:900;color:#0f172a;margin-top:4px;'>{st.session_state.selected_conf}%</div></div>",unsafe_allow_html=True)
            with s4:
                st.markdown(f"<div class='card-tight'><div class='small-muted'>Severity</div><div style='font-size:14px;font-weight:900;color:#0f172a;margin-top:6px;'>{st.session_state.selected_sev}</div></div>",unsafe_allow_html=True)
            b1,b2,b3=st.columns([1,1,1],gap="small")
            with b1:
                if st.button("Acknowledge",use_container_width=True):
                    events.loc[events["detection_id"]==st.session_state.selected_det,"status"]="ACKNOWLEDGED"
                    st.toast("Acknowledged")
            with b2:
                if st.button("Dispatch Team",use_container_width=True):
                    events.loc[events["detection_id"]==st.session_state.selected_det,"status"]="DISPATCHED"
                    st.toast("Dispatched")
            with b3:
                if st.button("Close View",use_container_width=True):
                    st.session_state.selected_det=None
                    st.toast("Closed")

with right:
    st.markdown('<div class="card"><div class="section-title">🧾 Alert Details</div><div class="section-sub">Operational response notes</div><div class="hr"></div>',unsafe_allow_html=True)
    if st.session_state.selected_det is None:
        st.info("Please choose any active alerts.")
    else:
        st.markdown(f"<div style='font-weight:900;font-size:16px;color:#0f172a;'>Detection ID</div><div class='small-muted'>{st.session_state.selected_det}</div>",unsafe_allow_html=True)
        st.markdown("<div class='hr'></div>",unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:900;font-size:16px;color:#0f172a;'>Status</div><div style='margin-top:6px;'>{badge(st.session_state.selected_stat,st.session_state.selected_stat)}</div>",unsafe_allow_html=True)
        st.markdown("<div class='hr'></div>",unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:900;font-size:16px;color:#0f172a;'>Recommended Action</div>",unsafe_allow_html=True)
        sev=st.session_state.selected_sev
        if sev=="CRITICAL":
            st.markdown("<div class='small-muted'>Dispatch municipal team immediately, prioritize public safety zones (schools/parks), and initiate capture/relocation protocol.</div>",unsafe_allow_html=True)
        elif sev=="HIGH":
            st.markdown("<div class='small-muted'>Acknowledge within 10 minutes and dispatch team to monitor/redirect pack movement near crowded areas.</div>",unsafe_allow_html=True)
        elif sev=="MEDIUM":
            st.markdown("<div class='small-muted'>Acknowledge and schedule patrol. Log recurring hotspots for targeted mitigation.</div>",unsafe_allow_html=True)
        else:
            st.markdown("<div class='small-muted'>Log event and monitor. Escalate if repeated detections occur within 30 minutes.</div>",unsafe_allow_html=True)
        st.markdown("<div class='hr'></div>",unsafe_allow_html=True)
        note=st.text_area("Operator Notes",value=st.session_state.get("op_note",""),height=140)
        st.session_state.op_note=note
        if st.button("Save Notes",use_container_width=True):
            st.toast("Notes saved")
    st.markdown("</div>",unsafe_allow_html=True)
