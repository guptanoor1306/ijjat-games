import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & GLOBAL CSS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
st.markdown("""
<style>
.progress-label {
  font-weight: 600;
  margin-bottom: 4px;
}
.progress-container {
  background-color: #E0E0E0;
  border-radius: 20px;
  padding: 3px;
  margin-bottom: 8px;
}
.progress-bar {
  background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
  height: 20px;
  border-radius: 20px;
  width: 0%;
  transition: width 0.8s ease-in-out;
}
.runrate-table {
  width: 100%;
  margin-bottom: 24px;
  border-collapse: collapse;
}
.runrate-table th,
.runrate-table td {
  padding: 4px 8px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)

# ── 2) LOAD SHEET UTILITY (no cache) ──
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    hdr  = raw[1]    # row 2 = headers
    data = raw[2:]   # row 3+ = data

    key = "Channel" if sheet_name == "Channel-View" else "POD"
    # build final columns
    col_names, last_week = [], None
    for cell in hdr:
        h = cell.strip() if isinstance(cell, str) else ""
        if not h:
            col_names.append(key)
        elif h.startswith("Week-"):
            col_names.append(h)
            last_week = h
        elif h.lower() == "required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)

    df = pd.DataFrame(data, columns=col_names)
    # drop any footer rows where key is blank
    df = df[df[key].astype(str).str.strip().astype(bool)].copy()
    # coerce all non-key to numeric
    for c in df.columns:
        if c != key:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

# pull both views
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) UI LAYOUT ──
st.title("🎯 Ijjat Games – Phase 2")
if st.button("🔄 Refresh Data"):
    st.write("Data reloaded ✅")

view    = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df      = df_channel if view=="Channel" else df_pod
key_col = "Channel" if view=="Channel" else "POD"

# figure out which columns are Weeks
week_cols = [c for c in df.columns if c.startswith("Week-") and "Required" not in c]

st.subheader(f"{view}-View Progress by {view}")

for name in df[key_col].unique():
    row = df[df[key_col]==name].iloc[0]
    total_target = row["Total Target"] or 0

    # gather the 6 week values
    week_vals = [(row[c] if not pd.isna(row[c]) else 0) for c in week_cols]
    cumulative = []
    cum = 0
    for w in week_vals:
        cum += w
        cumulative.append(cum)

    # overall progress fraction
    frac = (cumulative[-1] / total_target) if total_target>0 else 0
    pct = frac * 100

    # render the bar
    st.markdown(f"<div class='progress-label'>{name} — {pct:0.1f}%</div>", unsafe_allow_html=True)
    st.markdown(f"""
      <div class='progress-container'>
        <div class='progress-bar' style='width:{pct}%;'></div>
      </div>
    """, unsafe_allow_html=True)

    # compute run-rate needed after each past week
    total_weeks = len(week_cols)
    runrates = []
    for i, cum_val in enumerate(cumulative, start=1):
        rem_weeks = total_weeks - i
        if rem_weeks > 0:
            rem_target = total_target - cum_val
            needed = rem_target / rem_weeks
            runrates.append((f"After Week-{i}", needed))

    # render as a small table
    if runrates:
        table_html = "<table class='runrate-table'><tr><th>Milestone</th><th>Needed per Week</th></tr>"
        for label, val in runrates:
            table_html += f"<tr><td>{label}</td><td>{val:,.0f}</td></tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)

# optional raw data
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
