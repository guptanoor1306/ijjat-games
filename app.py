import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & SECRETS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) DATA LOADING UTIL ──
@st.cache_data(ttl=300)
def load_view(sheet_name):
    """
    Fetches a worksheet, uses row 2 as header, cleans data.
    First blank column becomes 'Channel' or 'POD' depending on sheet_name.
    """
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # Row 2 → actual header; Row 3+ → data
    hdr = raw[1]
    rows = raw[2:]

    # Determine what to call the first column
    key_name = "Channel" if sheet_name == "Channel-View" else "POD"

    # Build cleaned column names
    col_names = []
    last_week = None
    for cell in hdr:
        h = cell.strip() if isinstance(cell, str) else ""
        if not h:
            col_names.append(key_name)
        elif h.startswith("Week-"):
            col_names.append(h)
            last_week = h
        elif h.lower() == "required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)

    # Assemble DataFrame
    df = pd.DataFrame(rows, columns=col_names)

    # Drop any footer rows where key is blank
    df = df[df[key_name].astype(str).str.strip().astype(bool)].copy()

    # Coerce everything but key_name to numeric
    for c in df.columns:
        if c != key_name:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")

    return df

# Load both views
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")


# ── 3) UI ──
st.title("🎯 Ijjat Games – Phase 2")

view = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df   = df_channel if view == "Channel" else df_pod
key  = "Channel" if view == "Channel" else "POD"

# ── 4) SAFE % TARGET ACHIEVED ──
pct_series = []
if "% Target Achieved" in df.columns:
    # drop NaNs, convert to float
    pct_series = pd.to_numeric(df["% Target Achieved"].dropna(), errors="coerce").tolist()

last_pct = pct_series[-1] if pct_series else 0.0
pct_frac = last_pct / 100.0  # convert to [0–1]

# ── 5) RENDER PROGRESS ──
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"{view}-View Progress")
    st.progress(min(pct_frac, 1.0))
with col2:
    st.metric(
        label="Completion",
        value=f"{pct_frac*100:0.1f}%",
        delta=f"{last_pct:0.1f}%"
    )

# ── 6) RAW TABLE (for verification) ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
