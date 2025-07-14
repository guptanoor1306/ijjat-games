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
  margin-bottom: 4px;
}
.progress-bar {
  background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
  height: 20px;
  border-radius: 20px;
  width: 0%;
  transition: width 0.8s ease-in-out;
}
.next-rate {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ── 2) SHEET LOADER (no cache) ──
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # row 2 = headers, row 3+ = data
    hdr  = raw[1]
    rows = raw[2:]

    key = "Channel" if sheet_name=="Channel-View" else "POD"
    # build column names
    col_names, last_week = [], None
    for cell in hdr:
        h = cell.strip() if isinstance(cell, str) else ""
        if not h:
            col_names.append(key)
        elif h.startswith("Week-"):
            col_names.append(h)
            last_week = h
        elif h.lower()=="required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)

    df = pd.DataFrame(rows, columns=col_names)
    # drop footer rows
    df = df[df[key].astype(str).str.strip().astype(bool)].copy()
    # coerce numeric columns
    for c in df.columns:
        if c!=key:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) UI ──
st.title("🎯 Ijjat Games – Phase 2")
if st.button("🔄 Refresh Data"):
    st.write("Data reloaded — any sheet edits will appear below.")

view    = st.radio("Select view:", ["Channel","POD"], horizontal=True)
df      = df_channel if view=="Channel" else df_pod
key_col = "Channel" if view=="Channel" else "POD"

# identify your Week-1…Week-6 columns
week_cols = [c for c in df.columns if c.startswith("Week-") and "Required" not in c]

st.subheader(f"{view}-View Progress by {view}")

for name in df[key_col].unique():
    row = df[df[key_col]==name].iloc[0]
    total_target = row.get("Total Target", 0) or 0

    # build cumulative sums
    week_vals = [(row[c] if not pd.isna(row[c]) else 0) for c in week_cols]
    cumulative = []
    cum = 0
    for w in week_vals:
        cum += w
        cumulative.append(cum)

    # overall progress
    frac = (cumulative[-1] / total_target) if total_target>0 else 0
    pct  = frac * 100

    # determine how many weeks are "filled"
    filled = sum(pd.notna(row[c]) for c in week_cols)
    # pick the next week index (0-based)
    if filled < len(week_cols):
        next_week = week_cols[filled]
        prev_cum  = cumulative[filled-1] if filled>0 else 0
        rem_target= total_target - prev_cum
        # run-rate needed for that one next week
        needed = rem_target
        next_label = f"{next_week} Run-Rate Needed"
    else:
        next_label = None
        needed     = 0

    # render
    st.markdown(f"<div class='progress-label'>{name} — {pct:0.1f}%</div>", unsafe_allow_html=True)
    st.markdown(f"""
      <div class='progress-container'>
        <div class='progress-bar' style='width:{pct}%;'></div>
      </div>
    """, unsafe_allow_html=True)

    if next_label:
        st.markdown(f"<div class='next-rate'><strong>{next_label}:</strong> {needed:,.0f}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='next-rate'><em>All weeks completed!</em></div>", unsafe_allow_html=True)

# ── 4) DEBUG DATA ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
