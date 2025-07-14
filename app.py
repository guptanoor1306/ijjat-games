import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & SECRETS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# ── 2) GLOBAL CSS FOR CLASSY PROGRESS BARS ──
st.markdown("""
<style>
.progress-container {
  background-color: #E0E0E0;
  border-radius: 20px;
  padding: 4px;
  margin-bottom: 12px;
}
.progress-bar {
  background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
  height: 24px;
  border-radius: 20px;
  width: 0%;
  transition: width 0.8s ease-in-out;
}
.progress-label {
  font-weight: 600;
  margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── 3) DATA LOADING (no cache) ──
def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # Row 2 → true headers; Row 3+ → data
    hdr  = raw[1]
    rows = raw[2:]

    key_name = "Channel" if sheet_name == "Channel-View" else "POD"

    # Build column names
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

    df = pd.DataFrame(rows, columns=col_names)
    # Drop any empty-key footers
    df = df[df[key_name].astype(str).str.strip().astype(bool)].copy()
    # Coerce numeric columns
    for c in df.columns:
        if c != key_name:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

# Always fetch fresh on each run
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 4) BUILD UI ──
st.title("🎯 Ijjat Games – Phase 2")
if st.button("🔄 Refresh Data"):
    st.write("Data reloaded — any sheet edits will now be visible below.")

view   = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df     = df_channel if view == "Channel" else df_pod
key_col = "Channel" if view == "Channel" else "POD"

st.subheader(f"{view}-View Progress")

# Render one HTML progress bar per group
for name in df[key_col].unique():
    # grab the last “Progress %” (as a fraction)
    if "Progress %" in df.columns:
        vals      = pd.to_numeric(df[df[key_col] == name]["Progress %"].dropna(), errors="coerce")
        frac      = float(vals.iloc[-1]) if not vals.empty else 0.0
    else:
        frac = 0.0

    pct_display = frac * 100
    st.markdown(f"""
      <div class='progress-label'>{name} — {pct_display:0.1f}%</div>
      <div class='progress-container'>
        <div class='progress-bar' style='width:{frac*100}%;'></div>
      </div>
    """, unsafe_allow_html=True)

# Optional raw data for debugging
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
