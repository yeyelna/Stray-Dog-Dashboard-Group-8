import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser
import plotly.graph_objects as go
st.set_page_config(page_title="Smart City Stray Dog Control System", layout="wide")
TZ=ZoneInfo("Asia/Kuala_Lumpur")
SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_SEC=8
DEFAULT_WINDOW="24 Hours"
st.markdown("""<style>
html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;}
.block-container{padding-top:1.0rem;padding-bottom:1.0rem;max-width:1400px;}
.card{background:#fff;border:1px solid #E6EAF0;border-radius:16px;box-shadow:0 1px 2px rgba(16,24,40,.04);padding:16px;}
.cardTitle{display:flex;align-items:center;gap:10px;font-weight:700;color:#0F172A;font-size:18px;}
.subtle{color:#64748B;font-size:13px;}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px;border:1px solid transparent;}
.pillGreen{background:#ECFDF3;color:#027A48;border-color:#ABEFC6;}
.pillYellow{background:#FFFAEB;color:#B54708;border-color:#FEDF89;}
.pillBlue{background:#EFF8FF;color:#175CD3;border-color:#B2DDFF;}
.pillGray{background:#F8FAFC;color:#334155;border-color:#E2E8F0;}
.pillRed{background:#FEF3F2;color:#B42318;border-color:#FECDCA;}
.pillOrange{background:#FFF6ED;color:#C4320A;border-color:#FEC84B;}
.kpiWrap{display:flex;justify-content:space-between;align-items:flex-start;}
.kpiLeft{display:flex;flex-direction:column;gap:8px;}
.kpiValue{font-size:34px;font-weight:800;color:#0F172A;line-height:1;}
.kpiLabel{color:#475569;font-weight:600;}
.kpiTrend{font-size:12px;font-weight:800;border-radius:10px;padding:6px 10px;display:inline-block;}
.trendUp{background:#FEF3F2;color:#B42318;}
.trendDown{background:#ECFDF3;color:#027A48;}
.alertItem{border:1px solid #EEF2F6;border-radius:14px;padding:12px;cursor:pointer;}
.alertItem:hover{border-color:#D5DCE6;background:#FBFCFE;}
.alertHeader{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.alertId{font-weight:800;color:#0F172A;}
.alertMain{font-size:18px;font-weight:800;color:#0F172A;margin-top:6px;}
.alertMeta{display:flex;flex-direction:column;gap:6px;margin-top:6px;color:#475569;font-weight:600;font-size:13px;}
.alertFooter{display:flex;justify-content:space-between;align-items:center;margin-top:8px;color:#64748B;font-size:13px;font-weight:700;}
.camGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;}
.camCard{border:1px solid #E6EAF0;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.04);}
.camImg{position:relative;height:150px;background:linear-gradient(135deg,#E2E8F0,#CBD5E1);}
.camBadges{position:absolute;top:10px;left:10px;display:flex;gap:8px;align-items:center;}
.camBadge{border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;color:#fff;}
.camOnline{background:#16A34A;}
.camRec{background:#EF4444;}
.camId{position:absolute;top:10px;right:10px;background:rgba(15,23,42,.85);color:#fff;font-weight:900;font-size:12px;border-radius:10px;padding:6px 10px;}
.camAgo{position:absolute;bottom:10px;left:10px;background:#F59E0B;color:#111827;font-weight:900;font-size:12px;border-radius:10px;padding:7px 10px;}
.camBody{padding:12px 14px;}
.camLoc{font-weight:900;color:#0F172A;}
.camSub{color:#64748B;font-weight:700;font-size:13px;}
.smallBtnRow [data-baseweb="radio"]{gap:10px;}
.smallBtnRow label{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:8px 12px;}
.smallBtnRow label:has(input:checked){background:#1D4ED8;border-color:#1D4ED8;color:#fff;}
.smallBtnRow input{display:none;}
</style>""", unsafe_allow_html=True)
def parse_ts(x):
    if pd.isna(x): 
        return pd.NaT
    s=str(x).strip()
    try:
        dt=parser.isoparse(s)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        pass
    try:
        dt=datetime.strptime(s,"%d/%m/%Y %H:%M")
        return dt.replace(tzinfo=TZ)
    except Exception:
        pass
    try:
        dt=datetime.strptime(s,"%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=TZ)
    except Exception:
        return pd.NaT
def time_ago(dt):
    if pd.isna(dt):
        return "—"
    now=datetime.now(TZ)
    diff=now-dt
    sec=max(int(diff.total_seconds()),0)
    if sec<60:
        return f"{sec}s ago"
    mins=sec//60
    if mins<60:
        return f"{mins}m ago"
    hrs=mins//60
    if hrs<24:
        return f"{hrs}h ago"
    days=hrs//24
    return f"{days}d ago"
def pill(text, kind):
    cls="pillGray"
    if kind=="green": cls="pillGreen"
    if kind=="yellow": cls="pillYellow"
    if kind=="blue": cls="pillBlue"
    if kind=="red": cls="pillRed"
    if kind=="orange": cls="pillOrange"
    return f'<span class="pill {cls}">{text}</span>'
def sev_pill(sev):
    s=str(sev).upper()
    if s=="CRITICAL": return pill("CRITICAL","red")
    if s=="HIGH": return pill("HIGH","orange")
    if s=="MEDIUM": return pill("MEDIUM","yellow")
    if s=="LOW": return pill("LOW","blue")
    return pill(s,"gray")
def status_pill(sts):
    s=str(sts).upper()
    if s=="NEW": return pill("NEW","red")
    if s=="ACKNOWLEDGED": return pill("ACKNOWLEDGED","yellow")
    if s=="DISPATCHED": return pill("DISPATCHED","blue")
    return pill(s,"gray")
@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data():
    if "PASTE_YOUR_GSHEETS" in SHEET_CSV_URL or SHEET_CSV_URL.strip()=="":
        now=datetime.now(TZ).replace(second=0, microsecond=0)
        demo=[]
        locs=["Residential Area 3","West End Avenue","Shopping District","Central Park, Zone A3","Market Street, Intersection 5B","Riverside Drive, Block 12","School District 4, Gate C","Industrial Area, Sector 7"]
        breeds=["Small breed","Mixed","Large breed","Pack detected","Medium breed"]
        sevs=["LOW","MEDIUM","HIGH","CRITICAL"]
        stats=["NEW","ACKNOWLEDGED","DISPATCHED"]
        cams=["CAM-015","CAM-026","CAM-075","CAM-016","CAM-012","CAM-023","CAM-047","CAM-089","CAM-105","CAM-132"]
        for i in range(40):
            dt=now-timedelta(minutes=i*3)
            demo.append({"timestamp":dt.isoformat(),"detection_id":f"DET-{np.random.randint(100000,999999)}","location":np.random.choice(locs),"camera_id":np.random.choice(cams),"dogs":int(np.random.choice([1,1,1,2,3])),"breed":np.random.choice(breeds),"confidence":int(np.random.randint(78,97)),"severity":np.random.choice(sevs,p=[0.35,0.25,0.30,0.10]),"status":np.random.choice(stats,p=[0.55,0.30,0.15]),"camera_state":"ONLINE","recording":np.random.choice(["REC",""],p=[0.6,0.4])})
        df=pd.DataFrame(demo)
    else:
        df=pd.read_csv(SHEET_CSV_URL)
        if "timestamp" not in df.columns:
            raise ValueError("Your data must contain a 'timestamp' column (or rename it to 'timestamp').")
    df["timestamp"]=df["timestamp"].apply(parse_ts)
    df=df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)
    if "detection_id" not in df.columns: df["detection_id"]=["DET-"+str(i+1).zfill(3) for i in range(len(df))]
    if "camera_id" not in df.columns: df["camera_id"]="CAM-000"
    if "location" not in df.columns: df["location"]="Unknown"
    if "dogs" not in df.columns: df["dogs"]=1
    if "breed" not in df.columns: df["breed"]="Unknown"
    if "confidence" not in df.columns: df["confidence"]=90
    if "severity" not in df.columns: df["severity"]="LOW"
    if "status" not in df.columns: df["status"]="NEW"
    if "camera_state" not in df.columns: df["camera_state"]="ONLINE"
    if "recording" not in df.columns: df["recording"]=""
    return df
