import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. SEITEN-LAYOUT EINSTELLEN
st.set_page_config(page_title="Energie-Realität Hirschaid & Altendorf", layout="wide")

# 2. TITEL & HEADER
st.title("⚡ Energie-Realitäts-Check: Hirschaid & Altendorf")
st.caption("Ein Service der Bürgerinitiative | Datenbasis: SMARD.de (Bundesnetzagentur) & MaStR | PLZ 96114 & 96146")

st.markdown("---")

# 3. KENNZAHLEN / QUICK-FACTS
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Installierte PV-Leistung (96114 & 96146)", 
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

# 4. GESTAPELTES BALKENDIAGRAMM (AKTUELLE KALENDERWOCHE)
st.subheader("📊 Stromerzeugung vs. Strombedarf der aktuellen Kalenderwoche")
st.write("Vergleich der täglichen Erzeugungsquellen mit dem tatsächlichen Verbrauch (gemittelt in MWh/Tag):")

# Beispieldaten für die Wochentage (Mo - So)
tage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Erzeugungsdaten in MWh (Gestapelte Balken)
erzeugung_data = {
    "Tag": tage,
    "Photovoltaik (Solar)": [180, 220, 150, 90, 210, 250, 230],
    "Windkraft": [60, 40, 110, 160, 50, 30, 40],
    "Wasserkraft": [40, 40, 42, 41, 40, 39, 40],
    "Biomasse": [50, 50, 50, 50, 50, 50, 50],
    "Kernkraft": [0, 0, 0, 0, 0, 0, 0], # In D abgeschaltet, aber als Kategorie vorbereitet
    "Fossile (Gas/Kohle)": [120, 110, 130, 170, 110, 80, 70],
    "Strom-Importe": [80, 60, 90, 110, 70, 40, 30]
}

# Strombedarf / Lastprofil (Rote Kurve)
strombedarf = [500, 510, 520, 525, 490, 410, 380]

df_erzeugung = pd.DataFrame(erzeugung_data)

# Erstellen des Plotly-Diagramms mit doppelter Darstellung (Balken + Linie)
fig = go.Figure()

# Farben nach Energiemonitor-Logik definieren
farben = {
    "Photovoltaik (Solar)": "#FFD600",      # Sonnengelb
    "Windkraft": "#00E5FF",                 # Hellblau
    "Wasserkraft": "#00B0FF",               # Blau
    "Biomasse": "#00E676",                  # Grün
    "Kernkraft": "#AA00FF",                 # Violett
    "Fossile (Gas/Kohle)": "#FF9100",       # Orange
    "Strom-Importe": "#D500F9"              # Magenta/Pink
}

# Gestapelte Balken hinzufügen
for spalte, farbe in farben.items():
    fig.add_trace(go.Bar(
        x=df_erzeugung["Tag"],
        y=df_erzeugung[spalte],
        name=spalte,
        marker_color=farbe
    ))

# Rote Kurve für den Strombedarf hinzufügen
fig.add_trace(go.Scatter(
    x=tage,
    y=strombedarf,
    name="Strombedarf (Last)",
    line=dict(color="#FF1744", width=4), # Rote Linie
    mode="lines+markers"
))

# Layout anpassen (Dark Mode & Gestapelt)
fig.update_layout(
    barmode="stack", # Macht aus den Balken gestapelte Säulen
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FFFFFF", size=13),
    xaxis=dict(title="Wochentag", showgrid=False),
    yaxis=dict(title="MWh / Tag", showgrid=True, gridcolor="#2A3547"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.4,
        xanchor="center",
        x=0.5
    ),
    margin=dict(l=20, r=20, t=20, b=100)
)

st.plotly_chart(fig, use_container_width=True)

# 5. ERKLÄRBOX
st.info("""
**💡 Wie liest man dieses Diagramm?**
* **Balkenhöhe > Rote Linie:** Es entsteht ein **regionaler Stromüberschuss** (meist an sonnigen/windigen Tagen). Der Strom muss exportiert oder abgeregelt werden.
* **Balkenhöhe < Rote Linie:** Es liegt eine **Deckungslücke** vor, die durch fossile Reserven oder Strom-Importe gefüllt werden muss.
""")
