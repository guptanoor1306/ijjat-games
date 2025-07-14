import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SHEET_ID             = st.secrets["sheet_id"]
SCOPE                = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

@st.cache_data(ttl=600)
def load_data():
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_INFO, SCOPE)
    client = gspread.authorize(creds)
    ss     = client.open_by_key(SHEET_ID)

    def fetch_and_clean(sheet_name):
        # 1) grab everything as a list of lists
        raw = ss.worksheet(sheet_name).get_all_values()
        header_row, data_rows = raw[0], raw[1:]
        
        # 2) build friendly column names
        col_names = []
        last_week = None
        for h in header_row:
            if not h.strip():
                col_names.append("Channel")
            elif h.startswith("Week-"):
                col_names.append(h)
                last_week = h
            elif h == "Required run-rate" and last_week:
                col_names.append(f"{last_week} Required run-rate")
            else:
                col_names.append(h)
        
        # 3) make DataFrame
        df = pd.DataFrame(data_rows, columns=col_names)
        
        # 4) drop any rows where Channel is blank (e.g. the bottom total row)
        df = df[df["Channel"].str.strip() != ""].copy()
        
        # 5) convert all non-Channel columns to numeric (coerce errors to NaN)
        for c in df.columns:
            if c != "Channel":
                df[c] = pd.to_numeric(df[c], errors="coerce")
        
        return df

    df_chan = fetch_and_clean("Channel-View")
    df_pod  = fetch_and_clean("POD-View")
    return df_chan, df_pod

df_channel, df_pod = load_data()

# —— rest of your code unchanged —— #
# e.g. let user pick channel vs pod, show metrics cards, progress bars, charts, etc.
