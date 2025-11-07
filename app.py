# app.py

import os
from urllib.parse import urlencode

import streamlit as st
from dotenv import load_dotenv

from amazon_ads_api import AmazonAdsClient

# Carica variabili da .env
load_dotenv()

st.set_page_config(page_title="Amazon Bid Manager", layout="wide")

# Istanzia client una volta sola nella sessione
if "client" not in st.session_state:
    st.session_state["client"] = AmazonAdsClient()

client = st.session_state["client"]

# Recupero variabili di ambiente
MANAGER_ENTITY_ID = os.getenv("AMAZON_MANAGER_ENTITY_ID", "").strip()


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
# Sezione 1 - Generatore link accesso come Editor (ENTITY)
# ----------------------------------------
st.header("1. Generatore link accesso come Editor")

col_a, col_b = st.columns(2)

with col_a:
    st.write("ENTITY ID del tuo account manager")
    if MANAGER_ENTITY_ID:
        st.code(MANAGER_ENTITY_ID)
    else:
        st.warning("Imposta AMAZON_MANAGER_ENTITY_ID nel file .env con il tuo ENTITY manager.")

with col_b:
    client_entity_id = st.text_input("ENTITY ID account cliente", help="Copiato dalla URL dell account Ads del cliente")

if MANAGER_ENTITY_ID and client_entity_id:
    review_link = (
        "https://advertising.amazon.com/"
        f"advertisingAccounts/{client_entity_id}/"
        f"managerAccounts/{MANAGER_ENTITY_ID}/review-link-request"
    )
    st.write("Link da inviare al cliente per concederti i permessi come Editor:")
    st.code(review_link)
elif client_entity_id and not MANAGER_ENTITY_ID:
    st.error("Devi impostare AMAZON_MANAGER_ENTITY_ID nel .env per generare il link.")


st.markdown("---")


# ----------------------------------------
# Sezione 2 - Dashboard campagne per profilo
# ----------------------------------------
st.header("2. Dashboard campagne per profilo cliente")

# 2.1 Recupero profili e selezione dalla sidebar
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
        selected_profile_label = st.selectbox(
            "Seleziona profilo Amazon Ads",
            list(profile_options.keys()),
        )
        profile_id_selected = profile_options[selected_profile_label]
else:
    st.info("Nessun profilo disponibile. Verifica i permessi del tuo account manager.")

if not profile_id_selected:
    st.stop()

st.subheader(f"Profilo selezionato: {selected_profile_label}")

# 2.2 Recupero campagne SP del profilo selezionato
try:
    campaigns = client.get_sp_campaigns(profile_id_selected)
except Exception as e:
    st.error(f"Errore nel recupero campagne Sponsored Products: {e}")
    campaigns = []

if not campaigns:
    st.info("Nessuna campagna Sponsored Products trovata per questo profilo.")
    st.stop()

# Mappa per selezione singola campagna
campaign_map = {
    f"{c.get('name', 'Senza nome')} (ID {c.get('campaignId')})": c
    for c in campaigns
}

selected_campaign_label = st.selectbox(
    "Seleziona una campagna da gestire",
    list(campaign_map.keys()),
)

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

# 2.3 Conteggio target interni alla campagna
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

# ----------------------------------------
# Sezione 3 - Modifica bid campagna selezionata
# ----------------------------------------
st.header("3. Modifica bid della campagna selezionata")

col1, col2, col3, col4 = st.columns(4)

with col1:
    direction = st.radio(
        "Tipo modifica",
        ["Incrementa", "Decrementa"],
        index=0,
    )

with col2:
    delta = st.number_input(
        "Variazione bid (valuta account)",
        min_value=0.0,
        step=0.01,
        format="%.02f",
    )

with col3:
    min_bid = st.number_input(
        "Bid minimo (opzionale)",
        min_value=0.0,
        step=0.01,
        format="%.02f",
    )

with col4:
    max_bid = st.number_input(
        "Bid massimo (opzionale)",
        min_value=0.0,
        step=0.01,
        format="%.02f",
    )

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
            st.error(f"Errore durante l aggiornamento dei bid: {e}")