df=load_data()
top=df.head(2000).copy()
st.markdown(f"""<div class="card" style="padding:18px 18px 14px 18px;">
<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;">
<div style="display:flex;align-items:center;gap:14px;">
<div style="width:44px;height:44px;border-radius:14px;background:#1D4ED8;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;">⚠️</div>
<div>
<div style="font-size:22px;font-weight:900;color:#0F172A;">Smart City Stray Dog Control System</div>
<div class="subtle">Real-Time AI Detection Monitoring</div>
</div>
</div>
<div style="display:flex;gap:10px;align-items:center;">
{pill("System Active","green")}
{pill(f"{(top['status'].astype(str).str.upper()=='NEW').sum()} New Alerts","yellow")}
</div>
</div>
</div>""", unsafe_allow_html=True)
leftA,leftB,leftC=st.columns(3)
window=st.session_state.get("window",DEFAULT_WINDOW)
hours=24 if window=="24 Hours" else 24*7
cut=datetime.now(TZ)-timedelta(hours=hours)
dfw=top[top["timestamp"]>=cut].copy()
new_alerts=int((dfw["status"].astype(str).str.upper()=="NEW").sum())
total_dogs=int(dfw["dogs"].fillna(0).astype(int).sum())
high_pri=int((dfw["severity"].astype(str).str.upper().isin(["HIGH","CRITICAL"]) & (dfw["status"].astype(str).str.upper()!="DISPATCHED")).sum())
def kpi_card(title,value,trend,trend_dir,icon):
    tcls="trendUp" if trend_dir=="up" else "trendDown"
    return f"""<div class="card"><div class="kpiWrap">
<div class="kpiLeft"><div style="width:42px;height:42px;border-radius:14px;background:#F1F5F9;display:flex;align-items:center;justify-content:center;font-weight:900;">{icon}</div>
<div class="kpiValue">{value}</div><div class="kpiLabel">{title}</div></div>
<div class="kpiTrend {tcls}">{trend}</div></div></div>"""
with leftA:
    st.markdown(kpi_card("New Alerts",new_alerts,"+12%","up","🚨"), unsafe_allow_html=True)
