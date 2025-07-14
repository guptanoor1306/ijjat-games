import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) CONFIG ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) UTILS ──
def clean_sheet(sheet_name):
    """Fetch worksheet, use row 2 as header, clean numeric columns."""
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()
    
    # row 2 = headers; row 3+ = data
    hdr_row = raw[1]
    data    = raw[2:]
    
    col_names = []
    last_week = None
    for cell in hdr_row:
        h = cell.strip() if isinstance(cell, str) else ""
        if not h:
            col_names.append("Key")
        elif h.startswith("Week-"):
            col_names.append(h)
            last_week = h
        elif h.lower() == "required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)
    
    df = pd.DataFrame(data, columns=col_names)
    
    # Drop any footer rows where Key is blank
    df = df[df["Key"].astype(str).str.strip().astype(bool)].copy()
    
    # Coerce all but Key to numeric
    for c in df.columns:
        if c != "Key":
            df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")
    return df

@st.cache_data(ttl=300)
def load_data():
    return clean_sheet("Channel-View"), clean_sheet("POD-View")

df_channel, df_pod = load_data()

# ── 3) UI ──
st.title("🎯 Ijjat Games – Phase 2")

view = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df   = df_channel if view == "Channel" else df_pod

# ── 4) PROGRESS BAR & METRIC ──
pct = 0.0
if "% Target Achieved" in df.columns and not df["% Target Achieved"].dropna().empty:
    pct = float(df["% Target Achieved"].dropna().iloc[-1]) / 100

col1, col2 = st.columns([3,1])
with col1:
    st.subheader(f"{view}-View Progress")
    st.progress(min(pct, 1.0))
with col2:
    st.metric(
        label="Completion",
        value=f"{pct*100:0.1f}%",
        delta=f"{df['% Target Achieved'].dropna().iloc[-1]:.1f}%"
    )

# ── 5) SANITY CHECK ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
