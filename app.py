import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ── 1) PAGE CONFIG & GLOBAL CSS ──
st.set_page_config(page_title="Ijjat Games – Phase 2", layout="wide")
st.markdown("""
<style>
/* Card container */
.header-card {
  background-color: var(--secondary-background-color);
  padding: 20px;
  border-radius: 12px;
  box-shadow: var(--shadow-2);
  margin-bottom: 24px;
}
/* Row of items */
.header-card-row {
  display: flex;
  justify-content: space-around;
  gap: 1rem;
}
/* Each metric */
.header-card-item {
  flex: 1;
  text-align: center;
}
/* Label (small text above value) */
.header-card-label {
  font-size: 0.9rem;
  color: #888; /* muted */
  margin-bottom: 4px;
}
/* Value (big text) */
.header-card-value {
  font-size: 1.8rem;
  font-weight: bold;
  color: var(--text-color);
}
/* Footer line */
.header-card-footer {
  margin-top: 12px;
  text-align: center;
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-color);
}
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
.next-rate {
  font-size: 0.9rem;
  color: #555;
  margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ── 2) SHEET LOADING ──
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def load_view(sheet_name: str) -> pd.DataFrame:
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    raw    = client.open_by_key(SHEET_ID).worksheet(sheet_name).get_all_values()
    hdr, rows = raw[1], raw[2:]

    key_col = "Channel" if sheet_name=="Channel-View" else "POD"
    col_names, last_week = [], None
    for cell in hdr:
        h = (cell or "").strip()
        if not h:
            col_names.append(key_col)
        elif h.startswith("Week-"):
            col_names.append(h); last_week = h
        elif h.lower()=="required run-rate" and last_week:
            col_names.append(f"{last_week} Required run-rate")
        else:
            col_names.append(h)

    df = pd.DataFrame(rows, columns=col_names)
    df = df[df[key_col].astype(str).str.strip().astype(bool)].copy()
    for c in df.columns:
        if c!=key_col:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    return df

df_channel = load_view("Channel-View")
df_pod     = load_view("POD-View")

# ── 3) AGGREGATED CARD ──
# compute totals
week_cols_all  = [c for c in df_channel.columns if c.startswith("Week-") and "Required" not in c]
total_views    = df_channel[week_cols_all].fillna(0).sum().sum()
total_target   = df_channel["Total Target"].fillna(0).sum()
pct_achieved   = (total_views/total_target*100) if total_target>0 else 0

ach_m = total_views/1_000_000
tar_m = total_target/1_000_000

st.title("🎯 Ijjat Games – Phase 2")
if st.button("🔄 Refresh Data"):
    st.write("Data reloaded — your sheet edits will appear immediately.")

# render card
st.markdown(f"""
<div class="header-card">
  <div class="header-card-row">
    <div class="header-card-item">
      <div class="header-card-label">Views so far</div>
      <div class="header-card-value">{ach_m:0.1f}M</div>
    </div>
    <div class="header-card-item">
      <div class="header-card-label">Total target</div>
      <div class="header-card-value">{tar_m:0.1f}M</div>
    </div>
    <div class="header-card-item">
      <div class="header-card-label">% achieved</div>
      <div class="header-card-value">{pct_achieved:0.1f}%</div>
    </div>
  </div>
  <div class="header-card-footer">Company Dec 2025 target: 100M</div>
</div>
""", unsafe_allow_html=True)

# ── 4) CHANNEL vs POD VIEW ──
view    = st.radio("Select view:", ["Channel", "POD"], horizontal=True)
df      = df_channel if view=="Channel" else df_pod
key_col = "Channel" if view=="Channel" else "POD"

week_cols = [c for c in df.columns if c.startswith("Week-") and "Required" not in c]

st.subheader(f"{view}-View Progress by {view}")

for name in df[key_col].unique():
    row = df[df[key_col]==name].iloc[0]
    tgt = row.get("Total Target", 0) or 0

    # build cumulative
    week_vals  = [(row[c] if pd.notna(row[c]) else 0) for c in week_cols]
    cum, cumulative = 0, []
    for w in week_vals:
        cum += w; cumulative.append(cum)

    frac = (cumulative[-1]/tgt) if tgt>0 else 0
    pct  = frac*100

    # next week
    filled = sum(pd.notna(row[c]) and row[c]>0 for c in week_cols)
    if filled < len(week_cols):
        next_w    = week_cols[filled]
        prev_cum  = cumulative[filled-1] if filled>0 else 0
        rem       = tgt - prev_cum
        run_label = f"{next_w} Run-Rate Needed"
        run_needed= rem
    else:
        run_label = None; run_needed=0

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

# ── 5) RAW DATA ──
with st.expander("Show raw data"):
    st.dataframe(df, use_container_width=True)
