import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Smart City Stray Dog Control System", layout="wide")
TZ = ZoneInfo("Asia/Kuala_Lumpur")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSxyGtEAyftAfaY3M3H_sMvnA6oYcTsVjxMLVznP7SXvGA4rTXfrvzESYgSND7Z6o9qTrD-y0QRyvPo/pub?gid=0&single=true&output=csv"
REFRESH_SEC = 8
DEFAULT_WINDOW = "24 Hours"

# =========================
# THEME / CSS (LIGHT MODE)
# =========================
st.markdown(
    """<style>
html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;}
.stApp{background:#f7f4ef;}
.block-container{padding-top:1.0rem;padding-bottom:1.0rem;max-width:1400px;background:transparent;}
.card{background:#fffefc;border:1px solid #E6EAF0;border-radius:16px;box-shadow:0 1px 2px rgba(16,24,40,.04);padding:16px;}
.cardTitle{display:flex;align-items:center;gap:10px;font-weight:800;color:#0F172A;font-size:18px;}
.subtle{color:#64748B;font-size:13px;}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:6px 10px;font-weight:800;font-size:12px;border:1px solid transparent;}
.pillGreen{background:#ECFDF3;color:#027A48;border-color:#ABEFC6;}
.pillYellow{background:#FFFAEB;color:#B54708;border-color:#FEDF89;}
.pillBlue{background:#EFF8FF;color:#175CD3;border-color:#B2DDFF;}
.pillGray{background:#F8FAFC;color:#334155;border-color:#E2E8F0;}
.pillRed{background:#FEF3F2;color:#B42318;border-color:#FECDCA;}
.pillOrange{background:#FFF6ED;color:#C4320A;border-color:#FEC84B;}
.kpiWrap{display:flex;justify-content:space-between;align-items:flex-start;}
.kpiLeft{display:flex;flex-direction:column;gap:8px;}
.kpiValue{font-size:34px;font-weight:900;color:#0F172A;line-height:1;}
.kpiLabel{color:#475569;font-weight:700;}
.kpiTrend{font-size:12px;font-weight:900;border-radius:10px;padding:6px 10px;display:inline-block;}
.trendUp{background:#FEF3F2;color:#B42318;}
.trendDown{background:#ECFDF3;color:#027A48;}
.camGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;}
.camCard{border:1px solid #E6EAF0;border-radius:16px;overflow:hidden;background:#fffefc;box-shadow:0 1px 2px rgba(16,24,40,.04);}
.camImg{position:relative;height:150px;background:linear-gradient(135deg,#E2E8F0,#CBD5E1);}
.camBadges{position:absolute;top:10px;left:10px;display:flex;gap:8px;align-items:center;}
.camBadge{border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;color:#fff;}
.camOnline{background:#16A34A;}
.camRec{background:#EF4444;}
.camId{position:absolute;top:10px;right:10px;background:rgba(15,23,42,.85);color:#fff;font-weight:900;font-size:12px;border-radius:10px;padding:6px 10px;}
.camAgo{position:absolute;bottom:10px;left:10px;background:#F59E0B;color:#111827;font-weight:900;font-size:12px;border-radius:10px;padding:7px 10px;}
.camBody{padding:12px 14px;background:#fffefc;}
.camLoc{font-weight:900;color:#0F172A;}
.camSub{color:#64748B;font-weight:800;font-size:13px;}

/* Light buttons */
.stButton>button{
  background:#fffefc !important;
  color:#0F172A !important;
  border:1px solid #E6EAF0 !important;
  border-radius:12px !important;
  padding:10px 12px !important;
  font-weight:900 !important;
  width:100% !important;
}
.stButton>button:hover{background:#FFFDFA !important;border-color:#D5DCE6 !important;}
</style>""",
    unsafe_allow_html=True,
)

# =========================
# HELPERS
# =========================
def parse_ts(x):
    if pd.isna(x):
        return pd.NaT
    s = str(x).strip()
    try:
        dt = parser.isoparse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        pass
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=TZ)
        except Exception:
            continue
    return pd.NaT


def time_ago(dt):
    if pd.isna(dt):
        return "—"
    now = datetime.now(TZ)
    diff = now - dt
    sec = max(int(diff.total_seconds()), 0)
    if sec < 60:
        return f"{sec}s ago"
    mins = sec // 60
    if mins < 60:
        return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}h ago"
    days = hrs // 24
    return f"{days}d ago"


