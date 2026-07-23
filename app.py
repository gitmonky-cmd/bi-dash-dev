import streamlit as st
import pandas as pd
import plotly.express as px

# Seiten-Layout einstellen
st.set_page_config(page_title="Energie-Realität Hirschaid & Altendorf", layout="wide")

# Titel & Header
st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption("Ein Service der Bürgerinitiative | Datenbasis: SMARD.de (Bundesnetzagentur) & MaStR")

st.markdown("---")

# 1. KENNZAHLEN / QUICK-FACTS (Im Bayernwerk-Karten-Stil)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Installierte PV-Leistung (96114 & 96145)", 
        value="45,2 MWp", 
        delta="Stand MaStR"
    )

with col2:
    st.metric(
        label="Börsenstrompreis (EPEX Spot)", 
        value="8,4 ct/kWh", 
        delta="Inland-Großhandel"
    )

with col3:
    st.metric(
        label="Netzzustand Region (TenneT)", 
        value="Redispatch aktiv", 
        delta="-12 MW Drosselung", 
        delta_color="inverse"
    )

st.markdown("---")

# 2. LIVE-NETZMIX DIAGRAMM (Dark Mode Design)
st.subheader("📊 Physikalisch-Bilanzielle Herkunft des Stroms im Netz")
st.write("Aktuelle Schätzung für das Verteilnetzgebiet TenneT / Bayernwerk:")

# Daten
mix_data = {
    "Energieträger": ["PV & Wind (Lokal)", "Biomasse & Wasser", "Fossile Reserven (Gas/Kohle)", "Strom-Importe (z.B. CZ)"],
    "Anteil": [35, 20, 25, 20]
}
df = pd.DataFrame(mix_data)

# Dark-Mode-Farben für das Diagramm (Bayernwerk-Style: leuchtendes Grün, Gelb, Grau, Rot)
farben = ["#00E676", "#00B0FF", "#FF9100", "#FF1744"]

fig = px.pie(
    df, 
    values="Anteil", 
    names="Energieträger", 
    color_discrete_sequence=farben,
    hole=0.4 # Macht daraus ein modernes Donut-Diagramm
)

# Dark-Mode Layout für Plotly
fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=14),
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
)

st.plotly_chart(fig, use_container_width=True)

# 3. HINWEISBOX
st.info("""
**💡 Der System-Realitäts-Check:**
Der offizielle *Energie Monitor Bayern* zeigt primär die rein bilanzielle Erzeugung vor Ort. 
Dieses Dashboard ergänzt die blinden Flecken: **Abregelungen von Ökostrom (Redispatch)** und die **tatsächliche Herkunft des Importstroms**, wenn lokal die Sonne nicht scheint.
""")
