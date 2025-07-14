import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & SECRETS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) DATA LOADING (always fresh) ──
def load_view(sheet_name: str) -> pd.DataFrame:
    """
    Fetch a worksheet by name, use row 2 as header, clean and return a DataFrame.
    The blank first header cell becomes "Channel" or "POD" based on sheet_name.
    """
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # Row 2 → header, Rows 3+ → data
    hdr  = raw[1]
    data = raw[2:]

    # Name of the key column
    key_name = "Channel" if sheet_name == "Channel-View" else "POD"

    # Build final column names
    col_names, last_week = [], None
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

    df = pd.DataFrame(data, columns=col_names)

    # Drop any footer rows where the key column is blank
    df = df[df[key_name].astype(str).str.strip().astype(bool)].copy()

    # Coerce all non-key columns to numeric
    for c in df.columns:
        if c != key_name:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")

    return df

# Load Channel & POD views
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) UI ──
st.title("🎯 Ijjat Games – Phase 2")

# Refresh button (any click re-runs the script and reloads the sheet)
if st.button("🔄 Refresh Data"):
    st.write("✅ Data reloaded")

view    = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df      = df_channel if view == "Channel" else df_pod
key_col = "Channel"      if view == "Channel" else "POD"

# ── 4) ONE BAR PER GROUP, USING 'Progress %' ──
st.subheader(f"{view}-View Progress by {view}")

for name in df[key_col].unique():
    # grab the last non-null "Progress %" value
    if "Progress %" in df.columns:
        vals       = pd.to_numeric(df[df[key_col] == name]["Progress %"].dropna(), errors="coerce")
        last_frac  = float(vals.iloc[-1]) if not vals.empty else 0.0
    else:
        last_frac = 0.0

    # render
    pct_display = last_frac * 100  # to show as percent
    c1, c2, c3 = st.columns([1, 4, 1])
    c1.markdown(f"**{name}**")
    c2.progress(min(last_frac, 1.0))
    c3.metric("", f"{pct_display:0.1f}%")

# ── 5) RAW DATA FOR DEBUGGING ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
