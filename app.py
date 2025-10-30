import os
from urllib.parse import urlencode

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AMAZON_CLIENT_ID", "")
REDIRECT_URI = os.getenv("AMAZON_REDIRECT_URI", "http://localhost:8501/callback")
SCOPE = "advertising::campaign_management"
AUTH_URL = "https://www.amazon.com/ap/oa"

st.set_page_config(page_title="Amazon Ads Login")

st.title("Amazon Ads OAuth")

if not CLIENT_ID:
    st.error("Set AMAZON_CLIENT_ID in .env")
else:
    params = {
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
    }
    login_url = AUTH_URL + "?" + urlencode(params)
    st.markdown(f"[Login with Amazon]({login_url})")

query_params = st.experimental_get_query_params()
if "code" in query_params:
    code = query_params["code"][0]
    st.success(f"Code received: {code}")
    st.write("Run: python get_token.py and paste this code.")
else:
    st.info("After login, Amazon will redirect here with ?code=...")
