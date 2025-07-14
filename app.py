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
        raw = ss.worksheet(sheet_name).get_all_values()

        # — use the 2nd row as header, skip the 1st blank row
        header_row = raw[1]
        data_rows  = raw[2:]

        # build column names exactly as what you see in row 2
        col_names = []
        last_week = None
        for h in header_row:
            h = h.strip()
            if not h:
                col_names.append("Channel")
            elif h.startswith("Week-"):
                col_names.append(h)
                last_week = h
            elif h.lower() == "required run-rate" and last_week:
                col_names.append(f"{last_week} Required run-rate")
            else:
                col_names.append(h)

        # assemble DataFrame
        df = pd.DataFrame(data_rows, columns=col_names)

        # drop any totally blank/“Total” footer row
        df = df[df["Channel"].str.strip().astype(bool)].copy()

        # coerce all non-Channel columns to numbers
        for c in df.columns:
            if c != "Channel":
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    df_chan = fetch_and_clean("Channel-View")
    df_pod  = fetch_and_clean("POD-View")
    return df_chan, df_pod

df_channel, df_pod = load_data()

# — the rest of your app stays exactly as before:
#    • let the user pick Channel vs POD
#    • apply filters
#    • show metrics cards, progress bar, line chart, etc.
