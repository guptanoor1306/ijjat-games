import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & SECRETS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) DATA LOADING (no caching) ──
def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # row 2 → header, rows 3+ → data
    hdr  = raw[1]
    rows = raw[2:]

    key_name = "Channel" if sheet_name == "Channel-View" else "POD"

    # build column names
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

    df = pd.DataFrame(rows, columns=col_names)
    # drop any blank-key footer rows
    df = df[df[key_name].astype(str).str.strip().astype(bool)].copy()
    # coerce numerics
    for c in df.columns:
        if c != key_name:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

# always load fresh
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) UI ──
st.title("🎯 Ijjat Games – Phase 2")
# clicking this button will re-run the script and thus re-fetch your sheet
if st.button("🔄 Refresh Data"):
    st.write("Data refreshed ✅")

view = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df   = df_channel if view == "Channel" else df_pod
key  = "Channel" if view == "Channel" else "POD"

# ── 4) ONE BAR PER GROUP ──
st.subheader(f"{view}-View Progress by {view}")
for name in df[key].unique():
    # grab last % Target Achieved or default to 0
    if "% Target Achieved" in df.columns:
        vals = pd.to_numeric(df[df[key] == name]["% Target Achieved"].dropna(), errors="coerce")
        last_pct = float(vals.iloc[-1]) if not vals.empty else 0.0
    else:
        last_pct = 0.0

    frac = last_pct / 100.0
    c1, c2, c3 = st.columns([1,4,1])
    c1.markdown(f"**{name}**")
    c2.progress(min(frac, 1.0))
    c3.metric("", f"{last_pct:0.1f}%")

# ── 5) RAW DATA (for sanity) ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