with leftB:
    st.markdown(kpi_card("Total Dogs Detected",total_dogs,"+8%","up","📈"), unsafe_allow_html=True)
with leftC:
    st.markdown(kpi_card("High Priority",high_pri,"-5%","down","⚠️"), unsafe_allow_html=True)
st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
colL,colM,colR=st.columns([1.05,1.45,1.05])
if "selected_alert" not in st.session_state:
    st.session_state["selected_alert"]=None
with colL:
    st.markdown("<div class='card'><div class='cardTitle'>⛔ Active Alerts</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='card' style='margin-top:10px;'>", unsafe_allow_html=True)
    st.markdown("<div class='smallBtnRow'>", unsafe_allow_html=True)
    tab=st.radio("alert_tab",["All","New","Acknowledged","Dispatched"],horizontal=True,label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    filt=top.copy()
    if tab!="All":
        filt=filt[filt["status"].astype(str).str.upper()==tab.upper()]
    filt=filt.sort_values("timestamp", ascending=False).head(30)
    for _,r in filt.iterrows():
        did=str(r["detection_id"])
        selected=(st.session_state["selected_alert"]==did)
        sev_html=sev_pill(r["severity"])
        item_bg="#F8FAFF" if selected else "#FFFFFF"
        item_bd="#93C5FD" if selected else "#EEF2F6"
        dogs=int(r["dogs"])
        ago=time_ago(r["timestamp"])
        conf=str(r["confidence"])
        st.markdown(f"""<div class="alertItem" style="background:{item_bg};border-color:{item_bd};" onclick="null">
<div class="alertHeader"><div class="alertId">●&nbsp;&nbsp;{did}</div><div>{sev_html}</div></div>
<div class="alertMain">{dogs} Dog{'s' if dogs!=1 else ''} Detected</div>
<div class="subtle" style="margin-top:2px;font-weight:700;">{r['breed']}</div>
<div class="alertMeta">
<div>📍 {r['location']}</div>
<div>🕒 {ago}</div>
</div>
<div class="alertFooter"><div></div><div>{conf}% confidence</div></div>
</div>""", unsafe_allow_html=True)
        if st.button(f"Select {did}", key=f"sel_{did}"):
            st.session_state["selected_alert"]=did
    st.markdown("</div>", unsafe_allow_html=True)
with colM:
    st.markdown("<div class='card'><div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'><div class='cardTitle'>📷 Camera Feeds & Snapshots</div><div style='display:flex;gap:10px;'><div class='smallBtnRow'>", unsafe_allow_html=True)
    view=st.radio("cam_view",["Gallery","Single"],horizontal=True,label_visibility="collapsed")
    st.markdown("</div></div></div></div>", unsafe_allow_html=True)
    cams=top.sort_values("timestamp", ascending=False).groupby("camera_id", as_index=False).first().head(4)
    st.markdown("<div class='card' style='margin-top:10px;'>", unsafe_allow_html=True)
    if view=="Gallery":
        st.markdown("<div class='camGrid'>", unsafe_allow_html=True)
        for _,r in cams.iterrows():
            cam=str(r["camera_id"])
            online=str(r["camera_state"]).upper()=="ONLINE"
            rec=str(r["recording"]).upper()=="REC"
            ago=time_ago(r["timestamp"])
            st.markdown(f"""<div class="camCard">
<div class="camImg">
<div class="camBadges">
<div class="camBadge camOnline">{'● ONLINE' if online else '● OFFLINE'}</div>
<div class="camBadge camRec">{'● REC' if rec else ''}</div>
</div>
<div class="camId">{cam}</div>
<div class="camAgo">📸 Detection {ago}</div>
</div>
<div class="camBody">
<div class="camLoc">{str(r['location']).split(',')[0]}</div>
<div class="camSub">{str(r['location'])[0:40]}</div>
</div>
</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        r=cams.iloc[0] if len(cams)>0 else None
        if r is None:
            st.markdown("<div class='subtle'>No camera data.</div>", unsafe_allow_html=True)
        else:
            cam=str(r["camera_id"])
            online=str(r["camera_state"]).upper()=="ONLINE"
            rec=str(r["recording"]).upper()=="REC"
            ago=time_ago(r["timestamp"])
            st.markdown(f"""<div class="camCard">
<div class="camImg" style="height:260px;">
<div class="camBadges">
<div class="camBadge camOnline">{'● ONLINE' if online else '● OFFLINE'}</div>
<div class="camBadge camRec">{'● REC' if rec else ''}</div>
</div>
<div class="camId">{cam}</div>
<div class="camAgo">📸 Detection {ago}</div>
</div>
<div class="camBody">
<div class="camLoc">{str(r['location']).split(',')[0]}</div>
<div class="camSub">{str(r['location'])[0:60]}</div>
</div>
</div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
with colR:
    st.markdown("<div class='card' style='height:100%;min-height:420px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:10px;'><div style='font-size:46px;'>🖼️</div><div style='font-weight:800;color:#64748B;'>Please choose any active alerts</div></div>", unsafe_allow_html=True)
sel=st.session_state.get("selected_alert",None)
if sel:
    pick=top[top["detection_id"].astype(str)==str(sel)].head(1)
    if len(pick)>0:
        r=pick.iloc[0]
        with colR:
    st.markdown("<div class='card' style='min-height:420px;'>", unsafe_allow_html=True)
    st.markdown(f"<div class='cardTitle'>📌 Alert Details</div><div class='subtle'>Selected: <b>{sel}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:10px;font-weight:900;font-size:20px;color:#0F172A;'>{int(r['dogs'])} Dog(s) Detected</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtle' style='margin-top:2px;font-weight:700;'>{r['breed']}</div>", unsafe_allow_html=True)
    conf_html=pill(f"{r['confidence']}% confidence","gray")
    sev_html=sev_pill(r["severity"])
    sts_html=status_pill(r["status"])
    st.markdown(f"<div style='margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;'>{sev_html}{sts_html}{conf_html}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:12px;color:#334155;font-weight:700;'>📍 {r['location']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:6px;color:#334155;font-weight:700;'>📷 {r['camera_id']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:6px;color:#334155;font-weight:700;'>🕒 {r['timestamp'].strftime('%b %d, %I:%M %p')}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
st.markdown("<div class='card'><div style='display:flex;justify-content:space-between;align-items:center;gap:10px;'><div class='cardTitle'>📈 Detection Trends & Analytics</div>", unsafe_allow_html=True)
trC1,trC2,trC3=st.columns([1,1,1])
with trC1:
    w=st.radio("window",["24 Hours","7 Days"],horizontal=True,label_visibility="collapsed")
st.session_state["window"]=w
with trC2:
    sev_filter=st.multiselect("Severity",["LOW","MEDIUM","HIGH","CRITICAL"],default=["LOW","MEDIUM","HIGH","CRITICAL"])
st.markdown("</div></div>", unsafe_allow_html=True)
hours=24 if w=="24 Hours" else 24*7
cut=datetime.now(TZ)-timedelta(hours=hours)
dft=top[(top["timestamp"]>=cut) & (top["severity"].astype(str).str.upper().isin(sev_filter))].copy()
dft["hour"]=dft["timestamp"].dt.floor("H")
agg=dft.groupby("hour", as_index=False).agg(detections=("detection_id","count"), dogs=("dogs","sum"))
if len(agg)==1:
    h=agg["hour"].iloc[0]
    agg=pd.concat([pd.DataFrame({"hour":[h-timedelta(hours=1)],"detections":[0],"dogs":[0]}),agg], ignore_index=True)
fig=go.Figure()
fig.add_trace(go.Scatter(x=agg["hour"], y=agg["detections"], mode="lines+markers", name="Detections"))
fig.add_trace(go.Scatter(x=agg["hour"], y=agg["dogs"], mode="lines+markers", name="Dogs"))
fig.update_layout(height=330, margin=dict(l=30,r=30,t=20,b=30), template="plotly_white", legend=dict(orientation="h", y=-0.25, x=0.35))
st.plotly_chart(fig, use_container_width=True)
peak_hour="—"
avg_daily=int(dft.groupby(dft["timestamp"].dt.date).size().mean()) if len(dft)>0 else 0
if len(agg)>0:
    peak_idx=int(agg["detections"].idxmax())
    ph=agg.loc[peak_idx,"hour"]
    peak_hour=f"{ph.strftime('%H:00')} - {(ph+timedelta(hours=2)).strftime('%H:00')}"
c1,c2=st.columns(2)
with c1:
    st.markdown(f"<div class='card' style='text-align:center;'><div class='subtle' style='font-weight:800;'>Peak Hour</div><div style='font-weight:900;font-size:22px;color:#7C3AED;margin-top:6px;'>{peak_hour}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='card' style='text-align:center;'><div class='subtle' style='font-weight:800;'>Avg Daily Detections</div><div style='font-weight:900;font-size:22px;color:#2563EB;margin-top:6px;'>{avg_daily}</div></div>", unsafe_allow_html=True)
st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
st.markdown("<div class='card'><div class='cardTitle'>🕒 Recent Detection Events <span class='subtle'>(Last 10 records)</span></div></div>", unsafe_allow_html=True)
show=top.sort_values("timestamp", ascending=False).head(10).copy()
show["Timestamp"]=show["timestamp"].dt.strftime("%b %d, %I:%M:%S %p")
show["Detection ID"]=show["detection_id"].astype(str)
show["Location"]=show["location"].astype(str)
show["Camera"]=show["camera_id"].astype(str)
show["Dogs"]=show["dogs"].astype(int)
show["Breed"]=show["breed"].astype(str)
show["Confidence"]=show["confidence"].astype(str)+"%"
show["Severity"]=show["severity"].astype(str).str.upper()
show["Status"]=show["status"].astype(str).str.upper()
disp=show[["Timestamp","Detection ID","Location","Camera","Dogs","Breed","Confidence","Severity","Status"]].copy()
def style_table(df_):
    def sev_bg(v):
        v=str(v).upper()
        if v=="LOW": return "background-color:#EFF8FF;color:#175CD3;font-weight:800;border-radius:10px;"
        if v=="MEDIUM": return "background-color:#FFFAEB;color:#B54708;font-weight:800;border-radius:10px;"
        if v=="HIGH": return "background-color:#FFF6ED;color:#C4320A;font-weight:800;border-radius:10px;"
        if v=="CRITICAL": return "background-color:#FEF3F2;color:#B42318;font-weight:800;border-radius:10px;"
        return "background-color:#F8FAFC;color:#334155;font-weight:800;border-radius:10px;"
    def sts_bg(v):
        v=str(v).upper()
        if v=="NEW": return "background-color:#FEF3F2;color:#B42318;font-weight:900;border-radius:10px;"
        if v=="ACKNOWLEDGED": return "background-color:#FFFAEB;color:#B54708;font-weight:900;border-radius:10px;"
        if v=="DISPATCHED": return "background-color:#EFF8FF;color:#175CD3;font-weight:900;border-radius:10px;"
        return "background-color:#F8FAFC;color:#334155;font-weight:900;border-radius:10px;"
    sty=df_.style
    sty=sty.applymap(sev_bg, subset=["Severity"])
    sty=sty.applymap(sts_bg, subset=["Status"])
    sty=sty.set_table_styles([{"selector":"th","props":[("text-align","left"),("font-weight","800"),("color","#334155"),("background","#F8FAFC"),("border-bottom","1px solid #E6EAF0")]},{"selector":"td","props":[("border-bottom","1px solid #EEF2F6"),("padding","10px 8px")]}])
    return sty
st.dataframe(disp, use_container_width=True, hide_index=True)
