import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & GLOBAL CSS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
st.markdown("""
<style>
/* Progress bars */
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
/* Next‑week run‑rate text */
.next-rate {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 16px;
}
/* Header stats */
.header-stats {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1rem;
}
.header-stats .achieved {
  font-size: 2rem;
  font-weight: bold;
  color: #222;
}
.header-stats .separator {
  font-size: 2rem;
  color: #888;
}
.header-stats .target {
  font-size: 2rem;
  color: #888;
}
.header-stats + .company-target {
  font-size: 1rem;
  color: #555;
  margin-top: -0.5rem;
  margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── 2) GOOGLE SHEETS LOADER (no cache) ──
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()

    # row 2 = headers, row 3+ = data
    hdr  = raw[1]
    rows = raw[2:]

    key_col = "Channel" if sheet_name == "Channel-View" else "POD"
    # build cleaned column names
    col_names, last_week = [], None
    for cell in hdr:
        h = (cell or "").strip()
        if not h:
            col_names.append(key_col)
        elif h.startswith("Week-"):
            col_names.append(h)
            last_week = h
        elif h.lower()=="required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)

    df = pd.DataFrame(rows, columns=col_names)
    # drop trailing blank-key rows
    df = df[df[key_col].astype(str).str.strip().astype(bool)].copy()
    # coerce numeric
    for c in df.columns:
        if c != key_col:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

# always fresh reload
df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) LAYOUT & HEADER STATS ──
st.title("🎯 Ijjat Games – Phase 2")

if st.button("🔄 Refresh Data"):
    st.write("Data reloaded — edits in your sheet will now appear.")

# compute aggregate totals for header
week_cols_all = [c for c in df_channel.columns if c.startswith("Week-") and "Required" not in c]
total_views   = df_channel[week_cols_all].fillna(0).sum().sum()
total_target  = df_channel["Total Target"].fillna(0).sum()

# convert to millions and round
ach_m = total_views / 1_000_000
tar_m = total_target / 1_000_000

# render aggregated header
st.markdown(f"""
<div class="header-stats">
  <div class="achieved">{ach_m:0.1f}M views</div>
  <div class="separator">/</div>
  <div class="target">{tar_m:0.1f}M target</div>
</div>
<div class="company-target">Company Dec 2025 target: 70M</div>
""", unsafe_allow_html=True)

# ── 4) CHANNEL vs POD VIEW ──
view    = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df      = df_channel if view=="Channel" else df_pod
key_col = "Channel" if view=="Channel" else "POD"

# identify Week-1…Week-6 columns robustly
week_cols = [c for c in df.columns if c.strip().startswith("Week-") and "Required" not in c]

st.subheader(f"{view}-View Progress by {view}")

for name in df[key_col].unique():
    row = df[df[key_col]==name].iloc[0]
    raw_target = row.get("Total Target", 0)
    # guard against NaN or zero
    total_target = raw_target if pd.notna(raw_target) and raw_target>0 else 0

    # build cumulative sums
    week_vals  = [(row[c] if pd.notna(row[c]) else 0) for c in week_cols]
    cumulative = []
    cum = 0
    for w in week_vals:
        cum += w
        cumulative.append(cum)

    # overall fraction
    frac = (cumulative[-1]/total_target) if total_target>0 else 0
    pct  = frac * 100

    # determine next week
    filled = sum(pd.notna(row[c]) and row[c]>0 for c in week_cols)
    if filled < len(week_cols):
        next_week = week_cols[filled]
        prev_cum  = cumulative[filled-1] if filled>0 else 0
        remaining = total_target - prev_cum
        run_label = f"{next_week} Run-Rate Needed"
        run_needed= remaining
    else:
        run_label = None
        run_needed= 0

    # render progress bar + run-rate
    st.markdown(f"<div class='progress-label'>{name} — {pct:0.1f}%</div>", unsafe_allow_html=True)
    st.markdown(f"""
      <div class='progress-container'>
        <div class='progress-bar' style='width:{pct}%;'></div>
      </div>
    """, unsafe_allow_html=True)

    if run_label:
        st.markdown(f"<div class='next-rate'><strong>{run_label}:</strong> {run_needed:,.0f}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='next-rate'><em>All weeks completed!</em></div>", unsafe_allow_html=True)

# ── 5) RAW DATA (for debugging) ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
