# app.py

import os
import streamlit as st
from dotenv import load_dotenv
from urllib.parse import urlencode

from amazon_ads_api import AmazonAdsClient
from auth import get_access_token

# Carica variabili da .env o da secrets
load_dotenv()

st.set_page_config(page_title="Amazon Bid Manager", layout="wide")

# Istanzia client una volta sola nella sessione
if "client" not in st.session_state:
    st.session_state["client"] = AmazonAdsClient()

client = st.session_state["client"]

# Recupero variabili
MANAGER_ENTITY_ID = st.secrets.get("AMAZON_MANAGER_ENTITY_ID", "").strip()

# Helper: mappa entityId -> profileId + regione

def get_profile_info_from_entity_id(entity_id):
    try:
        profiles = client.list_profiles()
        for profile in profiles:
            acc_info = profile.get("accountInfo", {})
            if acc_info.get("entityId") == entity_id:
                return {
                    "profileId": profile.get("profileId"),
                    "countryCode": acc_info.get("countryCode")
                }
    except Exception as e:
        st.error(f"Errore nel mapping entity -> profile: {e}")
    return None

def infer_region_from_country(country_code):
    if country_code in ["US", "CA", "MX"]:
        return "NA"
    elif country_code in ["DE", "FR", "IT", "ES", "UK", "GB", "NL", "SE", "PL", "BE"]:
        return "EU"
    elif country_code in ["JP", "SG", "AE", "AU"]:
        return "FE"
    return None

# ----------------------------------------
# Sezione 0 - Stato connessione base
# ----------------------------------------
st.title("Amazon Bid Manager")

with st.sidebar:
    st.subheader("Stato connessione")
    client_id = os.getenv("AMAZON_CLIENT_ID", "")
    refresh_token_present = bool(os.getenv("AMAZON_REFRESH_TOKEN", "").strip())

    if client_id:
        st.text("CLIENT_ID presente")
    else:
        st.error("AMAZON_CLIENT_ID non impostato nel .env")

    if refresh_token_present:
        st.text("REFRESH_TOKEN presente")
    else:
        st.error("AMAZON_REFRESH_TOKEN non impostato nel .env")

    if st.button("Test profili Ads"):
        try:
            profiles_test = client.list_profiles()
            if profiles_test:
                st.success(f"Profili trovati: {len(profiles_test)}")
            else:
                st.warning("Nessun profilo trovato dalla API.")
        except Exception as e:
            st.error(f"Errore test profili: {e}")

# ----------------------------------------
# Sezione 1 - Generatore link accesso come Editor (API)
# ----------------------------------------
st.header("1. Generatore link accesso come Editor")

col_a, col_b = st.columns(2)

with col_a:
    st.write("ENTITY ID del tuo account manager")
    if MANAGER_ENTITY_ID:
        st.code(MANAGER_ENTITY_ID)
    else:
        st.warning("Imposta AMAZON_MANAGER_ENTITY_ID nei secrets o nel .env")

with col_b:
    client_entity_id = st.text_input("ENTITY ID account cliente", help="ENTITY3... visibile nella URL")

selected_region = None
profile_info = None

if client_entity_id:
    profile_info = get_profile_info_from_entity_id(client_entity_id)
    region_auto = None
    if profile_info:
        region_auto = infer_region_from_country(profile_info["countryCode"])
        st.info(f"Regione rilevata automaticamente: {region_auto}")

    selected_region = st.selectbox(
        "Seleziona o conferma la regione del cliente",
        options=["NA", "EU", "FE"],
        index=["NA", "EU", "FE"].index(region_auto) if region_auto in ["NA", "EU", "FE"] else 0
    )

