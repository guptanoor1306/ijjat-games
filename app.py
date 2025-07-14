import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1) Load credentials & sheet ID from secrets
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# 2) Authorize & fetch into DataFrame (cached for 10 minutes)
@st.cache_data(ttl=600)
def load_data():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID).worksheet("Metrics")  # adjust sheet name
    data   = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# 3) Sidebar filters
st.sidebar.header("Filters")
pods    = df["POD"].unique().tolist()
channels= df["Channel"].unique().tolist()
sel_pods     = st.sidebar.multiselect("Select POD(s)", pods, default=pods)
sel_channels= st.sidebar.multiselect("Select Channel(s)", channels, default=channels)
filtered = df[df["POD"].isin(sel_pods) & df["Channel"].isin(sel_channels)]

# 4) Metrics cards
st.title("🏆 Weekly Metrics Leaderboard")
col1, col2, col3 = st.columns(3)
top_pod     = filtered.groupby("POD")["MetricValue"].sum().idxmax()
top_channel = filtered.groupby("Channel")["MetricValue"].sum().idxmax()
week_total  = filtered["MetricValue"].sum()

col1.metric("Top POD", top_pod)
col2.metric("Top Channel", top_channel)
col3.metric("This Week’s Total", f"{week_total:,}")

# 5) Progress bar (run-rate vs. target)
st.subheader("Run-Rate Progress")
current = filtered["RunRate"].iloc[-1]
target  = filtered["RunRateTarget"].iloc[-1]
st.write(f"Current: {current:,}  •  Target: {target:,}")
st.progress(min(current/target, 1.0))

# 6) Trend charts
st.subheader("Trend Over Time")
chart_df = filtered.set_index("Week")[["MetricValue", "RunRate"]]
st.line_chart(chart_df)

# 7) Detailed table (optional)
with st.expander("Show raw data"):
    st.dataframe(filtered)
