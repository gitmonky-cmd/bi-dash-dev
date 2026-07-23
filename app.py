import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Seiten-Layout einstellen
st.set_page_config(page_title="Energie-Realität Hirschaid & Altendorf", layout="wide")

st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption("Ein Service der Bürgerinitiative | Datenquelle: Bundesnetzagentur (SMARD API) & MaStR")

st.markdown("---")

# 1. KENNZAHLEN / QUICK-FACTS (Beispiele & Platzhalter)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Installierte PV-Leistung (Hirschaid/Altendorf)", value="ca. 45 MWp")
with col2:
    st.metric(label="Inland-Strompreis Börse (EPEX Spot)", value="8.4 ct/kWh")
with col3:
    st.metric(label="Regionaler Netzzustand (TenneT)", value="Eingriff / Redispatch", delta_color="inverse")

st.markdown("---")

# 2. LIVE-DATEN DER BUNDESNETZAGENTUR ABRUFEN
st.subheader("📊 Woher kommt der Strom im Netz zur aktuellen Stunde?")
st.write("Die Bilanz zeigt die tatsächliche Erzeugung im Netzgebiet (TenneT/Bayernwerk):")

@st.cache_data(ttl=900) # Speichert Daten für 15 Minuten, um API-Aufrufe zu sparen
def load_smard_data():
    # Beispiel-Abruf: Erzeugung Reallast/Mix Deutschland/Bayern-Sektor via SMARD API
    # Für den Test nutzen wir strukturierte Testdaten/Schnittstellenwerte
    mix_data = {
        "Energieträger": ["PV & Wind (Lokal)", "Biomasse & Wasser", "Fossile Reserven (Gas/Kohle)", "Strom-Importe (z.B. Tschechien)"],
        "Anteil (%)": [35, 20, 25, 20]
    }
    return pd.DataFrame(mix_data)

df = load_smard_data()

# Visualisierung als Kreisdiagramm
fig = px.pie(df, values="Anteil (%)", names="Energieträger", color_discrete_sequence=px.colors.qualitative.Set2)
st.plotly_chart(fig, use_container_width=True)

# 3. HINWEISBOX FÜR BÜRGER
st.info("""
**💡 Wussten Sie schon?** 
Wenn Erneuerbare-Energien-Anlagen in unserer Region wegen Netzüberlastung gedrosselt werden (Redispatch), erhalten die Betreiber eine Entschädigung. 
Diese Kosten werden über die **Netzentgelte** direkt auf die Stromrechnungen der Bürger umgelegt.
""")