def pill(text, kind):
    cls = "pillGray"
    if kind == "green":
        cls = "pillGreen"
    if kind == "yellow":
        cls = "pillYellow"
    if kind == "blue":
        cls = "pillBlue"
    if kind == "red":
        cls = "pillRed"
    if kind == "orange":
        cls = "pillOrange"
    return f'<span class="pill {cls}">{text}</span>'


def sev_pill(sev):
    s = str(sev).upper()
    if s == "CRITICAL":
        return pill("CRITICAL", "red")
    if s == "HIGH":
        return pill("HIGH", "orange")
    if s == "MEDIUM":
        return pill("MEDIUM", "yellow")
    if s == "LOW":
        return pill("LOW", "blue")
    return pill(s, "gray")


def status_pill(sts):
    s = str(sts).upper()
    if s == "NEW":
        return pill("NEW", "red")
    if s == "ACKNOWLEDGED":
        return pill("ACKNOWLEDGED", "yellow")
    if s == "DISPATCHED":
        return pill("DISPATCHED", "blue")
    return pill(s, "gray")


def conf_text(v):
    try:
        x = float(v)
        if x <= 1:
            x *= 100
        x = max(0, min(100, x))
        return f"{int(round(x))}% confidence"
    except Exception:
        return "—"


def segmented(label, options, default):
    if hasattr(st, "segmented_control"):
        return st.segmented_control(label, options=options, default=default, label_visibility="collapsed")
    return st.radio(label, options, horizontal=True, label_visibility="collapsed")


# =========================
# DATA
# =========================
@st.cache_data(ttl=REFRESH_SEC, show_spinner=False)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
    except Exception:
        df = pd.DataFrame()

    # fallback demo if sheet not accessible / wrong cols
    if df.empty or "timestamp" not in df.columns:
        now = datetime.now(TZ).replace(second=0, microsecond=0)
        demo = []
        locs = [
            "Residential Area 3",
            "West End Avenue",
            "Shopping District",
            "Central Park, Zone A3",
            "Market Street, Intersection 5B",
            "Riverside Drive, Block 12",
            "School District 4, Gate C",
            "Industrial Area, Sector 7",
        ]
        breeds = ["Small breed", "Mixed", "Large breed", "Pack detected", "Medium breed"]
        sevs = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        stats = ["NEW", "ACKNOWLEDGED", "DISPATCHED"]
        cams = ["CAM-015", "CAM-026", "CAM-075", "CAM-016", "CAM-012", "CAM-023", "CAM-047", "CAM-089", "CAM-105", "CAM-132"]
        for i in range(60):
            dt = now - timedelta(minutes=i * 2)
            demo.append(
                {
                    "timestamp": dt.isoformat(),
                    "detection_id": f"DET-{str(i+1).zfill(3)}",
                    "location": np.random.choice(locs),
                    "camera_id": np.random.choice(cams),
                    "dogs": int(np.random.choice([1, 1, 1, 2, 3])),
                    "breed": np.random.choice(breeds),
                    "confidence": int(np.random.randint(78, 97)),
                    "severity": np.random.choice(sevs, p=[0.35, 0.25, 0.30, 0.10]),
                    "status": np.random.choice(stats, p=[0.55, 0.30, 0.15]),
                    "camera_state": "ONLINE",
                    "recording": np.random.choice(["REC", ""], p=[0.6, 0.4]),
                }
            )
        df = pd.DataFrame(demo)

    # normalize / validate
    df["timestamp"] = df["timestamp"].apply(parse_ts)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=False)

    if "detection_id" not in df.columns:
        df["detection_id"] = [f"DET-{str(i+1).zfill(3)}" for i in range(len(df))]
    if "camera_id" not in df.columns:
        df["camera_id"] = "CAM-000"
    if "location" not in df.columns:
        df["location"] = "Unknown"
    if "dogs" not in df.columns:
        df["dogs"] = 1
    if "breed" not in df.columns:
        df["breed"] = "Unknown"
    if "confidence" not in df.columns:
        df["confidence"] = 90
    if "severity" not in df.columns:
        df["severity"] = "LOW"
    if "status" not in df.columns:
        df["stat]()