if MANAGER_ENTITY_ID and client_entity_id and selected_region:
    if st.button("Genera link di invito API"):
        try:
            profile_id = profile_info["profileId"] if profile_info else None
            if not profile_id:
                st.error("Impossibile trovare profileId per questo ENTITY ID")
            else:
                link = client.create_review_link(profile_id, MANAGER_ENTITY_ID, selected_region)
                st.success("Link generato con successo (Editor)")
                st.code(link)
                st.markdown(f"[🔗 Clicca qui per testare il link]({link})", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Errore nella generazione del link: {e}")

# ----------------------------------------
# Sezione 2 - Dashboard campagne per profilo
# ----------------------------------------
st.header("2. Dashboard campagne per profilo cliente")

try:
    profiles = client.list_profiles()
except Exception as e:
    st.error(f"Errore nel recupero profili: {e}")
    profiles = []

profile_id_selected = None
selected_profile_label = None

if profiles:
    profile_options = {}
    for p in profiles:
        name = p.get("accountInfo", {}).get("name") or "Senza nome"
        pid = p.get("profileId")
        label = f"{name} - {pid}"
        profile_options[label] = pid

    with st.sidebar:
        st.subheader("Profilo cliente")
        selected_profile_label = st.selectbox("Seleziona profilo Amazon Ads", list(profile_options.keys()))
        profile_id_selected = profile_options[selected_profile_label]
else:
    st.info("Nessun profilo disponibile. Verifica i permessi del tuo account manager.")

if not profile_id_selected:
    st.stop()

st.subheader(f"Profilo selezionato: {selected_profile_label}")

try:
    campaigns = client.get_sp_campaigns(profile_id_selected)
except Exception as e:
    st.error(f"Errore nel recupero campagne Sponsored Products: {e}")
    campaigns = []

if not campaigns:
    st.info("Nessuna campagna Sponsored Products trovata per questo profilo.")
    st.stop()

campaign_map = {f"{c.get('name', 'Senza nome')} (ID {c.get('campaignId')})": c for c in campaigns}

selected_campaign_label = st.selectbox("Seleziona una campagna da gestire", list(campaign_map.keys()))
selected_campaign = campaign_map[selected_campaign_label]
campaign_id = selected_campaign.get("campaignId")

st.write(f"Campagna selezionata ID: {campaign_id}")

col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.write(f"Stato: {selected_campaign.get('state', 'n.d.')}")
with col_info2:
    st.write(f"Daily budget: {selected_campaign.get('dailyBudget', 'n.d.')}")
with col_info3:
    st.write(f"Campaign type: {selected_campaign.get('campaignType', 'n.d.')}")

st.markdown("---")

st.subheader("Target interni alla campagna")
if st.button("Conta target della campagna"):
    try:
        targets = client.get_sp_targets_for_campaign(profile_id_selected, campaign_id)
        st.session_state["last_targets"] = targets
        st.session_state["last_target_count"] = len(targets)
        st.success(f"Target trovati nella campagna: {len(targets)}")
    except Exception as e:
        st.error(f"Errore nel recupero target: {e}")

if "last_target_count" in st.session_state:
    st.write(f"Ultimo conteggio target: {st.session_state['last_target_count']}")
    if "last_targets" in st.session_state and st.session_state["last_targets"]:
        preview_targets = [
            {
                "targetId": t.get("targetId") or t.get("keywordId"),
                "state": t.get("state"),
                "bid": t.get("bid"),
            }
            for t in st.session_state["last_targets"][:20]
        ]
        st.write("Anteprima primi target (max 20):")
        st.dataframe(preview_targets)

st.markdown("---")

st.header("3. Modifica bid della campagna selezionata")
col1, col2, col3, col4 = st.columns(4)

with col1:
    direction = st.radio("Tipo modifica", ["Incrementa", "Decrementa"], index=0)
with col2:
    delta = st.number_input("Variazione bid (valuta account)", min_value=0.0, step=0.01, format="%.02f")
with col3:
    min_bid = st.number_input("Bid minimo (opzionale)", min_value=0.0, step=0.01, format="%.02f")
with col4:
    max_bid = st.number_input("Bid massimo (opzionale)", min_value=0.0, step=0.01, format="%.02f")

st.write("La variazione viene applicata a tutti i target della campagna selezionata.")

if st.button("Applica modifica ai bid della campagna"):
    if delta <= 0:
        st.error("Inserisci una variazione maggiore di zero.")
    else:
        dir_flag = "up" if direction == "Incrementa" else "down"
        min_bid_value = min_bid if min_bid > 0 else None
        max_bid_value = max_bid if max_bid > 0 else None
        try:
            result = client.update_sp_bids_for_campaign(
                profile_id=profile_id_selected,
                campaign_id=campaign_id,
                delta=delta,
                direction=dir_flag,
                min_bid=min_bid_value,
                max_bid=max_bid_value,
            )
            updated = result.get("updated", 0)
            st.success(f"Aggiornati {updated} target nella campagna.")
            preview = result.get("preview", [])
            if preview:
                st.write("Anteprima modifiche (prime righe):")
                st.dataframe(preview[:20])
        except Exception as e:
            st.error(f"Errore durante l'aggiornamento dei bid: {e}")
