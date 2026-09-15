import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Overall Client-wise Details",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    "bar": "#3730a3",
    "line": "#f97316",
    "primary": "#2563eb",
    "muted": "#64748b",
    "text": "#1e293b",
    "bg_card": "#ffffff",
    "bg_app": "#eef2f7",
    "border": "#e2e8f0",
}
CHART_TEMPLATE = "plotly_white"
FONT = dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=13, color=COLORS["text"])

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {COLORS['bg_app']}; }}
    .kpi-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(15,23,42,0.06);
        text-align: left;
    }}
    .kpi-label {{
        font-size: 12px; color: {COLORS['muted']}; font-weight: 700;
        text-transform: uppercase; letter-spacing: .02em; margin-bottom: 4px;
    }}
    .kpi-value {{ font-size: 24px; font-weight: 800; color: #0f172a; }}
    .section-title {{ font-size: 20px; font-weight: 800; color: #0f172a; margin: 6px 0 10px 0; }}
    div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 10px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="padding:6px 0 18px 0;">
        <div style="font-size:28px;font-weight:800;color:#0f172a;">📊 Overall Client-wise Details</div>
        <div style="font-size:14px;color:#64748b;">Management Overview — Coder / Auditor / Client Quality performance</div>
    </div>
    """,
    unsafe_allow_html=True
)

# =====================================================
# DATA LOADING (Google Sheet via Service Account)
# =====================================================
SHEET_ID = st.secrets.get("SHEET_ID", "PASTE_YOUR_SHEET_ID_HERE")
WORKSHEET_NAME = st.secrets.get("WORKSHEET_NAME", "Sheet1")

@st.cache_data(ttl=600, show_spinner="Loading data from Google Sheet...")
def load_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)

    # Clean column names
    df.columns = df.columns.astype(str).str.strip()

    # Numeric coercion for all metric columns we rely on
    numeric_cols = [
        "Total_Chart", "Total_Pages",
        "Coder Time", "Coder Avg time per chart", "Coder Avg Time Per Page",
        "A1 Time", "A1 Avg Time Per Chart", "A1 Avg Time Per Page",
        "A2 Time", "A2 Avg Time Per Chart", "A2 Avg Time Per Page",
        "Auditor_1_Completed_Time_In_Minutes", "Auditor_2_Completed_Time_In_Minutes",
        "Coder Quality", "Auditor Quality", "Client Quality",
        "Go", "NoGo", "Audited Charts", "Less than Average", "More than Average",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Date coercion
    for col in ["Coder_Completed_Date", "A1_Completed_Date", "A2_Completed_Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df

df = load_data()

def fmt_hms(total_seconds):
    if pd.isna(total_seconds) or total_seconds is None:
        return "00:00:00"
    total_seconds = int(round(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def style_fig(fig, height=380, xaxis_title=None, yaxis_title=None):
    fig.update_layout(
        template=CHART_TEMPLATE, font=FONT,
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        margin=dict(l=10, r=10, t=45, b=10), height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
    )
    fig.update_xaxes(showgrid=False, title_text=xaxis_title, showline=True, linecolor=COLORS["border"])
    fig.update_yaxes(showgrid=True, gridcolor="#eef1f5", title_text=yaxis_title, showline=True, linecolor=COLORS["border"])
    return fig

# =====================================================
# SIDEBAR FILTERS
# =====================================================
st.sidebar.markdown("### 🔍 Filters")

def ms_filter(label, col):
    if col in df.columns:
        opts = sorted(df[col].dropna().astype(str).unique().tolist())
        return st.sidebar.multiselect(label, opts)
    return []

client_f = ms_filter("Client Name", "client_name")
project_f = ms_filter("Project Name", "project_name")
domain_f = ms_filter("Domain", "Domain")
rvc_f = ms_filter("Required Validation Code", "Required Validation Code")
coder_loc_f = ms_filter("Coder Location", "Coder_Location")
a1_loc_f = ms_filter("A1 Location", "A1_Location")
a2_loc_f = ms_filter("A2 Location", "A2_Location")
pod_f = ms_filter("Coder POD", "Coder POD")
week_f = ms_filter("Coding Week", "Coding Week")

filtered = df.copy()
filter_map = {
    "client_name": client_f, "project_name": project_f, "Domain": domain_f,
    "Required Validation Code": rvc_f, "Coder_Location": coder_loc_f,
    "A1_Location": a1_loc_f, "A2_Location": a2_loc_f, "Coder POD": pod_f,
    "Coding Week": week_f,
}
for col, vals in filter_map.items():
    if vals and col in filtered.columns:
        filtered = filtered[filtered[col].astype(str).isin(vals)]

st.sidebar.markdown("---")
st.sidebar.download_button(
    "⬇️ Download Filtered Raw Data",
    filtered.to_csv(index=False).encode("utf-8"),
    "Filtered_Data.csv", "text/csv"
)

# =====================================================
# KPI SCORECARDS
# =====================================================
total_chart = filtered.get("Total_Chart", pd.Series(dtype=float)).sum()
total_pages = filtered.get("Total_Pages", pd.Series(dtype=float)).sum()
coder_total_time = filtered.get("Coder Time", pd.Series(dtype=float)).sum()
coder_avg_time = filtered.get("Coder Time", pd.Series(dtype=float)).mean()
coder_avg_time_per_page = filtered.get("Coder Avg Time Per Page", pd.Series(dtype=float)).mean()
avg_coder_quality = filtered.get("Coder Quality", pd.Series(dtype=float)).mean()
avg_auditor_quality = filtered.get("Auditor Quality", pd.Series(dtype=float)).mean()
avg_client_quality = filtered.get("Client Quality", pd.Series(dtype=float)).mean()

kpis = [
    ("Total_Chart", f"{total_chart:,.0f}"),
    ("Total_Pages", f"{total_pages:,.0f}"),
    ("Coder Total Time Taken", fmt_hms(coder_total_time)),
    ("Coder Avg. Time Taken", fmt_hms(coder_avg_time)),
    ("Coder Avg Time Per Page", fmt_hms(coder_avg_time_per_page)),
    ("Avg. Coder Quality", f"{avg_coder_quality:.2f}" if pd.notna(avg_coder_quality) else "—"),
    ("Avg. Auditor Quality", f"{avg_auditor_quality:.2f}" if pd.notna(avg_auditor_quality) else "—"),
    ("Avg. Client Quality", f"{avg_client_quality:.2f}" if pd.notna(avg_client_quality) else "—"),
]

kpi_cols = st.columns(len(kpis))
for c, (label, value) in zip(kpi_cols, kpis):
    c.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>',
        unsafe_allow_html=True
    )

st.write("")

# =====================================================
# WEEKLY TREND & DATE-WISE TREND (combo bar + line)
# =====================================================
def combo_trend_chart(data, group_col, title):
    if group_col not in data.columns or len(data) == 0:
        st.info(f"'{group_col}' column not found or no data.")
        return
    g = data.groupby(group_col).agg(
        Total_Chart=("Total_Chart", "sum"),
        Coder_Quality=("Coder Quality", "mean")
    ).reset_index().sort_values(group_col)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=g[group_col], y=g["Total_Chart"], name="Total_Chart",
                          marker_color=COLORS["bar"], text=g["Total_Chart"].map(lambda v: f"{v:,.0f}"),
                          textposition="outside"), secondary_y=False)
    fig.add_trace(go.Scatter(x=g[group_col], y=g["Coder_Quality"], name="Coder Quality",
                              mode="lines+markers+text", line=dict(color=COLORS["line"]),
                              text=g["Coder_Quality"].round(2), textposition="top center"),
                  secondary_y=True)
    fig.update_yaxes(title_text="Total_Chart", secondary_y=False)
    fig.update_yaxes(title_text="Coder Quality", range=[0, 100], secondary_y=True)
    fig.update_layout(title=title)
    st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

st.markdown('<div class="section-title">📈 Trend</div>', unsafe_allow_html=True)
tcol1, tcol2 = st.columns(2)
with tcol1:
    combo_trend_chart(filtered, "Coding Week", "Weekly Trend")
with tcol2:
    combo_trend_chart(filtered, "Coder_Completed_Date", "Date-wise Trend")

# =====================================================
# BUBBLE CHARTS
# =====================================================
st.markdown('<div class="section-title">🔵 Quality &amp; Avg. Time Taken Metrics</div>', unsafe_allow_html=True)
bcol1, bcol2 = st.columns(2)

with bcol1:
    if "Coder" in filtered.columns and len(filtered):
        cb = filtered.groupby("Coder").agg(
            X=("Coder Avg time per chart", "mean"),
            Y=("Coder Quality", "mean"),
            Size=("Total_Chart", "sum")
        ).reset_index()
        fig = px.scatter(cb, x="X", y="Y", size="Size", hover_name="Coder",
                          title="Coder Quality & Avg. Time Taken Metrics",
                          color_discrete_sequence=[COLORS["primary"]])
        st.plotly_chart(style_fig(fig, xaxis_title="Coder Avg time per chart (sec)",
                                   yaxis_title="Coder Quality"), use_container_width=True)

with bcol2:
    if "Auditor_1" in filtered.columns and len(filtered):
        ab = filtered.groupby("Auditor_1").agg(
            X=("Auditor_1_Completed_Time_In_Minutes", "mean"),
            Y=("Auditor Quality", "mean"),
            Size=("Audited Charts", "sum")
        ).reset_index()
        fig = px.scatter(ab, x="X", y="Y", size="Size", hover_name="Auditor_1",
                          title="Auditor Quality & Avg. Time Taken Metrics",
                          color_discrete_sequence=[COLORS["primary"]])
        st.plotly_chart(style_fig(fig, xaxis_title="Auditor_1_Completed_Time_In_Minutes",
                                   yaxis_title="Auditor Quality"), use_container_width=True)

# =====================================================
# POD-WISE DETAILS TABLE
# =====================================================
st.markdown('<div class="section-title">📋 POD-wise Details</div>', unsafe_allow_html=True)
if "Coder POD" in filtered.columns and len(filtered):
    pod_table = filtered.groupby("Coder POD").agg(
        Total_Chart=("Total_Chart", "sum"),
        Coder_Avg_time_per_chart=("Coder Avg time per chart", "mean"),
        Audited_Charts=("Audited Charts", "sum"),
        Coder_Quality=("Coder Quality", "mean"),
        Auditor_Quality=("Auditor Quality", "mean"),
        Client_Quality=("Client Quality", "mean"),
    ).reset_index()
    pod_table["Coder_Avg_time_per_chart"] = pod_table["Coder_Avg_time_per_chart"].apply(fmt_hms)
    for c in ["Coder_Quality", "Auditor_Quality", "Client_Quality"]:
        pod_table[c] = pod_table[c].round(2)
    st.dataframe(pod_table, hide_index=True, use_container_width=True)
    st.download_button("⬇️ Download POD-wise Details", pod_table.to_csv(index=False),
                        "POD_wise_Details.csv", "text/csv")

st.markdown("---")

# =====================================================
# PAGE 2: TOP/BOTTOM PERFORMERS
# =====================================================
st.markdown('<div class="section-title">🏆 Top 10 / Bottom 10 Performer (Coder Quality)</div>', unsafe_allow_html=True)
if "Coder" in filtered.columns and len(filtered):
    coder_quality = filtered.groupby("Coder")["Coder Quality"].mean().reset_index()
    top10 = coder_quality.sort_values("Coder Quality", ascending=False).head(10)
    bottom10 = coder_quality.sort_values("Coder Quality", ascending=True).head(10)

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        fig = px.bar(top10.sort_values("Coder Quality"), x="Coder Quality", y="Coder",
                     orientation="h", text="Coder Quality", title="Top 10 Performer",
                     color_discrete_sequence=[COLORS["bar"]])
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
    with pcol2:
        fig = px.bar(bottom10.sort_values("Coder Quality", ascending=False), x="Coder Quality", y="Coder",
                     orientation="h", text="Coder Quality", title="Bottom 10 Performer",
                     color_discrete_sequence=[COLORS["bar"]])
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

# =====================================================
# CODER PERFORMANCE TABLE
# =====================================================
st.markdown('<div class="section-title">👤 Coder Performance</div>', unsafe_allow_html=True)
if "Coder" in filtered.columns and len(filtered):
    perf = filtered.groupby(["Coder_Location", "Coder"]).agg(
        Charts=("Total_Chart", "sum"),
        Total_Pages=("Total_Pages", "sum"),
        Codes=("Required Validation Code", pd.Series.nunique),
        Quality=("Coder Quality", "mean"),
        Total_Time_Taken=("Coder Time", "sum"),
        Avg_Time_Taken=("Coder Time", "mean"),
        NoGo=("NoGo", "sum"),
        Audited_Charts=("Audited Charts", "sum"),
        Less_than_Average=("Less than Average", "sum"),
        More_than_Average=("More than Average", "sum"),
    ).reset_index()

    perf["NoGo %"] = (perf["NoGo"] / perf["Audited_Charts"] * 100).round(2)
    perf["Audit %"] = (perf["Audited_Charts"] / perf["Charts"] * 100).round(2)
    perf["Quality"] = perf["Quality"].round(2)
    perf["Total_Time_Taken"] = perf["Total_Time_Taken"].apply(fmt_hms)
    perf["Avg_Time_Taken"] = perf["Avg_Time_Taken"].apply(fmt_hms)
    perf = perf.sort_values("Charts", ascending=False)

    st.dataframe(perf, hide_index=True, use_container_width=True)
    st.download_button("⬇️ Download Coder Performance", perf.to_csv(index=False),
                        "Coder_Performance.csv", "text/csv")

st.caption("Built with Streamlit · Overall Client-wise Details Dashboard")
