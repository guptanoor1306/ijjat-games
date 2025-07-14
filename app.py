import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & SECRETS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) DATA LOADING UTILITIES ──
@st.cache_data(ttl=300)
def load_view(sheet_name: str) -> pd.DataFrame:
    """
    Fetch a worksheet by name, use row 2 as header, clean and return a DataFrame.
    The first blank header cell is named "Channel" or "POD" based on sheet_name.
    """
    # Authorize and fetch raw values
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # Row 2 = true headers; rows 3+ = data
    hdr  = raw[1]
    data = raw[2:]

    # Determine key column name
    key_name = "Channel" if sheet_name == "Channel-View" else "POD"

    # Build final column names
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
    df = pd.DataFrame(data, columns=col_names)

    # Drop footer rows where key is blank
    df = df[df[key_name].astype(str).str.strip().astype(bool)].copy()

    # Coerce all but the key column to numeric
    for c in df.columns:
        if c != key_name:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")

    return df

# Load both views once
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) BUILD THE UI ──
st.title("🎯 Ijjat Games – Phase 2")

# Toggle between Channel and POD views
view = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df   = df_channel if view == "Channel" else df_pod
key  = "Channel" if view == "Channel" else "POD"

# ── 4) MULTIPLE PROGRESS BARS ──
st.subheader(f"{view}-View Progress by {view}")

# For each Channel/POD, grab its last "% Target Achieved" (or 0)
for name in df[key].unique():
    # Extract and clean the series
    if "% Target Achieved" in df.columns:
        series = (
            pd.to_numeric(
                df[df[key] == name]["% Target Achieved"].dropna(),
                errors="coerce"
            )
            .tolist()
        )
    else:
        series = []

    last_pct = series[-1] if series else 0.0
    frac     = last_pct / 100.0  # normalize to [0–1]

    # Layout: name | progress bar | percent metric
    col_name, col_bar, col_pct = st.columns([1, 4, 1])
    col_name.markdown(f"**{name}**")
    col_bar.progress(min(frac, 1.0))
    col_pct.metric("", f"{last_pct:0.1f}%")

# ── 5) OPTIONAL: SHOW RAW DATA FOR DEBUGGING ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
