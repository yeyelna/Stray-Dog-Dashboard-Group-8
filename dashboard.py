# app.py
# Streamlit recreation of the provided Figma dashboard screenshots (layout + styling + components)

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None


# ============================================================
# PAGE CONFIG (matches wide dashboard canvas)
# ============================================================
st.set_page_config(page_title="Stray Dog Detection Dashboard", layout="wide")

# Auto-refresh (implied “real-time” behavior)
if st_autorefresh:
    st_autorefresh(interval=8000, key="dash_refresh")  # ~8s refresh similar to “live” dashboards


# ============================================================
# THEME / CSS (light mode, soft borders, chips, spacing)
# ============================================================
st.markdown(
    """
<style>
/* ---------- Page + container sizing ---------- */
html, body { background: #F6F8FC !important; }
.block-container { padding-top: 18px; padding-bottom: 22px; max-width: 1500px; }

/* Remove default Streamlit paddings that break exact spacing */
div[data-testid="stVerticalBlock"] { gap: 14px; }

/* ---------- Card primitives ---------- */
.card {
  background: #FFFFFF;
  border: 1px solid #E8EEF6;
  border-radius: 14px;
  box-shadow: 0 10px 24px rgba(16, 24, 40, 0.06);
}
.card.pad { padding: 14px 16px; }
.card.pad-lg { padding: 18px 18px; }

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #6B7280;
}

/* ---------- Small icon badge ---------- */
.icon-pill {
  width: 28px; height: 28px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center; justify-content: center;
  border: 1px solid #E8EEF6;
  background: #F7FAFF;
}

/* ---------- Table styling (Recent Detection Events) ---------- */
.table-wrap { overflow: hidden; }
.figma-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}
.figma-table thead th {
  text-align: left;
  color: #4B5563;
  font-weight: 600;
  padding: 12px 14px;
  border-bottom: 1px solid #E8EEF6;
  background: #FFFFFF;
}
.figma-table tbody td {
  padding: 14px 14px;
  border-bottom: 1px solid #EFF4FA;
  color: #111827;
  vertical-align: middle;
}
.figma-table tbody tr:last-child td { border-bottom: none; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

/* ---------- Chips ---------- */
.chip {
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  line-height: 1;
}
.chip.low { background: #EEF6FF; color: #2563EB; border-color: #D6E7FF; }
.chip.medium { background: #FFF7E6; color: #B45309; border-color: #FFE8B5; }
.chip.high { background: #FFF1F2; color: #EA580C; border-color: #FFD6D8; }
.chip.critical { background: #FFECEE; color: #E11D48; border-color: #FFC5CB; }

.chip.new { background: #FFECEE; color: #E11D48; border-color: #FFC5CB; }
.chip.ack { background: #FFF7E6; color: #B45309; border-color: #FFE8B5; }
.chip.disp { background: #EEF6FF; color: #2563EB; border-color: #D6E7FF; }

/* ---------- KPI cards row ---------- */
.kpi {
  position: relative;
  padding: 16px 18px;
  height: 92px;
}
.kpi-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.kpi-value {
  font-size: 34px;
  font-weight: 800;
  color: #111827;
  margin-top: 6px;
}
.kpi-label {
  font-size: 13px;
  color: #6B7280;
  margin-top: -2px;
}
.delta {
  font-size: 12px;
  font-weight: 700;
  border-radius: 9px;
  padding: 6px 10px;
  border: 1px solid transparent;
}
.delta.pos { background: #FFECEE; color: #E11D48; border-color: #FFC5CB; }
.delta.neg { background: #E9FBF0; color: #16A34A; border-color: #C7F2D6; }

/* ---------- Tabs (Active Alerts) ---------- */
div[role="radiogroup"] { gap: 10px !important; }
.stRadio > label { display:none !important; }
.stRadio [data-testid="stMarkdownContainer"] p { margin:0 !important; }

/* Make radio look like pill tabs */
.stRadio div[role="radiogroup"] label {
  background: #FFFFFF;
  border: 1px solid #E8EEF6;
  border-radius: 10px;
  padding: 9px 12px;
  cursor: pointer;
}
.stRadio div[role="radiogroup"] label:has(input:checked) {
  background: #2563EB;
  border-color: #2563EB;
}
.stRadio div[role="radiogroup"] label:has(input:checked) div, 
.stRadio div[role="radiogroup"] label:has(input:checked) span,
.stRadio div[role="radiogroup"] label:has(input:checked) p {
  color: #FFFFFF !important;
  font-weight: 700;
}

/* ---------- Active alert item list ---------- */
.scroll {
  height: 300px;
  overflow-y: auto;
  padding-right: 6px;
}
.alert-item {
  padding: 12px 10px;
  border-bottom: 1px solid #EFF4FA;
}
.alert-item:last-child { border-bottom: none; }
.alert-row {
  display: flex; justify-content: space-between; align-items: center;
}
.dot {
  width: 8px; height: 8px; border-radius: 999px; display: inline-block;
  margin-right: 8px; background: #EF4444;
}
.dot.med { background: #F59E0B; }
.dot.crit { background: #EF4444; }
.alert-id { font-weight: 800; color:#111827; font-size: 13px; }
.alert-main { font-size: 16px; font-weight: 800; margin-top: 6px; color:#111827; }
.alert-sub { font-size: 12px; color:#6B7280; margin-top: 2px; }

.meta {
  display: flex; gap: 8px; align-items: center;
  margin-top: 6px; color:#6B7280; font-size: 12px;
}
.meta .ic { width: 18px; display:inline-flex; justify-content:center; }

/* ---------- Camera cards grid ---------- */
.cam-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; }
.cam-card { border: 1px solid #E8EEF6; border-radius: 14px; overflow: hidden; background:#FFFFFF; }
.cam-img { width: 100%; height: 135px; object-fit: cover; display:block; }
.cam-body { padding: 10px 12px 12px; }
.cam-title { font-weight: 800; color:#111827; font-size: 14px; }
.cam-sub { color:#6B7280; font-size: 12px; margin-top: 2px; }

/* ---------- Placeholder panel (right) ---------- */
.center-empty {
  height: 356px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 10px;
  color: #94A3B8;
}
.empty-ic {
  width: 56px; height: 56px;
  border: 2px solid #D6E1F0;
  border-radius: 14px;
  display:flex; align-items:center; justify-content:center;
  background:#F7FAFF;
  font-size: 26px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# MOCK DATA (kept identical in format/values to the screenshot)
# ============================================================
now = datetime.now()
base_date = now.replace(month=1, day=14)  # matches “Jan 14” shown

recent_rows = [
    {"Timestamp": base_date.replace(hour=15, minute=50, second=55), "Detection ID": "DET-055844", "Location": "West End Avenue", "Camera": "CAM-091", "Dogs": 1, "Breed": "Small breed", "Confidence": 0.90, "Severity": "LOW", "Status": "NEW"},
    {"Timestamp": base_date.replace(hour=15, minute=48, second=29), "Detection ID": "DET-001", "Location": "Central Park, Zone A3", "Camera": "CAM-023", "Dogs": 2, "Breed": "Mixed", "Confidence": 0.95, "Severity": "HIGH", "Status": "NEW"},
    {"Timestamp": base_date.replace(hour=15, minute=45, second=29), "Detection ID": "DET-002", "Location": "Market Street, Intersection 5B", "Camera": "CAM-047", "Dogs": 1, "Breed": "Large breed", "Confidence": 0.88, "Severity": "MEDIUM", "Status": "ACKNOWLEDGED"},
    {"Timestamp": base_date.replace(hour=15, minute=40, second=29), "Detection ID": "DET-003", "Location": "Riverside Drive, Block 12", "Camera": "CAM-089", "Dogs": 3, "Breed": "Pack detected", "Confidence": 0.92, "Severity": "CRITICAL", "Status": "DISPATCHED"},
    {"Timestamp": base_date.replace(hour=15, minute=35, second=29), "Detection ID": "DET-004", "Location": "School District 4, Gate C", "Camera": "CAM-105", "Dogs": 1, "Breed": "Medium breed", "Confidence": 0.85, "Severity": "MEDIUM", "Status": "ACKNOWLEDGED"},
    {"Timestamp": base_date.replace(hour=15, minute=30, second=29), "Detection ID": "DET-005", "Location": "Industrial Area, Sector 7", "Camera": "CAM-132", "Dogs": 1, "Breed": "Small breed", "Confidence": 0.78, "Severity": "LOW", "Status": "NEW"},
]

# Chart series (24h, hourly) approximated to match the line shapes in screenshot
hours = list(range(24))
detections = [6, 8, 6, 15, 10, 13, 14, 19, 10, 13, 10, 19, 18, 18, 6, 15, 15, 11, 14, 6, 19, 13, 18, 7]
dogs =       [12, 29, 26, 27, 17,  8, 32, 24, 16, 25, 30, 13, 26, 22, 24, 24, 15, 27, 11, 16, 18, 20, 22, 16]

# KPI tiles (exact values shown)
kpi_new_alerts = 2
kpi_total_dogs = 8
kpi_high_priority = 2


# ============================================================
# HELPER: CHIP CLASS MAPPING
# ============================================================
def sev_class(sev: str) -> str:
    s = sev.strip().lower()
    if s == "low":
        return "low"
    if s == "medium":
        return "medium"
    if s == "high":
        return "high"
    return "critical"


def status_class(sta: str) -> str:
    s = sta.strip().lower()
    if s == "new":
        return "new"
    if s.startswith("ack"):
        return "ack"
    return "disp"


def fmt_ts(dt: datetime) -> str:
    # "Jan 14, 03:50:55 PM"
    return dt.strftime("%b %d, %I:%M:%S %p")


# ============================================================
# SECTION 1: Recent Detection Events (table card)
# ============================================================
st.markdown(
    """
<div class="card pad table-wrap">
  <div class="section-title">
    <span class="icon-pill">ℹ️</span>
    <span>Recent Detection Events</span>
    <span style="font-weight:600; color:#6B7280; margin-left:6px;">(Last 6 records)</span>
  </div>
  <div style="height:10px;"></div>
""",
    unsafe_allow_html=True,
)

# Build HTML table to preserve exact look (icons + chips)
table_html = """
<table class="figma-table">
  <thead>
    <tr>
      <th>Timestamp</th>
      <th>Detection ID</th>
      <th>Location</th>
      <th>Camera</th>
      <th>Dogs</th>
      <th>Breed</th>
      <th>Confidence</th>
      <th>Severity</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
"""
for r in recent_rows:
    table_html += f"""
    <tr>
      <td><span style="color:#6B7280; margin-right:10px;">🕒</span>{fmt_ts(r["Timestamp"])}</td>
      <td class="mono">{r["Detection ID"]}</td>
      <td><span style="color:#6B7280; margin-right:10px;">📍</span>{r["Location"]}</td>
      <td><span style="color:#6B7280; margin-right:10px;">📷</span><span class="mono">{r["Camera"]}</span></td>
      <td style="font-weight:800;">{r["Dogs"]}</td>
      <td style="color:#374151;">{r["Breed"]}</td>
      <td style="font-weight:900;">{int(r["Confidence"]*100)}%</td>
      <td><span class="chip {sev_class(r["Severity"])}">{r["Severity"]}</span></td>
      <td><span class="chip {status_class(r["Status"])}">{r["Status"]}</span></td>
    </tr>
    """
table_html += "</tbody></table></div>"

st.markdown(table_html, unsafe_allow_html=True)


# ============================================================
# SECTION 2: Detection Trends & Analytics (chart card)
# ============================================================
st.markdown(
    """
<div class="card pad-lg">
  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
    <div>
      <div class="section-title"><span style="color:#7C3AED;">📈</span>Detection Trends &amp; Analytics</div>
    </div>
  </div>
""",
    unsafe_allow_html=True,
)

# Figma top-right pill buttons: implement as radio (functional) but styled as pills
col_btn_spacer, col_btn = st.columns([5.6, 2.4])
with col_btn:
    view = st.radio(
        " ",
        ["24 Hours", "7 Days", "Severity"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

# Plotly chart (two series, markers, grid, left y-axis 0..32 style)
fig = go.Figure()
fig.add_trace(go.Scatter(x=hours, y=detections, mode="lines+markers", name="Detections", line=dict(color="#7B61FF", width=3), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=hours, y=dogs,       mode="lines+markers", name="Dogs",       line=dict(color="#2F80ED", width=3), marker=dict(size=7)))

fig.update_layout(
    height=330,
    margin=dict(l=24, r=24, t=20, b=18),
    paper_bgcolor="white",
    plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
    xaxis=dict(
        tickmode="array",
        tickvals=list(range(24)),
        ticktext=[f"{h:02d}:00" for h in range(24)],
        showgrid=True,
        gridcolor="#E8EEF6",
        zeroline=False,
        title=None,
    ),
    yaxis=dict(
        range=[0, 32],
        tick0=0,
        dtick=8,
        showgrid=True,
        gridcolor="#E8EEF6",
        zeroline=False,
        title=None,
    ),
)
st.plotly_chart(fig, use_container_width=True)

# Bottom stats row (Peak Hour + Avg Daily Detections)
st.markdown(
    """
<div style="display:flex; justify-content:space-between; padding: 4px 20px 4px;">
  <div style="text-align:center; width:50%;">
    <div style="color:#6B7280; font-size:12px; font-weight:600;">Peak Hour</div>
    <div style="margin-top:6px; color:#7B61FF; font-size:22px; font-weight:900;">14:00 - 16:00</div>
  </div>
  <div style="text-align:center; width:50%;">
    <div style="color:#6B7280; font-size:12px; font-weight:600;">Avg Daily Detections</div>
    <div style="margin-top:6px; color:#2563EB; font-size:22px; font-weight:900;">167</div>
  </div>
</div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SECTION 3: KPI Cards Row (3 tiles)
# ============================================================
c1, c2, c3 = st.columns(3, gap="large")

with c1:
    st.markdown(
        f"""
<div class="card kpi">
  <div class="kpi-top">
    <span class="icon-pill" style="background:#FFECEE; border-color:#FFC5CB;">⚠️</span>
    <span class="delta pos">+12%</span>
  </div>
  <div class="kpi-value">{kpi_new_alerts}</div>
  <div class="kpi-label">New Alerts</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
<div class="card kpi">
  <div class="kpi-top">
    <span class="icon-pill" style="background:#EEF6FF; border-color:#D6E7FF;">📈</span>
    <span class="delta pos">+8%</span>
  </div>
  <div class="kpi-value">{kpi_total_dogs}</div>
  <div class="kpi-label">Total Dogs Detected</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
<div class="card kpi">
  <div class="kpi-top">
    <span class="icon-pill" style="background:#FFF7E6; border-color:#FFE8B5;">⚠️</span>
    <span class="delta neg">-5%</span>
  </div>
  <div class="kpi-value">{kpi_high_priority}</div>
  <div class="kpi-label">High Priority</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# SECTION 4: Bottom 3-panels row
#   Left: Active Alerts
#   Middle: Camera Feeds & Snapshots (Gallery/Single)
#   Right: Empty detail panel (“Please choose any active alerts”)
# ============================================================
left, mid, right = st.columns([1.05, 1.55, 1.1], gap="large")


# ---------- Left: Active Alerts ----------
with left:
    st.markdown(
        """
<div class="card pad-lg">
  <div class="section-title"><span style="color:#EF4444;">❗</span>Active Alerts</div>
  <div style="height:10px;"></div>
""",
        unsafe_allow_html=True,
    )

    tab = st.radio(" ", ["All", "New", "Acknowledged", "Dispatched"], index=0, horizontal=True, label_visibility="collapsed")

    # Filter list
    def match_tab(row):
        if tab == "All":
            return True
        if tab == "New":
            return row["Status"] == "NEW"
        if tab == "Acknowledged":
            return row["Status"].startswith("ACK")
        return row["Status"] == "DISPATCHED"

    alert_list = [r for r in recent_rows if match_tab(r)]
    # In the screenshot, the list shows DET-001, DET-002, DET-003, ... (scrollable)
    st.markdown('<div class="scroll">', unsafe_allow_html=True)

    for r in alert_list:
        sev = r["Severity"]
        dot_class = "med" if sev == "MEDIUM" else ("crit" if sev == "CRITICAL" else "")
        sev_chip = sev_class(sev)
        # “2m ago / 5m ago / 10m ago” – mimic using fixed minutes from screenshot
        ago_map = {"DET-001": "2m ago", "DET-002": "5m ago", "DET-003": "10m ago"}
        ago = ago_map.get(r["Detection ID"], "—")

        st.markdown(
            f"""
<div class="alert-item">
  <div class="alert-row">
    <div><span class="dot {dot_class}"></span><span class="alert-id">{r["Detection ID"]}</span></div>
    <span class="chip {sev_chip}">{sev}</span>
  </div>
  <div class="alert-main">{r["Dogs"]} Dogs Detected</div>
  <div class="alert-sub">{r["Breed"]}</div>
  <div class="meta"><span class="ic">📍</span><span>{r["Location"]}</span></div>
  <div class="meta">
    <span class="ic">🕒</span><span>{ago}</span>
    <span style="margin-left:auto; color:#6B7280;">{int(r["Confidence"]*100)}% confidence</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)


# ---------- Middle: Camera Feeds & Snapshots ----------
with mid:
    st.markdown(
        """
<div class="card pad-lg">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div class="section-title"><span style="color:#0EA5E9;">🎥</span>Camera Feeds &amp; Snapshots</div>
  </div>
""",
        unsafe_allow_html=True,
    )

    # Figma top-right “Gallery / Single”
    m_sp, m_btn = st.columns([3.9, 2.1])
    with m_btn:
        cam_view = st.radio(" ", ["Gallery", "Single"], index=0, horizontal=True, label_visibility="collapsed")

    # Use local cropped images if available; otherwise, show neutral placeholders.
    # NOTE: This keeps the dashboard runnable even without the screenshot assets.
    img_paths = {
        "CAM-023": "/mnt/data/cam023_photo_final.png",
        "CAM-047": "/mnt/data/cam047_photo_final.png",
        "CAM-089": "/mnt/data/cam089_photo_final2.png",
        "CAM-105": "/mnt/data/cam105_photo_final2.png",
    }

    def img_tag(path: str) -> str:
        # Streamlit can render local images with st.image; for exact layout inside HTML we use st.image per card.
        return path

    cam_cards = [
        {"cam": "CAM-023", "title": "Central Park - Zone A3", "sub": "North Entrance"},
        {"cam": "CAM-047", "title": "Market Street", "sub": "Intersection 5B"},
        {"cam": "CAM-089", "title": "Riverside Drive", "sub": "Block 12"},
        {"cam": "CAM-105", "title": "School District 4", "sub": "Gate C"},
    ]

    # Build 2x2 grid like Figma
    st.markdown('<div class="cam-grid">', unsafe_allow_html=True)

    # Render each card with Streamlit image + HTML body to keep exact spacing
    for card in cam_cards:
        cam = card["cam"]
        path = img_paths.get(cam, "")
        # Card shell (HTML)
        st.markdown('<div class="cam-card">', unsafe_allow_html=True)
        if path and os.path.exists(path):
            st.image(path, use_container_width=True)
        else:
            # fallback placeholder (keeps dashboard runnable)
            st.markdown(
                """
<div style="height:135px; background:linear-gradient(135deg,#E8EEF6,#F7FAFF); display:flex; align-items:center; justify-content:center; color:#94A3B8; font-weight:800;">
No snapshot
</div>
""",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"""
<div class="cam-body">
  <div class="cam-title">{card["title"]}</div>
  <div class="cam-sub">{card["sub"]}</div>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)


# ---------- Right: Empty detail panel ----------
with right:
    st.markdown(
        """
<div class="card pad-lg">
  <div class="center-empty">
    <div class="empty-ic">🖼️</div>
    <div style="font-size:16px; font-weight:700;">Please choose any active alerts</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
